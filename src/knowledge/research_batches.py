"""Persistent research import jobs with per-item retries and cancellation."""

import json
from threading import Lock, Thread
from time import monotonic
from uuid import uuid4

from src.core.logger import get_logger
from src.core.redaction import redact_text
from src.core.repository import Repository
from src.core.stream_control import STREAM_STOP
from src.core.task_control import TaskEvent, cancel_lease, lease_alive
from src.core.timeutil import utc_now_iso

from .config import chunk_length, library_name
from .research_batch_import import ingest
from .research_catalog import collect
from .research_classification import policy

KIND = "research_ingestion"
LOCK = Lock()
ACTIVE: dict[str, tuple[TaskEvent, Thread]] = {}
LOG = get_logger("knowledge.research")


class ResearchBatches:
    def __init__(self, repo=None):
        self.repo = repo or Repository()
        self.db = self.repo.db

    def prepare(self, kind, filters):
        items, scope = collect(kind, filters)
        key, now = uuid4().hex, utc_now_iso()
        with self.db.transaction():
            self.db.execute(
                "INSERT INTO kb_research_batches(id,status,scope,created_at,updated_at) VALUES(?,?,?,?,?)",
                (key, "prepared", json.dumps(scope, ensure_ascii=False), now, now),
            )
            self.db.executemany(
                "INSERT INTO kb_research_batch_items(batch_id,item_key,manifest,status) VALUES(?,?,?,?)",
                [(key, item["key"], json.dumps(item, ensure_ascii=False), "candidate") for item in items],
            )
        return key, scope, [(item["title"], item["key"]) for item in items]

    def start(self, key, selected, all_results, library, mode, model_id=None, size=None, expected_filters=None):
        if mode not in {"traditional", "zero_shot", "llm"}:
            raise ValueError("Unknown classification mode")
        if mode == "llm":
            row = self.db.query_one("SELECT id FROM llm_models WHERE id=? AND enabled=1", (model_id,))
            if not row:
                raise ValueError("Select an enabled classification model")
        settings = {
            "library": library_name(library),
            "mode": mode,
            "model_id": model_id,
            "chunk_chars": chunk_length(size),
        }
        with self.db.transaction():
            row = self.repo.get("kb_research_batches", key)
            if row["status"] != "prepared":
                raise ValueError("This batch has already been submitted")
            saved = json.loads(row["scope"]).get("filters")
            if expected_filters is not None and saved is not None and saved != list(expected_filters):
                raise ValueError("The search filters changed. Prepare the batch again.")
            actual = {
                item["item_key"]
                for item in self.db.query("SELECT item_key FROM kb_research_batch_items WHERE batch_id=?", (key,))
            }
            keys = actual if all_results else set(selected or [])
            if not keys or not keys <= actual:
                raise ValueError("Select documents from the prepared results")
            self.db.executemany(
                "UPDATE kb_research_batch_items SET status='pending' WHERE batch_id=? AND item_key=?",
                [(key, item) for item in keys],
            )
            self.db.execute(
                "UPDATE kb_research_batches SET status=?,settings=?,updated_at=? WHERE id=?",
                ("queued", json.dumps(settings, ensure_ascii=False), utc_now_iso(), key),
            )
        self._launch(key)
        return key

    def _launch(self, key):
        try:
            event = TaskEvent(KIND, key, self.repo, limit=policy()["limits"]["jobs"])
        except ValueError:
            if not lease_alive(KIND, key, self.repo):
                self.db.execute(
                    "UPDATE kb_research_batches SET status='waiting',updated_at=? WHERE id=? AND status='queued'",
                    (utc_now_iso(), key),
                )
            return
        thread = Thread(target=self._run, args=(key, event), daemon=True, name="research-ingestion")
        with LOCK:
            ACTIVE[key] = event, thread
            try:
                thread.start()
            except Exception:
                ACTIVE.pop(key, None)
                event.close()
                self._state(key, "interrupted")
                raise

    def _state(self, key, status):
        self.db.execute("UPDATE kb_research_batches SET status=?,updated_at=? WHERE id=?", (status, utc_now_iso(), key))

    def _run(self, key, event):
        token = STREAM_STOP.set(event)
        outcome = "interrupted"

        def check():
            if event.is_set():
                raise InterruptedError("Research import cancelled")

        try:
            acquired = self.db.execute(
                "UPDATE kb_research_batches SET status='running',updated_at=? WHERE id=? AND status='queued'",
                (utc_now_iso(), key),
            )
            if not acquired.rowcount:
                outcome = "cancelled"
                return
            settings = json.loads(self.repo.get("kb_research_batches", key)["settings"])
            rows = self.db.query(
                "SELECT item_key,manifest FROM kb_research_batch_items WHERE batch_id=? AND status='pending'",
                (key,),
            )
            for row in rows:
                check()
                item_key = row["item_key"]

                def update(status, doc_id=None, detail="", item_key=item_key):
                    self.db.execute(
                        "UPDATE kb_research_batch_items SET status=?,document_id=?,detail=? WHERE batch_id=? AND item_key=?",
                        (status, doc_id, detail, key, item_key),
                    )

                update("starting")
                try:
                    update(*ingest(self.repo, json.loads(row["manifest"]), settings, check, update))
                except InterruptedError:
                    update("pending")
                    raise
                except Exception as exc:
                    detail = redact_text(str(exc)) if type(exc) is ValueError else type(exc).__name__
                    update("failed", detail=detail[:150])
            outcome = "completed"
        except InterruptedError:
            outcome = "cancelled"
        except Exception as exc:
            LOG.warning("Research batch interrupted | job={} error_type={}", key, type(exc).__name__)
        finally:
            STREAM_STOP.reset(token)
            with LOCK:
                event.close()
                self._state(key, outcome)
                ACTIVE.pop(key, None)

    def cancel(self, key):
        with LOCK:
            row = self.repo.get("kb_research_batches", key)
            if row["status"] in {"queued", "waiting", "running"} and not cancel_lease(KIND, key, self.repo):
                self.db.execute(
                    "UPDATE kb_research_batches SET status='cancelled',updated_at=? "
                    "WHERE id=? AND status IN ('queued','waiting','running')",
                    (utc_now_iso(), key),
                )

    def retry(self, key):
        with LOCK, self.db.transaction():
            if self._status(key) not in {"waiting", "interrupted", "cancelled", "completed"}:
                raise ValueError("The batch has not finished")
            self.db.execute(
                "UPDATE kb_research_batch_items SET status='pending' WHERE batch_id=? "
                "AND status NOT IN ('candidate','imported','duplicate','review')",
                (key,),
            )
            self._state(key, "queued")
        self._launch(key)

    def status(self, key):
        with LOCK:
            status = self._status(key)
            rows = self.db.query(
                "SELECT manifest,status,document_id,detail FROM kb_research_batch_items "
                "WHERE batch_id=? AND status!='candidate' ORDER BY rowid",
                (key,),
            )
        return status, [
            [json.loads(row["manifest"])["title"], row["status"], row["document_id"], row["detail"]] for row in rows
        ]

    def _status(self, key):
        status = self.repo.get("kb_research_batches", key)["status"]
        if status == "running" and not lease_alive(KIND, key, self.repo):
            return "interrupted"
        if status == "queued" and not lease_alive(KIND, key, self.repo) and key not in ACTIVE:
            return "interrupted"
        return status

    def history(self, kind):
        rows = self.db.query(
            "SELECT id,status,created_at FROM kb_research_batches WHERE json_extract(scope,'$.kind')=? "
            "AND status!='prepared' ORDER BY created_at DESC LIMIT ?",
            (kind, policy()["limits"]["history"]),
        )
        return [(f"{row['created_at']} · {row['status']} · {row['id'][:8]}", row["id"]) for row in rows]


def shutdown():
    with LOCK:
        jobs = list(ACTIVE.values())
    for event, _ in jobs:
        event.set()
    deadline = monotonic() + policy()["limits"]["model_timeout"] + policy()["limits"]["download_seconds"]
    for _, thread in jobs:
        thread.join(max(0.0, deadline - monotonic()))
