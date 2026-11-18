"""Declared local CLI protocol fixture; not an external model or billing claim."""

import json
import sys

from src.core.page_analysis_snapshot import analysis_config

prompt = sys.stdin.read()
if "Page evidence analysis" not in prompt:
    raise ValueError("Actual Skill prompt was not supplied")
report = {
    "title": "Declared native CLI report",
    "summary": "Protocol acceptance only",
    "risks": [],
    "missing": [],
    "sections": [
        {"heading": heading, "paragraphs": ["Declared evidence interpretation"], "source_ids": ["E1"]}
        for heading in analysis_config()["sections"]
    ],
}
for event in (
    {"type": "thread.started", "thread_id": "declared"},
    {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(report)}},
    {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 100}},
):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()
