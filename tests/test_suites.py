"""
Validate benchmark suite contracts.

Input: Suite loaders and canonical task models.

Processing: Checks suite metadata, item counts, gold answers, schemas, unit tests, and provenance.

Output: Pytest assertions for generated suite items.
"""

from __future__ import annotations

import ast
from collections.abc import Callable

import pytest

from scoring.code_exec import score_python_code_pass_at_1
from suites import (
    classification,
    extraction,
    find_replace,
    long_context,
    multi_agent,
    nested_data,
    reasoning,
    tabular,
)
from suites.base import ExperimentAxis, SuiteItem
from templating.canonical import Document, Format, InstructionBlock, NestedRecord, Table


SuiteLoader = Callable[[], list[SuiteItem]]
EXPECTED_EXTRACTION_SCHEMAS = {
    "invoice": extraction.InvoiceExtraction,
    "clinical_note": extraction.ClinicalNoteExtraction,
    "contract": extraction.ContractExtraction,
    "support_ticket": extraction.SupportTicketExtraction,
    "research_abstract": extraction.ResearchAbstractExtraction,
}
CORRECT_FIND_REPLACE_SOLUTIONS = {
    "add": "def solve(a, b):\n    return a + b\n",
    "multiply": "def solve(a, b):\n    return a * b\n",
    "is_even": "def solve(n):\n    return n % 2 == 0\n",
}


@pytest.mark.parametrize(
    ("suite_name", "loader", "expected_axis", "expected_formats"),
    [
        ("classification", classification.load_items, ExperimentAxis.Q_IN, set(Format)),
        ("reasoning", reasoning.load_items, ExperimentAxis.Q_IN, set(Format)),
        ("extraction", extraction.load_items, ExperimentAxis.Q_OUT, {Format.JSON}),
        ("find_replace", find_replace.load_items, ExperimentAxis.Q_OUT, {Format.PLAIN, Format.JSON}),
        ("nested_data", nested_data.load_items, ExperimentAxis.Q_IN, set(Format)),
        ("tabular", tabular.load_items, ExperimentAxis.Q_IN, set(Format)),
        ("long_context", long_context.load_items, ExperimentAxis.Q_IN, set(Format)),
        ("multi_agent", multi_agent.load_items, ExperimentAxis.Q_IN, {Format.JSON, Format.MARKDOWN, Format.YAML}),
    ],
)
def test_each_suite_declares_axis_formats_and_valid_items(
    suite_name: str,
    loader: SuiteLoader,
    expected_axis: ExperimentAxis,
    expected_formats: set[Format],
) -> None:
    spec = loader()[0].suite
    assert spec.name == suite_name
    assert spec.axis == expected_axis
    assert set(spec.formats) == expected_formats

    items = loader()

    assert items
    assert all(item.suite == spec for item in items)
    assert all(item.item_id for item in items)
    assert all(item.dataset_source.is_synthetic for item in items)
    assert all(item.dataset_source.replacement_hint for item in items)


def test_classification_suite_has_stratified_500_items_with_gold_labels() -> None:
    items = classification.load_items()
    subjects = {item.metadata["subject"] for item in items if item.metadata["source_dataset"] == "synthetic-mmlu"}

    assert len(items) == 500
    assert len(subjects) == 10
    assert all(sum(item.metadata.get("subject") == subject for item in items) == 50 for subject in subjects)
    assert all(isinstance(item.content, InstructionBlock) for item in items)
    assert all(item.gold_answer in {"A", "B", "C", "D"} for item in items)
    assert all(item.metric == "accuracy" for item in items)


def test_reasoning_suite_has_300_items_per_source_with_final_answer_gold() -> None:
    items = reasoning.load_items()

    assert len(items) == 900
    assert _count_by(items, "source_dataset") == {
        "synthetic-gsm8k": 300,
        "synthetic-zebralogic": 300,
        "synthetic-math500": 300,
    }
    assert all(isinstance(item.content, InstructionBlock) for item in items)
    assert all(item.gold_answer is not None for item in items)
    assert all(item.metric == "accuracy_final_answer" for item in items)


def test_extraction_suite_has_five_schemas_sixty_docs_each_and_pydantic_gold() -> None:
    items = extraction.load_items()

    assert len(items) == 300
    assert _count_by(items, "schema_name") == {
        "invoice": 60,
        "clinical_note": 60,
        "contract": 60,
        "support_ticket": 60,
        "research_abstract": 60,
    }
    assert all(isinstance(item.content, Document) for item in items)
    assert all(isinstance(item.gold_answer, dict) for item in items)
    assert all(item.output_schema is not None for item in items)
    assert all(item.metric == "field_f1_schema_compliance" for item in items)
    for item in items:
        _assert_extraction_gold_matches_schema(item)


