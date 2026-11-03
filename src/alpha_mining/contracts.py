"""Internal capabilities cannot be supplied through JSON or CLI request parameters."""

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from src.agent.providers.contracts import ModelSelection


class StudyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    dataset_id: int = Field(gt=0)
    mode: Literal["alpha", "theme", "regime"] = "alpha"
    purpose: str = Field(default="", max_length=2000)
    market: Literal["CN", "US"] = "CN"
    policy: dict[str, Any] = Field(default_factory=dict)
    batch_size: int = Field(default=4, ge=1, le=24)
    models: dict[str, ModelSelection] = Field(default_factory=dict)
    model_call_budget: int = Field(default=32, ge=1, le=256)
    execution: dict[str, Any] = Field(default_factory=dict)
    execution_costs: dict[str, Any] | None = None
    cutoff: str | None = None
    theme: str | None = None
    manual_keywords: list[str] = Field(default_factory=list)
    market_dataset_id: int | None = Field(default=None, gt=0)
    memory_dataset_id: int | None = Field(default=None, gt=0)
    configurations: list[ModelSelection] = Field(default_factory=list)
    asset_mapping: dict[str, str] = Field(default_factory=dict)
    decision_dates: list[str] = Field(default_factory=list)
    regime: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ResearchPermit:
    study_id: int
    candidate_id: int
    scores: pd.DataFrame
    targets: bool = False
