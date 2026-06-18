from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator import ExperimentOrchestrator, OrchestratorPaths, _default_runner_factory
from runners.ollama_runner import OllamaRunner
from runners.base import ModelRunner, RunParams, RunResult


D5_MODEL_COUNT = 6
D5_LEVEL_COUNT = 4
D5_SEED_COUNT = 3


def test_dry_run_counts_calls_for_limited_d5_without_api_calls(tmp_path: Path) -> None:
    runner = FakeRunner()
    orchestrator = _orchestrator(tmp_path, runner)

    summary = orchestrator.run_experiment("D5", dry_run=True, limit=2)

    assert summary.experiment_ids == ("D5",)
    assert summary.planned_calls == D5_MODEL_COUNT * D5_LEVEL_COUNT * D5_SEED_COUNT * 2
    assert summary.api_calls_made == 0
    assert summary.skipped_existing == 0
    assert runner.calls == []
    assert summary.estimated_cost_usd >= 0.0


def test_resume_skips_existing_raw_call(tmp_path: Path) -> None:
    runner = FakeRunner()
    orchestrator = _orchestrator(tmp_path, runner)
    first_call = orchestrator.plan_experiment("D5", limit=1)[0]
    orchestrator.raw_store.write(
        first_call.call_id,
        {
            "call_id": first_call.call_id,
            "experiment_id": "D5",
            "result": {
                "run_id": "existing",
                "model": first_call.model,
                "response_text": "subnet-0000",
                "input_tokens": 10,
                "output_tokens": 2,
                "error": None,
                "response_time_seconds": 0.01,
                "params_used": {"model": first_call.model},
            },
        },
    )

    summary = orchestrator.run_experiment("D5", dry_run=False, limit=1)

    assert summary.planned_calls == D5_MODEL_COUNT * D5_LEVEL_COUNT * D5_SEED_COUNT
    assert summary.skipped_existing == 1
    assert summary.api_calls_made == summary.planned_calls - 1
    assert first_call.call_id not in runner.call_ids


def test_dry_run_reports_existing_calls_as_skipped(tmp_path: Path) -> None:
    runner = FakeRunner()
    orchestrator = _orchestrator(tmp_path, runner)
    first_call = orchestrator.plan_experiment("D5", limit=1)[0]
    orchestrator.raw_store.write(first_call.call_id, {"call_id": first_call.call_id})

    summary = orchestrator.run_experiment("D5", dry_run=True, limit=1)

    assert summary.planned_calls == D5_MODEL_COUNT * D5_LEVEL_COUNT * D5_SEED_COUNT
    assert summary.skipped_existing == 1
    assert summary.api_calls_made == 0


def test_runner_factory_called_once_per_model_not_per_call(tmp_path: Path) -> None:
    calls_to_factory: list[str] = []
    runner = FakeRunner()

    def factory(model: str) -> FakeRunner:
        calls_to_factory.append(model)
        return runner

    orchestrator = ExperimentOrchestrator(
        paths=OrchestratorPaths(results_dir=tmp_path / "results"),
        runner_factory=factory,
    )

    orchestrator.run_experiment("D5", dry_run=False, limit=2)

    assert calls_to_factory == [
        "gpt-5.5",
        "gpt-5.4",
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "qwen2.5:7b-instruct-q4_K_M",
    ]


def test_limit_must_be_positive(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, FakeRunner())

    with pytest.raises(ValueError, match="limit must be positive"):
        orchestrator.run_experiment("D5", dry_run=True, limit=0)


def test_limit_applies_to_first_n_items_per_cell(tmp_path: Path) -> None:
    runner = FakeRunner()
    orchestrator = _orchestrator(tmp_path, runner)

    calls = orchestrator.plan_experiment("D5", limit=3)
    cell_counts: dict[tuple[str, str, int], int] = {}
    for call in calls:
        key = (call.model, call.level, call.seed)
        cell_counts[key] = cell_counts.get(key, 0) + 1

    assert set(cell_counts.values()) == {3}
    assert len(cell_counts) == D5_MODEL_COUNT * D5_LEVEL_COUNT * D5_SEED_COUNT


def test_cli_dry_run_prints_counts(tmp_path: Path, capsys) -> None:
    from run import main

    exit_code = main(
        [
            "--experiment",
            "D5",
            "--dry-run",
            "--limit",
            "1",
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Experiment(s): D5" in output
    assert "Planned calls: 72" in output
    assert "API calls made: 0" in output
    assert "Estimated cost USD:" in output


def test_default_runner_factory_supports_qwen() -> None:
    assert isinstance(_default_runner_factory("qwen2.5:7b-instruct-q4_K_M"), OllamaRunner)


def _orchestrator(tmp_path: Path, runner: FakeRunner) -> ExperimentOrchestrator:
    return ExperimentOrchestrator(
        paths=OrchestratorPaths(results_dir=tmp_path / "results"),
        runner_factory=lambda model: runner,
    )


class FakeRunner(ModelRunner):
    def __init__(self) -> None:
        super().__init__(raw_log_dir="unused")
        self.calls: list[tuple[str, RunParams]] = []
        self.call_ids: set[str] = set()

    def run(self, prompt: str, params: RunParams) -> RunResult:
        self.calls.append((prompt, params))
        call_id = str(params.metadata["call_id"])
        self.call_ids.add(call_id)
        return RunResult(
            run_id=f"run-{len(self.calls)}",
            model=params.model,
            response_text=str(params.metadata["gold_answer"]),
            input_tokens=max(1, len(prompt.split())),
            output_tokens=3,
            error=None,
            response_time_seconds=0.01,
            params_used={"model": params.model, "model_version": f"{params.model}-snapshot"},
        )

    def _execute(self, prompt: str, params: RunParams, params_used: dict) -> tuple[str, int | None, int | None, dict]:
        raise NotImplementedError
