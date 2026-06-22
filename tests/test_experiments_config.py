from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from experiments.validator import (
    ALLOWED_METRICS,
    GENERATIVE_MODELS,
    VALID_MODELS,
    VALID_SUITES,
    ExperimentConfig,
    load_experiments_config,
    validate_experiments_config,
)


CONFIG_PATH = Path("configs/experiments.yaml")
EXPECTED_EXPERIMENT_IDS = {
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7tab",
    "D8",
    "D9",
    "D10",
    "D11",
}


def test_experiments_yaml_declares_all_protocol_questions() -> None:
    config = load_experiments_config(CONFIG_PATH)

    assert isinstance(config, ExperimentConfig)
    assert {experiment.question_id for experiment in config.experiments} == EXPECTED_EXPERIMENT_IDS
    assert len(config.experiments) == 11


def test_experiments_reference_known_suites_models_and_metrics() -> None:
    config = validate_experiments_config(CONFIG_PATH)

    for experiment in config.experiments:
        assert experiment.suite in VALID_SUITES
        assert set(experiment.models).issubset(VALID_MODELS)
        assert set(experiment.metrics).issubset(ALLOWED_METRICS)
        assert experiment.repetition.seeds_or_repeated_calls >= 3
        assert experiment.hypothesis.expected
        assert experiment.hypothesis.falsification_threshold


def test_local_ollama_models_are_registered_with_capabilities() -> None:
    assert "qwen2.5:7b-instruct-q4_K_M" in VALID_MODELS
    assert "qwen2.5:7b-instruct-q4_K_M" in GENERATIVE_MODELS


def test_experiments_keep_required_confounders_fixed() -> None:
    config = validate_experiments_config(CONFIG_PATH)

    for experiment in config.experiments:
        fixed = set(experiment.fixed_confounders)
        assert "format_separator_casing_spacing_constant" in fixed
        if experiment.suite == "classification":
            assert "classification_option_order_rotated" in fixed
        if experiment.suite == "long_context" and experiment.question_id != "D11":
            assert "long_context_needle_position_randomized" in fixed
        if experiment.question_id == "D11":
            assert "long_context_needle_position_fixed_for_instruction_position" in fixed


def test_d8_preserves_project_rule_by_fixing_output_protocol() -> None:
    config = validate_experiments_config(CONFIG_PATH)
    d8 = next(experiment for experiment in config.experiments if experiment.question_id == "D8")

    assert d8.manipulated_variable.axis == "state_serialization"
    assert "multi_agent_output_protocol_fixed" in d8.fixed_confounders
    assert "q-in+out" not in d8.manipulated_variable.axis


def test_local_qwen_is_included_in_all_model_experiments() -> None:
    config = validate_experiments_config(CONFIG_PATH)
    all_model_ids = {"D1", "D2", "D4", "D5", "D6", "D7tab", "D8", "D9", "D10", "D11"}

    for experiment in config.experiments:
        if experiment.question_id in all_model_ids:
            assert "qwen2.5:7b-instruct-q4_K_M" in experiment.models


def test_d3_excludes_qwen_because_native_structured_output_is_not_comparable() -> None:
    config = validate_experiments_config(CONFIG_PATH)
    d3 = next(experiment for experiment in config.experiments if experiment.question_id == "D3")

    assert "qwen2.5:7b-instruct-q4_K_M" not in d3.models


def test_effort_is_variable_only_for_d3_and_d4() -> None:
    config = validate_experiments_config(CONFIG_PATH)

    for experiment in config.experiments:
        if experiment.question_id in {"D3", "D4"}:
            assert experiment.manipulated_variable.effort_levels == ("low", "medium", "high")
        else:
            assert experiment.manipulated_variable.effort_levels == ()


def test_validator_rejects_unknown_suite_model_metric_and_low_repetitions(tmp_path: Path) -> None:
    bad_config = {
        "experiments": [
            {
                "question_id": "BAD",
                "suite": "missing_suite",
                "manipulated_variable": {
                    "axis": "q-in",
                    "levels": ["json"],
                },
                "models": ["bad-model"],
                "metrics": ["bad_metric"],
                "repetition": {"seeds_or_repeated_calls": 2, "temperature_policy": "repeat_calls"},
                "fixed_confounders": ["format_separator_casing_spacing_constant"],
                "hypothesis": {
                    "expected": "invalid",
                    "falsification_threshold": "invalid",
                },
            }
        ]
    }
    path = tmp_path / "bad_experiments.yaml"
    path.write_text(yaml.safe_dump(bad_config), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown suite|unknown model|unknown metric|at least 3"):
        validate_experiments_config(path)
