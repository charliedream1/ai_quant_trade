"""Independent command-line processes drive the same isolated alpha API."""

import json


def test_cli_import_create_human_candidate_and_seal(cli_command, tmp_path, market_payload, workflow_fixture):
    path = tmp_path / "market.json"
    path.write_text(json.dumps(market_payload), encoding="utf-8")
    dataset = cli_command("alpha", "import", "--kind", "market", "--file", str(path))["data"]["id"]
    request = tmp_path / "study.yaml"
    request.write_text(
        json.dumps(
            {"name": "CLI隔离研究", "dataset_id": dataset, "batch_size": 1, "policy": workflow_fixture["policy"]}
        ),
        encoding="utf-8",
    )
    study = cli_command("alpha", "create", "--file", str(request))["data"]["id"]
    candidate = tmp_path / "candidate.json"
    candidate.write_text(
        json.dumps(
            {"hypothesis": workflow_fixture["idea"]["ideas"][0], "implementation": workflow_fixture["implement"]}
        ),
        encoding="utf-8",
    )
    cli_command("alpha", "candidate", str(study), "--file", str(candidate))
    sealed = cli_command("alpha", "seal", str(study))["data"]
    assert sealed["status"] == "sealed"
    assert cli_command("alpha", "show", str(study))["data"]["event_chain_valid"]
    assert cli_command("alpha", "events", str(study))["data"]["items"]
    assert cli_command("alpha", "template", "macro")["data"]["data_rows"] == 0
