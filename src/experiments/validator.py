"""
Validate declarative experiment configuration.

Input: configs/experiments.yaml or a caller-provided YAML path.

Processing: Parses experiment declarations with Pydantic and checks suites, models, metrics, and repetitions.

Output: Validated ExperimentConfig objects or ValueError with consistency problems.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


VALID_MODELS = {
    "gpt-5.5",
    "gpt-5.4",
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "qwen2.5:7b-instruct-q4_K_M",
}
GENERATIVE_MODELS = VALID_MODELS
VALID_SUITES = {
    "classification",
    "reasoning",
    "extraction",
    "find_replace",
    "nested_data",
    "tabular",
    "long_context",
    "multi_agent",
    "transversal",
}
ALLOWED_METRICS = {
    "accuracy",
    "accuracy_final_answer",
    "field_f1",
    "schema_compliance",
    "field_f1_schema_compliance",
    "pass_at_1",
    "accuracy_token",
    "token_input",
    "token_output",
    "token_ratio_output_input",
    "cost_usd",
    "success_rate",
    "success_rate_total_input_tokens",
    "accuracy_citation_fidelity",
}


class ManipulatedVariable(BaseModel):
    """Variable manipulated by one experiment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    axis: Literal["q-in", "q-out", "instruction_position", "pure_vs_mixed", "state_serialization", "cost_probe"]
    levels: tuple[str, ...] = Field(min_length=1)
    dimensions: tuple[str, ...] = ()
    notes: str | None = None


class RepetitionPlan(BaseModel):
    """Seed or repeated-call plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seeds_or_repeated_calls: int = Field(ge=3)
    temperature_policy: Literal["seed_when_supported_else_repeated_calls", "repeat_calls"]


class Hypothesis(BaseModel):
    """Expected outcome and falsification threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    expected: str = Field(min_length=1)
    falsification_threshold: str = Field(min_length=1)


class Experiment(BaseModel):
    """One protocol question declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str = Field(min_length=1)
    suite: str = Field(min_length=1)
    manipulated_variable: ManipulatedVariable
    models: tuple[str, ...] = Field(min_length=1)
    metrics: tuple[str, ...] = Field(min_length=1)
    repetition: RepetitionPlan
    fixed_confounders: tuple[str, ...] = Field(min_length=1)
    hypothesis: Hypothesis


class ExperimentConfig(BaseModel):
    """Top-level experiment configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiments: tuple[Experiment, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_question_ids(self) -> ExperimentConfig:
        id_counts = Counter(experiment.question_id for experiment in self.experiments)
        duplicates = sorted(question_id for question_id, count in id_counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate experiment question_id values: {duplicates}")
        return self


def load_experiments_config(path: str | Path = "configs/experiments.yaml") -> ExperimentConfig:
    """Load and validate schema shape without registry consistency checks."""

    raw = _load_yaml_mapping(path)
    try:
        return ExperimentConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(_format_validation_error(exc)) from exc


def validate_experiments_config(path: str | Path = "configs/experiments.yaml") -> ExperimentConfig:
    """Load experiments and check references against suite/model/metric registries."""

    config = load_experiments_config(path)
    errors: list[str] = []
    for experiment in config.experiments:
        _collect_reference_errors(experiment, errors)
    if errors:
        raise ValueError("; ".join(errors))
    return config


def _load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("experiments config must be a YAML mapping")
    return raw


def _format_validation_error(exc: ValidationError) -> str:
    return str(exc).replace("greater than or equal to 3", "at least 3")


def _collect_reference_errors(experiment: Experiment, errors: list[str]) -> None:
    if experiment.suite not in VALID_SUITES:
        errors.append(f"{experiment.question_id}: unknown suite {experiment.suite!r}")
    unknown_models = sorted(set(experiment.models) - VALID_MODELS)
    if unknown_models:
        errors.append(f"{experiment.question_id}: unknown model(s) {unknown_models}")
    unknown_metrics = sorted(set(experiment.metrics) - ALLOWED_METRICS)
    if unknown_metrics:
        errors.append(f"{experiment.question_id}: unknown metric(s) {unknown_metrics}")
