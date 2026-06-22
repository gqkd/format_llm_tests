"""
Run configured benchmark experiments end to end.

Input: Experiment ids, suite items, prompt builders, model runners, scorers, and result paths.

Processing: Plans deterministic model/task/format/seed calls, resumes completed raw calls, scores outputs, and aggregates results.

Output: Raw JSONL call records, aggregated JSON summaries, and run summary objects.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

from experiments.validator import Experiment, validate_experiments_config
from runners.anthropic_runner import AnthropicRunner
from runners.base import ModelRunner, RunParams, RunResult
from runners.ollama_runner import OllamaRunner
from runners.openai_runner import OpenAIRunner
from scoring.accuracy import exact_match_score
from scoring.code_exec import score_python_code_pass_at_1
from scoring.cost import PricingTable, load_pricing
from scoring.schema_compliance import validate_json_schema
from suites import classification, extraction, find_replace, long_context, multi_agent, nested_data, reasoning, tabular
from suites.base import SuiteItem
from templating.canonical import Format, InstructionBlock
from templating.prompt_builder import (
    ExperimentMode,
    InstructionPosition,
    OutputRequest,
    PromptTask,
    build_prompt,
)


RunnerFactory = Callable[[str], ModelRunner]

SUITE_LOADERS: dict[str, Callable[[], list[SuiteItem]]] = {
    "classification": classification.load_items,
    "reasoning": reasoning.load_items,
    "extraction": extraction.load_items,
    "find_replace": find_replace.load_items,
    "nested_data": nested_data.load_items,
    "tabular": tabular.load_items,
    "long_context": long_context.load_items,
    "multi_agent": multi_agent.load_items,
}

FORMAT_LEVELS = {
    "prose": Format.PLAIN,
    "plain": Format.PLAIN,
    "markdown": Format.MARKDOWN,
    "markdown_table": Format.MARKDOWN,
    "xml": Format.XML,
    "xml_document": Format.XML,
    "json": Format.JSON,
    "json_records": Format.JSON,
    "json_array": Format.JSON,
    "yaml": Format.YAML,
    "csv": Format.CSV,
    "toon": Format.TOON,
    "compact_pseudocode_yaml": Format.YAML,
    "compact_pseudocode": Format.YAML,
}
OUTPUT_FORMAT_LEVELS = {
    "plain": Format.PLAIN,
    "markdown": Format.MARKDOWN,
    "xml": Format.XML,
    "yaml": Format.YAML,
    "json": Format.JSON,
    "prompt_only_json": Format.JSON,
    "json_strict_direct": Format.JSON,
    "reason_then_convert": Format.JSON,
    "structured_native": Format.JSON,
    "json_strict": Format.JSON,
}
INSTRUCTION_POSITIONS = {
    "head": InstructionPosition.HEAD,
    "tail": InstructionPosition.TAIL,
    "both": InstructionPosition.BOTH,
}
DEFAULT_SEEDS = (0, 1, 2)


@dataclass(frozen=True)
class OrchestratorPaths:
    """Filesystem paths used by the orchestrator."""

    results_dir: Path = Path("results")
    experiments_config: Path = Path("configs/experiments.yaml")
    pricing_config: Path = Path("configs/pricing.yaml")

    @property
    def raw_dir(self) -> Path:
        return self.results_dir / "raw"

    @property
    def aggregated_dir(self) -> Path:
        return self.results_dir / "aggregated"


@dataclass(frozen=True)
class PlannedCall:
    """One deterministic API call unit."""

    call_id: str
    experiment_id: str
    model: str
    item: SuiteItem
    level: str
    seed: int
    prompt: str
    native_output: dict[str, Any] | None
    input_format: str | None
    output_format: str | None
    reasoning_effort: str


@dataclass(frozen=True)
class OrchestratorSummary:
    """Run summary for CLI and tests."""

    experiment_ids: tuple[str, ...]
    planned_calls: int
    api_calls_made: int
    skipped_existing: int
    estimated_cost_usd: float
    aggregated_paths: tuple[Path, ...] = ()


@dataclass
class _RunAccumulator:
    planned_calls: int = 0
    api_calls_made: int = 0
    skipped_existing: int = 0
    estimated_cost_usd: float = 0.0
    aggregated_paths: list[Path] = field(default_factory=list)


class RawResultStore:
    """Deterministic raw result storage keyed by orchestrator call id."""

    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir

    def exists(self, call_id: str) -> bool:
        return self.path_for(call_id).exists()

    def path_for(self, call_id: str) -> Path:
        return self.raw_dir / f"{call_id}.jsonl"

    def write(self, call_id: str, record: dict[str, Any]) -> Path:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(call_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")
        return path


class ExperimentOrchestrator:
    """Coordinate suite loading, prompt generation, model calls, scoring, and aggregation."""

    def __init__(
        self,
        *,
        paths: OrchestratorPaths | None = None,
        runner_factory: RunnerFactory | None = None,
    ) -> None:
        self.paths = paths or OrchestratorPaths()
        self.raw_store = RawResultStore(self.paths.raw_dir)
        self.runner_factory = runner_factory or _default_runner_factory
        self.pricing = _safe_load_pricing(self.paths.pricing_config)

    def run_experiment(self, experiment_id: str, *, dry_run: bool = False, limit: int | None = None) -> OrchestratorSummary:
        _validate_limit(limit)
        experiments = self._select_experiments(experiment_id)
        accumulator = _RunAccumulator()
        for experiment in experiments:
            calls = self.plan_experiment(experiment.question_id, limit=limit)
            accumulator.planned_calls += len(calls)
            accumulator.estimated_cost_usd += sum(self._estimate_call_cost(call) for call in calls)
            accumulator.skipped_existing += sum(self.raw_store.exists(call.call_id) for call in calls)
            if dry_run:
                continue
            aggregate_path = self._execute_calls(experiment, calls, accumulator)
            accumulator.aggregated_paths.append(aggregate_path)
        return OrchestratorSummary(
            experiment_ids=tuple(experiment.question_id for experiment in experiments),
            planned_calls=accumulator.planned_calls,
            api_calls_made=accumulator.api_calls_made,
            skipped_existing=accumulator.skipped_existing,
            estimated_cost_usd=accumulator.estimated_cost_usd,
            aggregated_paths=tuple(accumulator.aggregated_paths),
        )

    def plan_experiment(self, experiment_id: str, *, limit: int | None = None) -> list[PlannedCall]:
        _validate_limit(limit)
        experiment = self._experiment_by_id(experiment_id)
        items = _items_for_experiment(experiment)
        if limit is not None:
            items = items[:limit]
        seeds = tuple(range(experiment.repetition.seeds_or_repeated_calls))
        return [
            _planned_call(experiment, model, level, effort, seed, item)
            for model, level, effort, seed, item in _call_matrix(experiment, seeds, items)
        ]

    def _execute_calls(
        self,
        experiment: Experiment,
        calls: list[PlannedCall],
        accumulator: _RunAccumulator,
    ) -> Path:
        records: list[dict[str, Any]] = []
        runners: dict[str, ModelRunner] = {}
        batch_started_at = datetime.now(UTC).isoformat()
        for index, call in enumerate(calls, start=1):
            if self.raw_store.exists(call.call_id):
                continue
            print(f"[{experiment.question_id}] call {index}/{len(calls)} model={call.model} level={call.level} seed={call.seed}")
            runner = _runner_for(call.model, runners, self.runner_factory)
            result = runner.run(call.prompt, _run_params(call, batch_started_at))
            accumulator.api_calls_made += 1
            score = _score_result(call.item, result)
            model_version = str(result.params_used.get("model_version", result.model))
            record = _raw_record(call, result, score, batch_started_at, model_version)
            self.raw_store.write(call.call_id, record)
            records.append(record)
        return self._write_aggregate(experiment, records, calls)

    def _write_aggregate(self, experiment: Experiment, records: list[dict[str, Any]], calls: list[PlannedCall]) -> Path:
        self.paths.aggregated_dir.mkdir(parents=True, exist_ok=True)
        path = self.paths.aggregated_dir / f"{experiment.question_id}.json"
        payload = {
            "experiment_id": experiment.question_id,
            "planned_calls": len(calls),
            "new_records": len(records),
            "generated_at": datetime.now(UTC).isoformat(),
            "scores": [record["score"] for record in records],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _select_experiments(self, experiment_id: str) -> tuple[Experiment, ...]:
        config = validate_experiments_config(self.paths.experiments_config)
        if experiment_id == "all":
            return config.experiments
        matches = tuple(experiment for experiment in config.experiments if experiment.question_id == experiment_id)
        if not matches:
            raise ValueError(f"unknown experiment id: {experiment_id}")
        return matches

    def _experiment_by_id(self, experiment_id: str) -> Experiment:
        return self._select_experiments(experiment_id)[0]

    def _estimate_call_cost(self, call: PlannedCall) -> float:
        input_tokens = _estimate_tokens(call.prompt)
        model_pricing = self.pricing.models.get(call.model)
        if model_pricing is None:
            return 0.0
        return input_tokens / 1_000_000 * model_pricing.input_per_million


def _items_for_experiment(experiment: Experiment) -> list[SuiteItem]:
    if experiment.question_id == "D10":
        return classification.load_items()[:10] + reasoning.load_items()[:10]
    loader = SUITE_LOADERS[experiment.suite]
    return loader()


def _call_matrix(
    experiment: Experiment,
    seeds: tuple[int, ...],
    items: list[SuiteItem],
) -> Iterable[tuple[str, str, str, int, SuiteItem]]:
    return product(experiment.models, experiment.manipulated_variable.levels, _effort_levels_for(experiment), seeds, items)


def _effort_levels_for(experiment: Experiment) -> tuple[str, ...]:
    return experiment.manipulated_variable.effort_levels or ("medium",)


def _validate_limit(limit: int | None) -> None:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")


def _runner_for(model: str, runners: dict[str, ModelRunner], runner_factory: RunnerFactory) -> ModelRunner:
    if model not in runners:
        runners[model] = runner_factory(model)
    return runners[model]


def _planned_call(experiment: Experiment, model: str, level: str, effort: str, seed: int, item: SuiteItem) -> PlannedCall:
    built_prompt = _build_call_prompt(experiment, level, item)
    call_id = _call_id(experiment.question_id, model, item.item_id, level, effort, seed)
    return PlannedCall(
        call_id=call_id,
        experiment_id=experiment.question_id,
        model=model,
        item=item,
        level=level,
        seed=seed,
        prompt=built_prompt.message,
        native_output=built_prompt.native_output,
        input_format=_input_format_for(experiment, level),
        output_format=_output_format_for(experiment, level),
        reasoning_effort=effort,
    )


def _build_call_prompt(experiment: Experiment, level: str, item: SuiteItem):
    task = _prompt_task(item)
    if experiment.manipulated_variable.axis in {"q-out", "cost_probe"}:
        return build_prompt(
            task,
            input_format=Format.MARKDOWN,
            experiment_mode=ExperimentMode.Q_OUT,
            output_request=_output_request(level, item),
        )
    if experiment.manipulated_variable.axis == "instruction_position":
        return build_prompt(
            task,
            input_format=Format.MARKDOWN,
            experiment_mode=ExperimentMode.Q_IN,
            instruction_position=INSTRUCTION_POSITIONS[level],
        )
    return build_prompt(
        task,
        input_format=FORMAT_LEVELS.get(level, Format.MARKDOWN),
        experiment_mode=ExperimentMode.Q_IN,
    )


def _prompt_task(item: SuiteItem) -> PromptTask:
    query = str(item.metadata.get("question") or item.metadata.get("path") or _default_query(item))
    return PromptTask(
        task_id=item.item_id,
        instructions=InstructionBlock(
            role="benchmark participant",
            context=f"Suite: {item.suite.name}. Metric: {item.metric}.",
            instructions=("Answer the query using only the provided task content.",),
        ),
        content=item.content,
        query=query,
    )


def _default_query(item: SuiteItem) -> str:
    if item.metric == "pass_at_1":
        return "Return corrected code that passes the provided tests."
    if item.output_schema is not None:
        return "Extract the fields required by the schema."
    return "Return the gold answer requested by this benchmark item."


def _output_request(level: str, item: SuiteItem) -> OutputRequest:
    if level in {"structured_native", "json_strict", "json"} and item.output_schema is not None:
        return OutputRequest.structured_native(Format.JSON, item.output_schema.model_json_schema())
    output_format = OUTPUT_FORMAT_LEVELS.get(level, Format.JSON)
    return OutputRequest.text_format(output_format)


def _input_format_for(experiment: Experiment, level: str) -> str | None:
    if experiment.manipulated_variable.axis in {"q-in", "state_serialization"}:
        return level
    return None


def _output_format_for(experiment: Experiment, level: str) -> str | None:
    if experiment.manipulated_variable.axis in {"q-out", "cost_probe"}:
        return level
    return None


def _run_params(call: PlannedCall, batch_started_at: str) -> RunParams:
    return RunParams(
        model=call.model,
        task_id=call.item.item_id,
        input_format=call.input_format,
        output_format=call.output_format,
        seed=call.seed,
        reasoning_effort=call.reasoning_effort,
        native_output=call.native_output,
        metadata={
            "call_id": call.call_id,
            "experiment_id": call.experiment_id,
            "level": call.level,
            "gold_answer": call.item.gold_answer,
            "batch_started_at": batch_started_at,
        },
    )


def _score_result(item: SuiteItem, result: RunResult) -> dict[str, Any]:
    if result.error is not None:
        return {"metric": item.metric, "is_valid": False, "error": result.error}
    if item.metric == "pass_at_1" and item.unit_tests is not None:
        code_score = score_python_code_pass_at_1(result.response_text, item.unit_tests)
        return {"metric": item.metric, "passed": code_score.passed, "error": code_score.error}
    if item.output_schema is not None:
        schema_score = validate_json_schema(result.response_text, item.output_schema)
        return {"metric": item.metric, "schema_valid": schema_score.is_valid, "error": schema_score.error_message}
    accuracy = exact_match_score(result.response_text, item.gold_answer)
    return {"metric": item.metric, "is_correct": accuracy.is_correct}


def _raw_record(
    call: PlannedCall,
    result: RunResult,
    score: dict[str, Any],
    batch_started_at: str,
    model_version: str,
) -> dict[str, Any]:
    return {
        "call_id": call.call_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "batch_started_at": batch_started_at,
        "experiment_id": call.experiment_id,
        "model": call.model,
        "model_version": model_version,
        "task_id": call.item.item_id,
        "level": call.level,
        "reasoning_effort": call.reasoning_effort,
        "seed": call.seed,
        "input_format": call.input_format,
        "output_format": call.output_format,
        "result": result.model_dump(mode="json"),
        "score": score,
    }


def _call_id(experiment_id: str, model: str, task_id: str, level: str, effort: str, seed: int) -> str:
    key = f"{experiment_id}|{model}|{task_id}|{level}|{effort}|{seed}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"{experiment_id}-{digest}"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _safe_load_pricing(path: Path) -> PricingTable:
    try:
        return load_pricing(path)
    except Exception:  # noqa: BLE001 - missing or partial prices should not block dry-run planning.
        return PricingTable(models={})


def _default_runner_factory(model: str) -> ModelRunner:
    if model.startswith("gpt-"):
        return OpenAIRunner()
    if model.startswith("claude-"):
        return AnthropicRunner()
    if model == "qwen2.5:7b-instruct-q4_K_M":
        return OllamaRunner()
    raise ValueError(f"unsupported model: {model}")
