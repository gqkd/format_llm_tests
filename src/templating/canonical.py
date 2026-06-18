"""
Define portable canonical content models for benchmark rendering.

Input: Python data passed to Pydantic models.

Processing: Validates content shape, field names, scalar values, and renderer contracts.

Output: Immutable canonical content objects and shared type aliases.
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Format(str, Enum):
    """Supported surface formats for benchmark prompt rendering."""

    PLAIN = "plain"
    MARKDOWN = "markdown"
    XML = "xml"
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"
    TOON = "toon"


JsonValue: TypeAlias = Any
PORTABLE_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class CanonicalModel(BaseModel):
    """Base model shared by canonical benchmark content types."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class NestedRecord(CanonicalModel):
    """A format-independent nested mapping for structured data tasks."""

    data: dict[str, JsonValue] = Field(min_length=1)

    @field_validator("data")
    @classmethod
    def validate_json_like_mapping(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_json_value(value)
        return value


def _validate_json_value(value: Any) -> None:
    if _is_json_scalar(value):
        _validate_finite_number(value)
        return
    if isinstance(value, list):
        _validate_json_list(value)
        return
    if isinstance(value, dict):
        _validate_json_mapping(value)
        return
    raise ValueError(f"unsupported canonical value type: {type(value).__name__}")


def _is_json_scalar(value: Any) -> bool:
    return value is None or type(value) in {str, int, float, bool}


def _validate_finite_number(value: Any) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValueError("numbers must be finite")


def _validate_json_list(value: list[Any]) -> None:
    for item in value:
        _validate_json_value(item)


def _validate_json_mapping(value: dict[Any, Any]) -> None:
    if not all(isinstance(key, str) for key in value):
        raise ValueError("mapping keys must be strings")
    invalid_keys = [key for key in value if not PORTABLE_FIELD_NAME_RE.fullmatch(key)]
    if invalid_keys:
        raise ValueError(
            "mapping keys must be portable field names: "
            + ", ".join(repr(key) for key in invalid_keys)
        )
    for item in value.values():
        _validate_json_value(item)


ColumnDType: TypeAlias = Literal["string", "integer", "number", "boolean"]


class TableColumn(CanonicalModel):
    """Typed table header entry."""

    name: str = Field(min_length=1)
    dtype: ColumnDType

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("column name must not be blank")
        if not PORTABLE_FIELD_NAME_RE.fullmatch(value):
            raise ValueError("column name must be a portable field name")
        return value


class Table(CanonicalModel):
    """A table with a typed header and homogeneous row dictionaries."""

    columns: tuple[TableColumn, ...] = Field(min_length=1)
    rows: tuple[dict[str, Any], ...] = Field(min_length=1)

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    @property
    def rows_as_tuples(self) -> tuple[tuple[Any, ...], ...]:
        return tuple(
            tuple(row[column.name] for column in self.columns)
            for row in self.rows
        )

    @model_validator(mode="after")
    def validate_rows_match_header(self) -> Table:
        names = self.column_names
        if len(set(names)) != len(names):
            raise ValueError("column names must be unique")

        expected = set(names)
        for row_index, row in enumerate(self.rows):
            actual = set(row)
            if actual != expected:
                raise ValueError(
                    f"row {row_index} keys must match table columns exactly"
                )

            for column in self.columns:
                value = row[column.name]
                if not _matches_dtype(value, column.dtype):
                    raise ValueError(
                        f"row {row_index} column {column.name!r} must be {column.dtype}"
                    )
        return self


def _matches_dtype(value: Any, dtype: ColumnDType) -> bool:
    if dtype == "string":
        return isinstance(value, str)
    if dtype == "integer":
        return type(value) is int
    if dtype == "number":
        return type(value) in {int, float}
    if dtype == "boolean":
        return type(value) is bool
    raise AssertionError(f"unsupported table dtype: {dtype}")


class DocumentMetadata(CanonicalModel):
    """Metadata required for long-context and RAG document chunks."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)

    @field_validator("id", "title", "source")
    @classmethod
    def reject_blank_metadata(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metadata fields must not be blank")
        return value


class Document(CanonicalModel):
    """A source document with text and identifying metadata."""

    text: str = Field(min_length=1)
    metadata: DocumentMetadata

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("document text must not be blank")
        return value


class Example(CanonicalModel):
    """Few-shot example represented independently from any markup syntax."""

    input: JsonValue
    output: JsonValue

    @model_validator(mode="after")
    def validate_json_like_values(self) -> Example:
        _validate_json_value(self.input)
        _validate_json_value(self.output)
        return self


class InstructionBlock(CanonicalModel):
    """Instructional prompt content shared by classification and reasoning tasks."""

    role: str | None = None
    context: str | None = None
    instructions: tuple[str, ...] = Field(min_length=1)
    examples: tuple[Example, ...] = ()

    @field_validator("role", "context")
    @classmethod
    def reject_blank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional text fields must not be blank when provided")
        return value

    @field_validator("instructions")
    @classmethod
    def reject_blank_instructions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not instruction.strip() for instruction in value):
            raise ValueError("instructions must not be blank")
        return value


CanonicalContent: TypeAlias = NestedRecord | Table | Document | InstructionBlock


class Renderer(ABC):
    """Abstract contract for rendering canonical content into a surface format."""

    format: Format

    @abstractmethod
    def render(self, canonical_content: CanonicalContent) -> str:
        """Render canonical content without adding, removing, or reordering facts."""
