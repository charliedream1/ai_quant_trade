from datetime import timedelta

from src.core.repository import Repository
from src.core.timeutil import utc_now, utc_now_iso
from src.scheduler.jobs import execute_scheduled_job


def test_data_maintain_prunes_cache_and_repairs_fts(client):
    repo = Repository()
    old_time = _days_ago(45)
    fresh_time = utc_now_iso()
    source = repo.insert(
        "remote_sources",
        {
            "source_type": "feishu",
            "name": "maintain-source",
            "conn_config": "{}",
            "enabled": 1,
            "status": "connected",
            "created_at": fresh_time,
            "updated_at": fresh_time,
        },
    )
    repo.insert(
        "remote_docs_cache",
        {
            "source_id": source["id"],
            "remote_id": "old-doc",
            "title": "旧缓存",
            "summary": "",
            "content": "",
            "local_path": "",
            "fetched_at": old_time,
            "created_at": old_time,
            "updated_at": old_time,
        },
    )
    repo.insert(
        "remote_docs_cache",
        {
            "source_id": source["id"],
            "remote_id": "fresh-doc",
            "title": "新缓存",
            "summary": "",
            "content": "",
            "local_path": "",
            "fetched_at": fresh_time,
            "created_at": fresh_time,
            "updated_at": fresh_time,
        },
    )
    repo.insert(
        "kb_qa_history",
        {
            "question": "旧问答",
            "answer": "旧答案",
            "cited_docs": "",
            "model_name": "",
            "created_at": old_time,
        },
    )
    repo.insert(
        "kb_documents",
        {
            "title": "索引修复样例",
            "doc_type": "note",
            "category_id": 0,
            "summary": "FTS should be repaired",
            "content": "动量因子观察",
            "file_path": "",
            "source": "",
            "tags": "",
            "status": "ready",
            "imported_at": fresh_time,
            "updated_at": fresh_time,
        },
    )
    repo.db.execute("DELETE FROM kb_documents_fts")

    result = execute_scheduled_job(
        {
            "job_type": "data_maintain",
            "target": {
                "news_retain_days": 0,
                "remote_cache_retain_days": 30,
                "qa_history_retain_days": 30,
                "execution_keep_per_job": 0,
                "rebuild_fts_on_mismatch": True,
                "optimize_fts": True,
                "wal_checkpoint": False,
                "database_optimize": False,
            },
        }
    )

    assert result["status"] == "成功"
    assert result["details"]["deleted_remote_cache"] == 1
    assert result["details"]["deleted_qa_history"] == 1
    assert result["details"]["fts"]["kb_documents_fts"]["rebuilt"] is True
    assert repo.db.scalar("SELECT COUNT(*) FROM remote_docs_cache") == 1
    assert repo.db.scalar("SELECT COUNT(*) FROM kb_qa_history") == 0
    assert repo.db.scalar("SELECT COUNT(*) FROM kb_documents_fts") == 1


def _days_ago(days: int) -> str:
    return (utc_now() - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
