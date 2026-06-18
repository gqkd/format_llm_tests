from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel

from runners.base import RunResult
from scoring.accuracy import (
    exact_match_score,
    extraction_field_f1,
    normalize_answer,
    substring_score,
)
from scoring.code_exec import score_python_code_pass_at_1
from scoring.cost import calculate_cost_usd, load_pricing
from scoring.judge import CalibrationItem, JudgeClient, JudgeRequest, calibrate_judge, score_with_judge
from scoring.schema_compliance import validate_json_schema


def test_normalize_answer_handles_case_space_and_numeric_formats() -> None:
    assert normalize_answer("  Answer\nValue ") == "answer value"
    assert normalize_answer("1,200.00") == "1200"
    assert normalize_answer("001.5000") == "1.5"


def test_exact_and_substring_scores_use_canonicalized_gold_answer() -> None:
    assert exact_match_score("  1,200.0 ", "1200").is_correct is True
    assert exact_match_score("1201", "1200").is_correct is False
    assert substring_score("The final answer is 1,200.00 euros.", "1200").is_correct is True


def test_extraction_field_f1_counts_correct_fields() -> None:
    score = extraction_field_f1(
        prediction={"name": "Ada", "age": "37", "city": "Paris"},
        gold={"name": "ada", "age": 37, "country": "FR"},
    )

    assert score.correct_fields == 2
    assert score.precision == pytest.approx(2 / 3)
    assert score.recall == pytest.approx(2 / 3)
    assert score.f1 == pytest.approx(2 / 3)


def test_code_exec_passes_and_fails_with_timeout_isolation(tmp_path: Path) -> None:
    passing = score_python_code_pass_at_1(
        code='def add(a, b):\n    return a + b\n',
        tests='from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n',
        work_dir=tmp_path / "pass",
        timeout_seconds=5,
    )
    failing = score_python_code_pass_at_1(
        code='def add(a, b):\n    return a - b\n',
        tests='from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n',
        work_dir=tmp_path / "fail",
        timeout_seconds=5,
    )

    assert passing.passed is True
    assert passing.exit_code == 0
    assert failing.passed is False
    assert "AssertionError" in failing.stderr or "assert" in failing.stdout


def test_code_exec_times_out(tmp_path: Path) -> None:
    result = score_python_code_pass_at_1(
        code='while True:\n    pass\n',
        tests="def test_import_solution():\n    import solution\n",
        work_dir=tmp_path / "timeout",
        timeout_seconds=1,
    )

    assert result.passed is False
    assert result.timed_out is True
    assert result.error is not None


def test_schema_compliance_validates_json_with_pydantic_model() -> None:
    class Answer(BaseModel):
        answer: str
        confidence: float

    valid = validate_json_schema('{"answer":"yes","confidence":0.9}', Answer)
    invalid_json = validate_json_schema('{"answer":', Answer)
    invalid_schema = validate_json_schema('{"answer":"yes"}', Answer)

    assert valid.is_valid is True
    assert invalid_json.is_valid is False
    assert invalid_json.error_type == "json_invalid"
    assert invalid_schema.is_valid is False
    assert invalid_schema.error_type == "schema_invalid"


def test_cost_uses_configurable_pricing_for_input_and_output(tmp_path: Path) -> None:
    pricing_path = tmp_path / "pricing.yaml"
    pricing_path.write_text(
        yaml.safe_dump(
            {
                "models": {
                    "gpt-5.5": {
                        "input_per_million": 1.25,
                        "output_per_million": 10.0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    pricing = load_pricing(pricing_path)
    result = RunResult(
        run_id="r1",
        model="gpt-5.5",
        response_text="x",
        input_tokens=1_000_000,
        output_tokens=500_000,
        error=None,
        response_time_seconds=1.0,
        params_used={"model": "gpt-5.5"},
    )

    assert calculate_cost_usd(result, pricing).total_usd == pytest.approx(6.25)


def test_judge_uses_cross_vendor_rule_and_structured_score() -> None:
    client = FakeJudgeClient({"score": 4, "rationale": "Clear", "rubric_version": "v1"})
    request = JudgeRequest(
        item_id="item-1",
        prompt="write a concise summary",
        response="summary",
        executor_vendor="openai",
        judge_vendor="anthropic",
    )

    score = score_with_judge(request, client)

    assert score.score == 4
    assert score.rationale == "Clear"
    assert client.requests[0].judge_vendor == "anthropic"


def test_judge_rejects_same_vendor_and_calibrates_against_human_labels() -> None:
    client = FakeJudgeClient({"score": 1, "rationale": "same", "rubric_version": "v1"})
    with pytest.raises(ValueError, match="different vendor"):
        score_with_judge(
            JudgeRequest(
                item_id="bad",
                prompt="p",
                response="r",
                executor_vendor="openai",
                judge_vendor="openai",
            ),
            client,
        )

    mislabeled_client = FakeJudgeClient(
        {"score": 4, "rationale": "Clear", "rubric_version": "v1"},
        vendor="openai",
    )
    with pytest.raises(ValueError, match="client vendor"):
        score_with_judge(
            JudgeRequest(
                item_id="bad-client",
                prompt="p",
                response="r",
                executor_vendor="openai",
                judge_vendor="anthropic",
            ),
            mislabeled_client,
        )

    calibration = calibrate_judge(
        [
            CalibrationItem(item_id="1", human_score=1, judge_score=1),
            CalibrationItem(item_id="2", human_score=2, judge_score=2),
            CalibrationItem(item_id="3", human_score=3, judge_score=4),
            CalibrationItem(item_id="4", human_score=5, judge_score=5),
        ],
        target_agreement=0.75,
    )

    assert calibration.agreement == pytest.approx(0.75)
    assert calibration.meets_target is True


class FakeJudgeClient(JudgeClient):
    def __init__(self, response: dict[str, Any], vendor: str = "anthropic") -> None:
        self.response = response
        self._vendor = vendor
        self.requests: list[JudgeRequest] = []

    @property
    def vendor(self) -> str:
        return self._vendor

    def score(self, request: JudgeRequest) -> dict[str, Any]:
        self.requests.append(request)
        return self.response
