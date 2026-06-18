"""
Score qualitative tasks with a cross-vendor LLM judge and calibration checks.

Input: Judge requests, explicit rubrics, judge clients, and human calibration items.

Processing: Enforces different executor/judge vendors, requests structured scores, and measures agreement.

Output: Judge score and calibration result objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DEFAULT_JUDGE_RUBRIC = {
    "rubric_version": "v1",
    "scale": "1-5",
    "criteria": [
        {
            "name": "task_fulfillment",
            "description": "The response satisfies the user-visible task requirements.",
        },
        {
            "name": "factuality",
            "description": "Claims are supported by the provided task context.",
        },
        {
            "name": "clarity",
            "description": "The response is clear, specific, and concise.",
        },
    ],
    "output_schema": {
        "score": "integer 1-5",
        "rationale": "brief evidence-based explanation",
        "rubric_version": "string",
    },
}


class RubricCriterion(BaseModel):
    """One qualitative dimension in the judge rubric."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class JudgeRubric(BaseModel):
    """Explicit rubric and expected structured output contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rubric_version: str = Field(min_length=1)
    scale: str = "1-5"
    criteria: list[RubricCriterion] = Field(min_length=1)
    output_schema: dict[str, str]

    @field_validator("scale")
    @classmethod
    def require_supported_scale(cls, value: str) -> str:
        if value != "1-5":
            raise ValueError("judge rubric scale must be 1-5")
        return value

    @field_validator("output_schema")
    @classmethod
    def require_structured_score_fields(cls, value: dict[str, str]) -> dict[str, str]:
        required_fields = {"score", "rationale", "rubric_version"}
        missing = required_fields - set(value)
        if missing:
            raise ValueError(f"judge output schema missing required fields: {sorted(missing)}")
        return value


class JudgeRequest(BaseModel):
    """Structured input for one judge call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    prompt: str
    response: str
    rubric: JudgeRubric = Field(default_factory=lambda: JudgeRubric.model_validate(DEFAULT_JUDGE_RUBRIC))
    executor_vendor: str
    judge_vendor: str

    @model_validator(mode="after")
    def enforce_cross_vendor_judge(self) -> JudgeRequest:
        if self.executor_vendor.strip().lower() == self.judge_vendor.strip().lower():
            raise ValueError("judge vendor must be different vendor from executor")
        return self


class JudgeScore(BaseModel):
    """Structured qualitative score returned by the judge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    score: int = Field(ge=1, le=5)
    rationale: str
    rubric_version: str
    executor_vendor: str
    judge_vendor: str


class CalibrationItem(BaseModel):
    """One human/judge agreement item."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    human_score: int = Field(ge=1, le=5)
    judge_score: int = Field(ge=1, le=5)


class CalibrationResult(BaseModel):
    """Agreement summary for judge calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_count: int
    agreement: float
    target_agreement: float
    meets_target: bool


class JudgeClient(ABC):
    """Protocol for vendor-specific judge clients."""

    @property
    @abstractmethod
    def vendor(self) -> str:
        """Return the actual vendor backing this judge client."""

    @abstractmethod
    def score(self, request: JudgeRequest) -> dict[str, Any]:
        """Return a structured judge score."""


def score_with_judge(request: JudgeRequest, client: JudgeClient) -> JudgeScore:
    client_vendor = client.vendor.strip().lower()
    request_judge_vendor = request.judge_vendor.strip().lower()
    if client_vendor != request_judge_vendor:
        raise ValueError("judge client vendor must match request judge_vendor")
    if client_vendor == request.executor_vendor.strip().lower():
        raise ValueError("judge vendor must be different vendor from executor")

    raw_score = client.score(request)
    if raw_score["rubric_version"] != request.rubric.rubric_version:
        raise ValueError("judge response rubric_version must match request rubric")
    return JudgeScore(
        item_id=request.item_id,
        score=raw_score["score"],
        rationale=raw_score["rationale"],
        rubric_version=raw_score["rubric_version"],
        executor_vendor=request.executor_vendor,
        judge_vendor=request.judge_vendor,
    )


def calibrate_judge(items: list[CalibrationItem], target_agreement: float = 0.95) -> CalibrationResult:
    if not 0.0 <= target_agreement <= 1.0:
        raise ValueError("target_agreement must be between 0 and 1")
    if not items:
        raise ValueError("calibration requires at least one item")
    agreements = sum(item.human_score == item.judge_score for item in items)
    agreement = agreements / len(items)
    return CalibrationResult(
        item_count=len(items),
        agreement=agreement,
        target_agreement=target_agreement,
        meets_target=agreement >= target_agreement,
    )
