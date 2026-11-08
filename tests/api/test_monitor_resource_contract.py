"""Shared UI/API/CLI import, scope and monitor task contracts."""

import time
from pathlib import Path


def test_pool_templates_preview_commit_and_invalid_batch(client):
    pool = client.post("/api/v1/resource-pools", json={"name": "validated"}).json()["data"]
    for kind in ("csv", "xlsx"):
        response = client.get("/api/v1/resource-pools/templates/" + kind)
        assert response.status_code == 200 and response.content
    content = b"symbol,weight\n000001,0\n600519,1\n"
    url = f"/api/v1/resource-pools/{pool['id']}/import"
    preview = client.post(url + "/preview", files={"file": ("pool.csv", content)}).json()["data"]
    assert preview["valid"] and preview["counts"]["add"] == 2
    assert not client.get(f"/api/v1/resource-pools/{pool['id']}/items").json()["data"]
    imported = client.post(
        url, params={"preview_hash": preview["preview_hash"]}, files={"file": ("pool.csv", content)}
    ).json()
    assert imported["code"] == 0 and imported["data"]["added"] == 2
    stale = client.post(
        url, params={"preview_hash": preview["preview_hash"]}, files={"file": ("pool.csv", content)}
    ).json()
    assert stale["code"] != 0
    invalid = client.post(url, files={"file": ("bad.csv", b"symbol,weight\n300750,1\n688981,NaN\n")}).json()
    assert invalid["code"] != 0
    assert len(client.get(f"/api/v1/resource-pools/{pool['id']}/items").json()["data"]) == 2


def test_cli_preview_preserves_codes_and_monitor_uses_explicit_backend(cli_command):
    pool = cli_command("pool", "create", "--name", "preview-cli")["data"]
    path = Path(__file__).resolve().parents[2] / "egs/examples/resource_pool_templates/universe.csv"
    preview = cli_command("pool", "preview", pool["id"], "--file", path)["data"]
    assert preview["valid"] and preview["rows"][0]["symbol"] == "000001"
    assert not cli_command("pool", "items", pool["id"])["data"]
    cli_command("pool", "import", pool["id"], "--file", path)
    definitions = cli_command("factor", "definitions")["data"]
    assert len(definitions) == 8
    universes = cli_command("factor", "universes")["data"]
    assert {"csi300", "resource", "holdings"} <= {row["id"] for row in universes}


def test_monitor_job_has_real_progress_and_report(client):
    job = client.post("/api/v1/factors/jobs", json={"universe_text": "600519,300750,000001,688981,300124"}).json()[
        "data"
    ]
    deadline = time.monotonic() + 60
    result = None
    while time.monotonic() < deadline:
        result = client.get("/api/v1/factors/jobs/" + job["job_id"]).json()["data"]
        if result["status"] in {"completed", "failed"}:
            break
        time.sleep(0.1)
    assert result["status"] == "completed", result
    assert result["events"]
    assert result["result"]["coverage"]["requested"] == 5
    assert len(result["result"]["metrics"]) == 8
