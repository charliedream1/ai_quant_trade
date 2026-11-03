"""Common generation selection contract; no dependency on a research family."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def merge_selection(base: dict, override: dict) -> dict:
    selected = {**base, **override}
    if selected.get("backend", "api") != "api":
        selected.pop("model_id", None)
    elif override.get("backend") == "api":
        selected.pop("model_name", None)
    return selected


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    backend: Literal["api", "codex", "qoder", "trae", "codebuddy"] = "api"
    model_id: int | None = Field(default=None, gt=0)
    model_name: str = Field(default="", max_length=200)
    reasoning_effort: Literal["", "low", "medium", "high", "xhigh"] = ""
    enable_thinking: bool | None = None

    @model_validator(mode="after")
    def check_cli_identity(self):
        if self.backend != "api" and self.model_id is not None:
            raise ValueError("CLI使用model_name，不接受API model_id冒充不同模型配置")
        return self
