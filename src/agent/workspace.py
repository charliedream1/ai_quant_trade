"""AI sessions and durable messages independent of Gradio callback objects."""

import threading
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from weakref import WeakValueDictionary

import yaml

from src.agent.attachments import CONFIG_PATH, _limits, prepare_attachments
from src.agent.composer_config import validate_selection
from src.agent.image_validation import validate_images
from src.agent.workspace_backend import backend_events
from src.core.config import get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.kb_importer import parse_document_bytes
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso

_LOCKS: WeakValueDictionary[int, threading.Lock] = WeakValueDictionary()
_LOCKS_GUARD = threading.Lock()


def workspace_config() -> dict[str, Any]:
    return dict(yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["workspace"])


class AIWorkspaceService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def list_sessions(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self.repo.page("ai_workspace_sessions", page, page_size, order_by="updated_at DESC, id DESC")

    def create_session(self, title: str, project_name: str | None = None) -> dict[str, Any]:
        if not title.strip():
            raise BusinessError(ErrorCode.INVALID_PARAM, "会话标题不能为空")
        now = utc_now_iso()
        return self.repo.insert(
            "ai_workspace_sessions",
            {
                "title": title.strip(),
                "project_name": project_name or str(workspace_config()["default_project"]),
                "session_type": "chat",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
        )

    def detail(self, session_id: int) -> dict[str, Any]:
        session = self.repo.get("ai_workspace_sessions", session_id)
        limit = max(1, int(workspace_config()["history_messages"]))
        messages = self.repo.db.query(
            "SELECT * FROM ai_workspace_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit)
        )
        for message in messages:
            message["metadata"] = json_loads(message.get("metadata"), {})
        return {**session, "session_id": session_id, "messages": list(reversed(messages))}

    def upload(self, filename: str, content: bytes) -> dict[str, Any]:
        limits = _limits()
        suffix = Path(filename).suffix.lower()
        if suffix not in set(limits["text_extensions"]) | set(limits["image_extensions"]):
            raise BusinessError(ErrorCode.INVALID_PARAM, "不支持的附件类型")
        if len(content) > int(limits["max_total_bytes"]):
            raise BusinessError(ErrorCode.INVALID_PARAM, "附件超过大小限制")
        if suffix in limits["image_extensions"]:
            validate_images([(filename, content)])
        elif suffix in {".pdf", ".docx"}:
            parse_document_bytes(filename, content)
        identifier = uuid4().hex
        root = get_settings().data_dir / "ai_workspace" / "attachments" / identifier
        root.mkdir(parents=True, exist_ok=True)
        path = root / ("attachment" + suffix)
        path.write_bytes(content)
        return {"attachment_id": identifier, "name": Path(filename).name, "bytes": len(content)}

    def _attachment_paths(self, identifiers: list[str]):
        if not isinstance(identifiers, list) or any(not isinstance(item, str) for item in identifiers):
            raise BusinessError(ErrorCode.INVALID_PARAM, "attachments 必须是上传标识字符串列表")
        paths = []
        for identifier in identifiers:
            try:
                key = UUID(identifier).hex
            except ValueError as exc:
                raise BusinessError(ErrorCode.INVALID_PARAM, "附件标识格式无效") from exc
            files = list((get_settings().data_dir / "ai_workspace" / "attachments" / key).glob("attachment.*"))
            if len(files) != 1:
                raise BusinessError(ErrorCode.NOT_FOUND, "附件不存在")
            paths.append(files[0])
        return paths

    def send_stream(self, session_id: int, payload: dict[str, Any], *, local_attachments: Any = None):
        payload = validate_selection(payload)
        message = str(payload.get("message") or "").strip()
        if not message:
            raise BusinessError(ErrorCode.INVALID_PARAM, "消息不能为空")
        self.repo.get("ai_workspace_sessions", session_id)
        bundle = prepare_attachments(
            local_attachments
            if local_attachments is not None
            else self._attachment_paths(payload.get("attachments") or [])
        )
        with _LOCKS_GUARD:
            lock = _LOCKS.setdefault(session_id, threading.Lock())
        if not lock.acquire(blocking=False):
            raise BusinessError(ErrorCode.CONSTRAINT_CONFLICT, "当前会话仍在处理上一条消息")
        try:
            yield from self._send_locked(session_id, {**payload, "message": message}, bundle)
        finally:
            lock.release()

    def _send_locked(self, session_id: int, payload: dict[str, Any], bundle: Any):
        history = [{"role": item["role"], "content": item["content"]} for item in self.detail(session_id)["messages"]]
        self.repo.insert(
            "ai_workspace_messages",
            {
                "session_id": session_id,
                "role": "user",
                "content": payload["message"],
                "metadata": {
                    "backend": payload.get("backend", "generic"),
                    "attachments": bundle.metadata(),
                    "access_mode": payload["access_mode"],
                    "model_name": payload.get("model_name"),
                    "reasoning_effort": payload.get("reasoning_effort"),
                },
                "created_at": utc_now_iso(),
            },
        )
        result: dict[str, Any] = {"status": "failed", "text": "消息流已中断"}
        events = []
        try:
            yield {"type": "status", "data": {"status": "received", "session_id": session_id}}
            for event in backend_events(self.repo, {**payload, "session_id": session_id}, history, bundle):
                events.append(event)
                if event["type"] == "backend_result":
                    result = event["data"]
                else:
                    yield event
        except Exception as exc:
            result = {"status": "failed", "text": str(exc), "error": str(exc)}
        finally:
            self.repo.insert(
                "ai_workspace_messages",
                {
                    "session_id": session_id,
                    "role": "assistant",
                    "content": result.get("text", ""),
                    "metadata": {
                        **result,
                        "events": events,
                        "attachments": bundle.metadata(),
                        "access_mode": payload["access_mode"],
                    },
                    "created_at": utc_now_iso(),
                },
            )
            self.repo.update("ai_workspace_sessions", session_id, {"updated_at": utc_now_iso()})
        yield {
            "type": "result",
            "data": {"code": 0, "message": "会话调用已留档", "data": {"session_id": session_id, **result}},
        }

    def send(self, session_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return list(self.send_stream(session_id, payload))[-1]["data"]["data"]
