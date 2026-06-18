"""
Provide shared deterministic serialization helpers for renderers.

Input: Canonical content objects and primitive values.

Processing: Converts canonical structures to stable mappings, paths, XML, CSV, and text.

Output: Helper return values consumed by concrete renderers.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable, Iterable, Sequence
from typing import Any
from xml.sax.saxutils import escape

from templating.canonical import (
    CanonicalContent,
    Document,
    Example,
    InstructionBlock,
    NestedRecord,
    Table,
)

RenderHandler = tuple[type[CanonicalContent], Callable[[CanonicalContent], str]]


def dispatch_content(content: CanonicalContent, handlers: Sequence[RenderHandler]) -> str:
    for content_type, handler in handlers:
        if isinstance(content, content_type):
            return handler(content)
    raise TypeError(f"unsupported canonical content: {type(content).__name__}")


def content_to_data(content: CanonicalContent) -> Any:
    if isinstance(content, NestedRecord):
        return content.data
    if isinstance(content, Table):
        return {
            "columns": [column.model_dump(mode="python") for column in content.columns],
            "rows": [_ordered_row(row, content) for row in content.rows],
        }
    if isinstance(content, Document):
        return {
            "metadata": content.metadata.model_dump(mode="python"),
            "text": content.text,
        }
    if isinstance(content, InstructionBlock):
        data: dict[str, Any] = {}
        if content.role is not None:
            data["role"] = content.role
        if content.context is not None:
            data["context"] = content.context
        data["instructions"] = list(content.instructions)
        data["examples"] = [example.model_dump(mode="python") for example in content.examples]
        return data
    raise TypeError(f"unsupported canonical content: {type(content).__name__}")


def _ordered_row(row: dict[str, Any], table: Table) -> dict[str, Any]:
    return {column.name: row[column.name] for column in table.columns}


def scalar_to_text(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return str(value)


def flatten_mapping(data: dict[str, Any]) -> list[tuple[str, Any]]:
    return list(_flatten_value(data))


def _flatten_value(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield from _flatten_value(item, path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten_value(item, f"{prefix}[{index}]")
        return
    yield prefix, value


def csv_line(values: Iterable[Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="")
    writer.writerow([scalar_to_text(value) for value in values])
    return buffer.getvalue()


def render_csv_rows(rows: Iterable[Iterable[Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([scalar_to_text(value) for value in row])
    return buffer.getvalue()


def require_xml_tag(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", name):
        raise ValueError(f"invalid XML tag name: {name!r}")
    return name


def render_xml_element(name: str, value: Any) -> str:
    tag = require_xml_tag(name)
    if isinstance(value, dict):
        children = "".join(render_xml_element(key, item) for key, item in value.items())
        return f"<{tag}>{children}</{tag}>"
    if isinstance(value, list):
        children = "".join(
            render_xml_element(f"item_{index}", item)
            for index, item in enumerate(value)
        )
        return f"<{tag}>{children}</{tag}>"
    return f"<{tag}>{escape(scalar_to_text(value))}</{tag}>"


def render_markdown_mapping(data: dict[str, Any], level: int = 3) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{'#' * level} {key}")
            lines.append(render_markdown_mapping(value, level + 1))
        elif isinstance(value, list):
            lines.append(f"{'#' * level} {key}")
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    lines.append(f"{'#' * (level + 1)} item_{index}")
                    lines.append(render_markdown_mapping(item, level + 2))
                else:
                    lines.append(f"item_{index}: {scalar_to_text(item)}")
        else:
            lines.append(f"{key}: {scalar_to_text(value)}")
    return "\n".join(line for line in lines if line != "")


def render_plain_mapping(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(render_plain_mapping(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    lines.append(f"{prefix}  item_{index}:")
                    lines.append(render_plain_mapping(item, indent + 2))
                else:
                    lines.append(f"{prefix}  item_{index}: {scalar_to_text(item)}")
        else:
            lines.append(f"{prefix}{key}: {scalar_to_text(value)}")
    return "\n".join(lines)


def escape_markdown_table_cell(value: Any) -> str:
    return (
        scalar_to_text(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def render_instruction_lines(content: InstructionBlock) -> list[str]:
    lines: list[str] = []
    if content.role is not None:
        lines.extend(["role:", content.role])
    if content.context is not None:
        lines.extend(["context:", content.context])
    lines.append("instructions:")
    lines.extend(f"- {instruction}" for instruction in content.instructions)
    lines.append("examples:")
    for example in content.examples:
        lines.extend(render_example_lines(example))
    return lines


def render_example_lines(example: Example) -> list[str]:
    return [
        f"- input: {scalar_to_text(example.input)}",
        f"  output: {scalar_to_text(example.output)}",
    ]