def test_find_replace_suite_has_thirty_code_tasks_with_unit_tests() -> None:
    items = find_replace.load_items()

    assert len(items) == 30
    assert all(isinstance(item.content, Document) for item in items)
    assert all(isinstance(item.unit_tests, str) and "assert" in item.unit_tests for item in items)
    assert all(item.gold_answer is None for item in items)
    assert all(item.metric == "pass_at_1" for item in items)
    for item in items:
        _assert_unit_tests_parse(item)
    _assert_corrected_find_replace_solutions_pass(items)


def test_nested_data_suite_uses_deep_records_with_gold_answers() -> None:
    items = nested_data.load_items()

    assert len(items) == 1000
    assert all(isinstance(item.content, NestedRecord) for item in items)
    assert min(_max_depth(item.content.data) for item in items) >= 6
    assert all(item.gold_answer is not None for item in items)
    assert all(item.metric == "accuracy_token" for item in items)
    for item in items:
        assert isinstance(item.content, NestedRecord)
        path = item.content.data["question"]["path"]
        assert isinstance(path, str)
        assert _resolve_dot_path(item.content.data, path) == item.gold_answer


def test_tabular_suite_uses_canonical_tables_across_requested_sizes_and_question_types() -> None:
    items = tabular.load_items()
    assert len(items) == 12
    assert _tabular_combinations(items) == _expected_tabular_combinations()
    assert {item.metadata["row_count"] for item in items} == {50, 500, 2000, 5000}
    assert {item.metadata["question_type"] for item in items} == {"lookup", "aggregation", "filter_count"}
    assert all(isinstance(item.content, Table) for item in items)
    assert all(item.gold_answer is not None for item in items)
    assert all(item.metric == "accuracy_token" for item in items)


def test_long_context_suite_has_lengths_and_citation_gold() -> None:
    items = long_context.load_items()

    assert len(items) == 800
    assert _count_by(items, "context_length") == {8000: 200, 32000: 200, 128000: 200, 1000000: 200}
    assert all(isinstance(item.content, Document) for item in items)
    assert all(isinstance(item.gold_answer, dict) for item in items)
    assert all("citation" in item.gold_answer for item in items if isinstance(item.gold_answer, dict))
    assert all(item.metric == "accuracy_citation_fidelity" for item in items)
    for item in items:
        _assert_long_context_gold_is_cited(item)


def test_multi_agent_suite_has_fixed_orchestrator_state_variants() -> None:
    items = multi_agent.load_items()

    assert len(items) == 50
    assert all(isinstance(item.content, NestedRecord) for item in items)
    assert all(item.metadata["orchestrator"] == "fixed-simple-v1" for item in items)
    assert all(item.gold_answer is not None for item in items)
    assert all(item.metric == "success_rate_total_input_tokens" for item in items)


def _count_by(items: list[SuiteItem], key: str) -> dict[object, int]:
    counts: dict[object, int] = {}
    for item in items:
        value = item.metadata[key]
        counts[value] = counts.get(value, 0) + 1
    return counts


def _assert_extraction_gold_matches_schema(item: SuiteItem) -> None:
    schema_name = item.metadata["schema_name"]
    expected_schema = EXPECTED_EXTRACTION_SCHEMAS[schema_name]
    assert item.output_schema is expected_schema
    assert isinstance(item.gold_answer, dict)
    assert set(item.gold_answer) == set(expected_schema.model_fields)
    expected_schema.model_validate(item.gold_answer)


def _assert_unit_tests_parse(item: SuiteItem) -> None:
    assert item.unit_tests is not None
    ast.parse(item.unit_tests)


def _assert_corrected_find_replace_solutions_pass(items: list[SuiteItem]) -> None:
    for bug_family, corrected_code in CORRECT_FIND_REPLACE_SOLUTIONS.items():
        representative = next(item for item in items if item.metadata["bug_family"] == bug_family)
        assert representative.unit_tests is not None
        result = score_python_code_pass_at_1(
            code=corrected_code,
            tests=representative.unit_tests,
            timeout_seconds=5,
        )
        assert result.passed is True


def _tabular_combinations(items: list[SuiteItem]) -> set[tuple[object, object]]:
    return {
        (item.metadata["row_count"], item.metadata["question_type"])
        for item in items
    }


def _expected_tabular_combinations() -> set[tuple[int, str]]:
    return {
        (row_count, question_type)
        for row_count in {50, 500, 2000, 5000}
        for question_type in {"lookup", "aggregation", "filter_count"}
    }


def _assert_long_context_gold_is_cited(item: SuiteItem) -> None:
    assert isinstance(item.content, Document)
    assert isinstance(item.gold_answer, dict)
    assert item.gold_answer["answer"] in item.content.text
    assert item.gold_answer["citation"] in item.content.text
    assert item.metadata["materialized_text"] == "compact-placeholder"


def _max_depth(value: object) -> int:
    if isinstance(value, dict) and value:
        return 1 + max(_max_depth(child) for child in value.values())
    if isinstance(value, list) and value:
        return 1 + max(_max_depth(child) for child in value)
    return 0


def _resolve_dot_path(data: dict[str, object], path: str) -> object:
    current: object = data
    for part in path.split("."):
        assert isinstance(current, dict)
        current = current[part]
    return current
