"""Actual Pillow 13 batch decoding and shared upload / send boundaries."""

import base64
import io
import subprocess
from pathlib import Path

import pytest
import yaml
from PIL import Image

from src.agent import image_validation
from src.agent.attachments import prepare_attachments
from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError


def picture(format="PNG", size=(32, 24)):
    stream = io.BytesIO()
    Image.new("RGB", size, "navy").save(stream, format=format)
    return stream.getvalue()


@pytest.mark.parametrize("suffix,format", [(".png", "PNG"), (".jpeg", "JPEG"), (".webp", "WEBP")])
def test_real_worker_accepts_unicode_images_and_uses_validated_snapshot(tmp_path, suffix, format):
    path = tmp_path / ("中文研究图" + suffix)
    content = picture(format)
    path.write_bytes(content)
    bundle = prepare_attachments([path])
    path.write_bytes(b"changed after validation")
    assert base64.b64decode(bundle.image_data_urls()[0].split(",", 1)[1]) == content


@pytest.mark.parametrize("content", [b"not an image", picture("PNG"), picture("JPEG")[:100]])
def test_worker_rejects_fake_mismatched_and_truncated_jpeg(tmp_path, content):
    path = tmp_path / "misleading.jpg"
    path.write_bytes(content)
    with pytest.raises(BusinessError, match="校验失败"):
        prepare_attachments([path])


def test_worker_rejects_pixel_and_frame_limits(tmp_path):
    path = tmp_path / "oversized.png"
    path.write_bytes(picture(size=(5000, 4000)))
    with pytest.raises(BusinessError, match="超限"):
        prepare_attachments([path])
    animation = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(
        animation, format="PNG", save_all=True, append_images=[Image.new("RGB", (16, 16), "blue")]
    )
    animated = tmp_path / "animated.png"
    animated.write_bytes(animation.getvalue())
    with pytest.raises(BusinessError, match="帧数"):
        prepare_attachments([animated])


def test_one_subprocess_per_batch_and_no_worker_for_text(tmp_path, monkeypatch):
    actual = image_validation.subprocess.run
    calls = []

    def record(*args, **kwargs):
        calls.append(args)
        return actual(*args, **kwargs)

    monkeypatch.setattr(image_validation.subprocess, "run", record)
    paths = [tmp_path / name for name in ("a.png", "b.png")]
    for path in paths:
        path.write_bytes(picture())
    assert len(prepare_attachments(paths).image_data_urls()) == 2
    assert len(calls) == 1
    text = tmp_path / "研究.md"
    text.write_text("风险与收益", encoding="utf-8")
    assert "风险与收益" in prepare_attachments([text]).text_context
    assert len(calls) == 1


def test_actual_worker_timeout_fails_closed(monkeypatch):
    config = yaml.safe_load((PROJECT_ROOT / "egs/config/models/image_validation.yaml").read_text(encoding="utf-8"))
    monkeypatch.setattr(image_validation.yaml, "safe_load", lambda text: {**config, "timeout_seconds": 0.001})
    with pytest.raises(BusinessError, match="失败或超时") as failure:
        image_validation.validate_images([("a.png", picture())])
    assert isinstance(failure.value.__cause__, subprocess.TimeoutExpired)


def test_missing_image_environment_fails_closed(monkeypatch):
    config = yaml.safe_load((PROJECT_ROOT / "egs/config/models/image_validation.yaml").read_text(encoding="utf-8"))
    monkeypatch.setattr(
        image_validation.yaml,
        "safe_load",
        lambda text: {**config, "environment": ".pytest_tmp/absent-image-environment"},
    )
    with pytest.raises(BusinessError, match="缺少独立图片校验环境"):
        image_validation.validate_images([("a.png", picture())])


def test_api_rejects_before_persist_and_validates_again_at_send(client):
    from src.agent.workspace import AIWorkspaceService
    from src.core.config import get_settings

    root = get_settings().data_dir / "ai_workspace/attachments"
    result = client.post("/api/v1/ai-workspace/attachments", files={"file": ("假图片.jpg", b"plain text")}).json()
    assert result["code"] == 1002 and not list(root.glob("*"))
    upload = client.post("/api/v1/ai-workspace/attachments", files={"file": ("图.png", picture())}).json()
    assert upload["code"] == 0, upload
    service = AIWorkspaceService()
    session = service.create_session("Boundary fixture")
    identifier = upload["data"]["attachment_id"]
    bundle = prepare_attachments(service._attachment_paths([identifier]))
    cli_paths = bundle.cli_image_paths()
    assert cli_paths[0].read_bytes() == picture()
    assert Path(cli_paths[0]).is_relative_to(get_settings().data_dir)
    service._attachment_paths([identifier])[0].write_bytes(b"changed")
    with pytest.raises(BusinessError, match="校验失败"):
        list(service.send_stream(session["id"], {"message": "analyze", "attachments": [identifier]}))
    assert service.detail(session["id"])["messages"] == []


def test_composer_retains_input_and_history_after_rejection(client, tmp_path):
    from src.agent.workspace import AIWorkspaceService
    from src.frontend.services import FrontendService

    path = tmp_path / "伪图片.jpg"
    path.write_bytes(b"ordinary text")
    value = list(FrontendService().ai_console_send_stream(0, "分析附件", [], attachments=[path]))[-1]
    assert value[1] == [] and value[2] == "分析附件" and value[3]["__type__"] == "update"
    assert "未发送" in value[4] and "校验失败" in value[4]
    assert AIWorkspaceService().detail(value[0])["messages"] == []
