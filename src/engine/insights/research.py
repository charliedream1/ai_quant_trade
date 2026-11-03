"""Fixed Skill tasks, bounded textual ReAct, and attributable report sections."""

import json
import re
from collections.abc import Callable
from typing import Any

from json_repair import loads as repair_json_loads

from .backend import generate_text

TOOL_PATTERN = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)


def parse_report(text: str, evidence: dict[str, Any], config: dict[str, Any], kind: str) -> dict[str, Any]:
    report = repair_json_loads(text)
    if (
        not isinstance(report, dict)
        or not isinstance(report.get("sections"), list)
        or not isinstance(report.get("summary"), str)
        or not report["summary"].strip()
    ):
        raise ValueError(config["messages"]["invalid_result"])
    valid_ids = {row["id"] for row in evidence["sources"]}
    sections = []
    for section in report["sections"]:
        if not isinstance(section, dict) or not isinstance(section.get("paragraphs"), list):
            raise ValueError(config["messages"]["invalid_result"])
        references = section.get("source_ids")
        if (
            not isinstance(references, list)
            or not references
            or any(not isinstance(item, str) or item not in valid_ids for item in references)
        ):
            raise ValueError(config["messages"]["invalid_result"])
        paragraphs = section["paragraphs"]
        if (
            not section.get("heading")
            or not paragraphs
            or any(not isinstance(item, str) or not item.strip() for item in paragraphs)
        ):
            raise ValueError(config["messages"]["invalid_result"])
        sections.append({"heading": str(section["heading"]), "paragraphs": paragraphs, "source_ids": references})
    headings = {item["heading"] for item in sections}
    if not set(config["tasks"][kind]["sections"]).issubset(headings):
        raise ValueError(config["messages"]["invalid_result"])
    for key in ("risks", "missing"):
        if not isinstance(report.get(key), list) or any(not isinstance(item, str) for item in report[key]):
            raise ValueError(config["messages"]["invalid_result"])
    return {
        "title": str(report.get("title") or config["tasks"][kind]["label"]),
        "summary": str(report["summary"]),
        "sections": sections,
        "risks": report["risks"],
        "missing": report["missing"],
    }


def run_research(
    payload: dict[str, Any],
    evidence: dict[str, Any],
    skill_text: str,
    resources: dict[str, Any],
    config: dict[str, Any],
    emit: Callable[..., None],
    save_prompt: Callable[[str], None],
    generate: Callable[..., str] = generate_text,
) -> dict[str, Any]:
    task = config["tasks"][payload["kind"]]
    prompt = config["prompts"]["request"].format(
        system=config["prompts"]["system"],
        instruction=task["instruction"],
        sections=json.dumps(task["sections"], ensure_ascii=False),
        request=json.dumps(payload, ensure_ascii=False),
        skill=skill_text,
        resource_index=json.dumps(list(resources), ensure_ascii=False),
        evidence=json.dumps(evidence, ensure_ascii=False),
        protocol=config["prompts"]["protocol"],
    )
    if len(prompt) > config["defaults"]["max_prompt_chars"]:
        raise ValueError(config["messages"]["invalid_result"])
    source_map = {item["id"]: item for item in evidence["sources"]}
    for turn in range(config["defaults"]["max_turns"]):
        if len(prompt) > config["defaults"]["max_prompt_chars"]:
            raise ValueError(config["messages"]["invalid_result"])
        save_prompt(prompt)
        emit("stage", config["messages"]["model_started"], {"backend": payload["backend"], "turn": turn + 1})
        text = generate(prompt, payload, config, emit)
        calls = TOOL_PATTERN.findall(text)
        if not calls:
            emit("stage", config["messages"]["validating"])
            try:
                return parse_report(text, evidence, config, payload["kind"])
            except ValueError as exc:
                emit("validation", str(exc), {"status": "retry"})
                prompt += "\n" + config["prompts"]["retry"].format(error=str(exc)) + "\n" + text
                continue
        observations = []
        for raw in calls:
            call = repair_json_loads(raw)
            name = call.get("name") if isinstance(call, dict) else None
            args = call.get("arguments") or {} if isinstance(call, dict) else {}
            emit("action", config["messages"]["tool_started"], {"name": name, "arguments": args})
            if name == "skill_read" and isinstance(args, dict) and args.get("resource") in resources:
                result = resources[args["resource"]]
            elif name == "evidence_read" and isinstance(args, dict) and args.get("source_id") in source_map:
                result = source_map[args["source_id"]]
            else:
                result = {"error": config["messages"]["unsupported_tool"]}
            observation = {"name": name, "result": result}
            emit("observation", config["messages"]["tool_finished"], observation)
            observations.append(observation)
        prompt += "\n" + config["prompts"]["observation"].format(
            observation=json.dumps(observations, ensure_ascii=False)
        )
        if len(prompt) > config["defaults"]["max_prompt_chars"]:
            raise ValueError(config["messages"]["invalid_result"])
    raise ValueError(config["messages"]["invalid_result"])
