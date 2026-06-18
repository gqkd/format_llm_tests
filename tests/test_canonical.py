from __future__ import annotations

from typing import Any

import math

import pytest
from pydantic import ValidationError

from templating.canonical import (
    CanonicalContent,
    Document,
    Format,
    InstructionBlock,
    NestedRecord,
    Renderer,
    Table,
    TableColumn,
)


def test_nested_record_accepts_arbitrarily_nested_mapping() -> None:
    record = NestedRecord(
        data={
            "service": "api",
            "replicas": 3,
            "resources": {
                "cpu": {"request": "500m", "limit": "1"},
                "memory": {"request": "512Mi", "limit": "1Gi"},
            },
            "ports": [80, 443],
        }
    )

    assert record.data["resources"]["cpu"]["request"] == "500m"


def test_nested_record_rejects_non_mapping_root() -> None:
    with pytest.raises(ValidationError):
        NestedRecord(data=["not", "a", "mapping"])


def test_nested_record_rejects_keys_that_cannot_render_across_formats() -> None:
    with pytest.raises(ValidationError):
        NestedRecord(data={"invalid key": "value"})

    with pytest.raises(ValidationError):
        NestedRecord(data={"valid": {"a.b": "ambiguous path"}})


def test_nested_record_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValidationError):
        NestedRecord(data={"score": math.nan})

    with pytest.raises(ValidationError):
        NestedRecord(data={"score": math.inf})


def test_table_accepts_homogeneous_rows_with_typed_header() -> None:
    table = Table(
        columns=[
            TableColumn(name="order_id", dtype="integer"),
            TableColumn(name="region", dtype="string"),
            TableColumn(name="amount", dtype="number"),
            TableColumn(name="is_priority", dtype="boolean"),
        ],
        rows=[
            {"order_id": 1, "region": "North", "amount": 120.5, "is_priority": True},
            {"order_id": 2, "region": "South", "amount": 80, "is_priority": False},
        ],
    )

    assert table.column_names == ("order_id", "region", "amount", "is_priority")


def test_table_rejects_rows_with_missing_extra_or_wrong_typed_values() -> None:
    with pytest.raises(ValidationError):
        Table(
            columns=[TableColumn(name="order_id", dtype="integer")],
            rows=[{"order_id": 1}, {"order_id": 2, "extra": "x"}],
        )

    with pytest.raises(ValidationError):
        Table(
            columns=[TableColumn(name="order_id", dtype="integer")],
            rows=[{"order_id": "1"}],
        )


def test_table_rejects_column_names_that_cannot_render_across_formats() -> None:
    with pytest.raises(ValidationError):
        TableColumn(name="order id", dtype="integer")

    with pytest.raises(ValidationError):
        TableColumn(name="a.b", dtype="integer")


def test_document_requires_text_and_metadata() -> None:
    document = Document(
        text="The source passage.",
        metadata={"id": "doc-1", "title": "Reference", "source": "kb"},
    )

    assert document.metadata.id == "doc-1"
    assert document.text == "The source passage."


def test_document_rejects_blank_text_or_missing_required_metadata() -> None:
    with pytest.raises(ValidationError):
        Document(text=" ", metadata={"id": "doc-1", "title": "Reference", "source": "kb"})

    with pytest.raises(ValidationError):
        Document(text="The source passage.", metadata={"id": "doc-1", "title": "Reference"})


def test_instruction_block_accepts_role_context_instructions_and_examples() -> None:
    block = InstructionBlock(
        role="You are a careful classifier.",
        context="Use the canonical labels.",
        instructions=["Read the item.", "Return exactly one label."],
        examples=[
            {"input": "A", "output": "alpha"},
            {"input": "B", "output": "beta"},
        ],
    )

    assert block.instructions == ("Read the item.", "Return exactly one label.")


def test_instruction_block_rejects_empty_instruction_list() -> None:
    with pytest.raises(ValidationError):
        InstructionBlock(role="Classifier", instructions=[])


def test_format_enum_contains_supported_formats() -> None:
    assert {member.value for member in Format} == {
        "plain",
        "markdown",
        "xml",
        "json",
        "yaml",
        "csv",
        "toon",
    }


def test_renderer_is_abstract_and_subclasses_render_canonical_content() -> None:
    with pytest.raises(TypeError):
        Renderer()

    class PlainRenderer(Renderer):
        format = Format.PLAIN

        def render(self, canonical_content: CanonicalContent) -> str:
            return type(canonical_content).__name__

    rendered = PlainRenderer().render(Document(text="Body", metadata={"id": "1", "title": "T", "source": "S"}))

    assert rendered == "Document"
