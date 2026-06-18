from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from typing import Any
from unittest.mock import Mock, patch

import pytest
import yaml

from templating.canonical import Document, Format, InstructionBlock, NestedRecord, Table, TableColumn
from templating.renderers.csv import CsvRenderer
from templating.renderers.json import JsonRenderer
from templating.renderers.markdown import MarkdownRenderer
from templating.renderers.plain import PlainRenderer
from templating.renderers.toon import ToonRenderer
from templating.renderers.xml import XmlRenderer
from templating.renderers.yaml import YamlRenderer
from templating.tokens import count_tokens


RENDERERS = [
    PlainRenderer(),
    MarkdownRenderer(),
    XmlRenderer(),
    JsonRenderer(),
    YamlRenderer(),
    CsvRenderer(),
    ToonRenderer(),
]


@pytest.fixture
def nested_record() -> NestedRecord:
    return NestedRecord(
        data={
            "service": "checkout",
            "replicas": 3,
            "enabled": True,
            "resources": {
                "cpu": {"request": "500m", "limit": "1 core"},
                "memory": {"request": "512Mi", "limit": "1Gi"},
            },
        }
    )


@pytest.fixture
def table() -> Table:
    return Table(
        columns=[
            TableColumn(name="order_id", dtype="integer"),
            TableColumn(name="region", dtype="string"),
            TableColumn(name="amount", dtype="number"),
        ],
        rows=[
            {"order_id": 1001, "region": "North", "amount": 120.5},
            {"order_id": 1002, "region": "South", "amount": 80},
        ],
    )


@pytest.fixture
def document() -> Document:
    return Document(
        text="Revenue increased in Q3.",
        metadata={"id": "doc-7", "title": "Quarterly Note", "source": "finance-kb"},
    )


@pytest.fixture
def instructions() -> InstructionBlock:
    return InstructionBlock(
        role="Classifier",
        context="Use the canonical label set.",
        instructions=["Read the item.", "Return one label."],
        examples=[{"input": "urgent invoice", "output": "billing"}],
    )


@pytest.mark.parametrize("renderer", RENDERERS)
@pytest.mark.parametrize("fixture_name", ["nested_record", "table", "document", "instructions"])
def test_renderer_is_deterministic(renderer: Any, fixture_name: str, request: pytest.FixtureRequest) -> None:
    content = request.getfixturevalue(fixture_name)

    assert renderer.render(content) == renderer.render(content)


def test_renderers_expose_expected_formats() -> None:
    assert [renderer.format for renderer in RENDERERS] == [
        Format.PLAIN,
        Format.MARKDOWN,
        Format.XML,
        Format.JSON,
        Format.YAML,
        Format.CSV,
        Format.TOON,
    ]


@pytest.mark.parametrize("renderer", RENDERERS)
def test_nested_record_information_matches_canonical(renderer: Any, nested_record: NestedRecord) -> None:
    assert extract_nested(renderer, renderer.render(nested_record)) == nested_record.data


@pytest.mark.parametrize("renderer", RENDERERS)
def test_nested_record_with_lists_matches_canonical(renderer: Any) -> None:
    record = NestedRecord(
        data={
            "service": "checkout",
            "ports": [80, 443],
            "targets": [{"name": "api", "weight": 1}, {"name": "worker", "weight": 2}],
        }
    )

    assert extract_nested(renderer, renderer.render(record)) == record.data


@pytest.mark.parametrize("renderer", RENDERERS)
def test_table_information_matches_canonical(renderer: Any, table: Table) -> None:
    assert extract_table(renderer, renderer.render(table)) == table.rows_as_tuples


@pytest.mark.parametrize("renderer", RENDERERS)
def test_document_information_matches_canonical(renderer: Any, document: Document) -> None:
    assert extract_document(renderer, renderer.render(document)) == {
        "id": "doc-7",
        "title": "Quarterly Note",
        "source": "finance-kb",
        "text": "Revenue increased in Q3.",
    }


@pytest.mark.parametrize("renderer", RENDERERS)
def test_instruction_block_information_matches_canonical(renderer: Any, instructions: InstructionBlock) -> None:
    assert extract_instructions(renderer, renderer.render(instructions)) == {
        "role": "Classifier",
        "context": "Use the canonical label set.",
        "instructions": ("Read the item.", "Return one label."),
        "examples": ((("input", "urgent invoice"), ("output", "billing")),),
    }


def test_same_nested_record_has_same_information_across_all_formats(nested_record: NestedRecord) -> None:
    extracted = [extract_nested(renderer, renderer.render(nested_record)) for renderer in RENDERERS]

    assert all(item == nested_record.data for item in extracted)


def test_same_table_has_same_information_across_all_formats(table: Table) -> None:
    extracted = [extract_table(renderer, renderer.render(table)) for renderer in RENDERERS]

    assert all(item == table.rows_as_tuples for item in extracted)


def test_markdown_uses_fixed_nested_heading_convention(nested_record: NestedRecord, table: Table) -> None:
    nested_output = MarkdownRenderer().render(nested_record)
    table_output = MarkdownRenderer().render(table)

    assert "service: checkout" in nested_output
    assert "### resources" in nested_output
    assert "#### cpu" in nested_output
    assert "| order_id | region | amount |" in table_output
    assert "| 1001 | North | 120.5 |" in table_output


def test_json_uses_two_space_indent_and_preserves_canonical_key_order(nested_record: NestedRecord) -> None:
    output = JsonRenderer().render(nested_record)

    assert output.startswith('{\n  "service": "checkout",\n  "replicas": 3,')
    assert json.loads(output) == nested_record.data


def test_yaml_uses_block_style(nested_record: NestedRecord) -> None:
    output = YamlRenderer().render(nested_record)

    assert "{service:" not in output
    assert "resources:\n  cpu:\n    request: 500m" in output


def test_csv_uses_comma_header_and_standard_quoting() -> None:
    table = Table(
        columns=[
            TableColumn(name="id", dtype="integer"),
            TableColumn(name="note", dtype="string"),
        ],
        rows=[{"id": 1, "note": "hello, world"}],
    )

    assert CsvRenderer().render(table) == 'id,note\r\n1,"hello, world"\r\n'


def test_markdown_table_escapes_delimiters_and_newlines() -> None:
    table = Table(
        columns=[
            TableColumn(name="id", dtype="integer"),
            TableColumn(name="note", dtype="string"),
        ],
        rows=[{"id": 1, "note": "left|right\nsecond"}],
    )

    assert MarkdownRenderer().render(table) == (
        "| id | note |\n"
        "| --- | --- |\n"
        "| 1 | left\\|right second |"
    )


def test_toon_declares_columns_once(table: Table) -> None:
    output = ToonRenderer().render(table)

    assert output.splitlines()[0] == "[2]{order_id,region,amount}:"
    assert output.splitlines()[1] == "1001,North,120.5"


def test_openai_token_count_uses_tiktoken() -> None:
    assert count_tokens("hello world", "gpt-5.5") == 2


def test_anthropic_token_count_uses_count_tokens_endpoint() -> None:
    fake_response = Mock(input_tokens=7)
    fake_messages = Mock()
    fake_messages.count_tokens.return_value = fake_response
    fake_client = Mock(messages=fake_messages)

    with patch("templating.tokens.anthropic.Anthropic", return_value=fake_client):
        assert count_tokens("hello world", "claude-opus-4-8") == 7

    fake_messages.count_tokens.assert_called_once()


def extract_nested(renderer: Any, output: str) -> dict[str, Any]:
    if renderer.format is Format.JSON:
        return json.loads(output)
    if renderer.format is Format.YAML:
        return yaml.safe_load(output)
    if renderer.format is Format.XML:
        return _collapse_index_dicts(_xml_element_to_value(ET.fromstring(output)))
    if renderer.format is Format.MARKDOWN:
        return _collapse_index_dicts(_parse_key_value_lines(output))
    if renderer.format is Format.PLAIN:
        return _unflatten({key: _parse_scalar(value) for key, value in _parse_path_value_lines(output)})
    if renderer.format is Format.CSV:
        rows = list(csv.reader(io.StringIO(output)))
        return _unflatten({key: _parse_scalar(value) for key, value in rows})
    if renderer.format is Format.TOON:
        return _unflatten(_parse_toon_object(output))
    raise AssertionError(renderer.format)


def extract_table(renderer: Any, output: str) -> tuple[tuple[Any, ...], ...]:
    if renderer.format is Format.JSON:
        return tuple(tuple(row.values()) for row in json.loads(output)["rows"])
    if renderer.format is Format.YAML:
        return tuple(tuple(row.values()) for row in yaml.safe_load(output)["rows"])
    if renderer.format is Format.XML:
        root = ET.fromstring(output)
        return tuple(
            tuple(_parse_scalar(child.text or "") for child in row)
            for row in root.findall("row")
        )
    if renderer.format is Format.MARKDOWN:
        lines = output.splitlines()
        data_lines = [line for line in lines if line.startswith("| ")][2:]
        return tuple(tuple(_parse_scalar(part.strip()) for part in line.strip("|").split("|")) for line in data_lines)
    if renderer.format is Format.PLAIN:
        rows = [line for line in output.splitlines() if line and not line.startswith("columns:")]
        return tuple(tuple(_parse_scalar(part) for part in line.split(" | ")) for line in rows)
    if renderer.format is Format.CSV:
        reader = csv.reader(io.StringIO(output))
        next(reader)
        return tuple(tuple(_parse_scalar(value) for value in row) for row in reader)
    if renderer.format is Format.TOON:
        lines = output.splitlines()[1:]
        return tuple(tuple(_parse_scalar(value) for value in line.split(",")) for line in lines)
    raise AssertionError(renderer.format)


def extract_document(renderer: Any, output: str) -> dict[str, str]:
    if renderer.format is Format.JSON:
        data = json.loads(output)
        return {**data["metadata"], "text": data["text"]}
    if renderer.format is Format.YAML:
        data = yaml.safe_load(output)
        return {**data["metadata"], "text": data["text"]}
    if renderer.format is Format.XML:
        root = ET.fromstring(output)
        return {
            "id": root.findtext("id") or "",
            "title": root.findtext("title") or "",
            "source": root.findtext("source") or "",
            "text": root.findtext("text") or "",
        }
    if renderer.format is Format.CSV:
        rows = list(csv.DictReader(io.StringIO(output)))
        return rows[0]
    if renderer.format is Format.TOON:
        reader = csv.DictReader(
            io.StringIO("\n".join(output.splitlines()[1:])),
            fieldnames=["id", "title", "source", "text"],
        )
        return next(reader)
    return _parse_key_value_lines(output)


def extract_instructions(renderer: Any, output: str) -> dict[str, Any]:
    if renderer.format is Format.JSON:
        data = json.loads(output)
    elif renderer.format is Format.YAML:
        data = yaml.safe_load(output)
    elif renderer.format is Format.XML:
        root = ET.fromstring(output)
        data = {
            "role": root.findtext("role"),
            "context": root.findtext("context"),
            "instructions": [node.text for node in root.findall("./instructions/instruction")],
            "examples": [
                {"input": node.findtext("input"), "output": node.findtext("output")}
                for node in root.findall("./examples/example")
            ],
        }
    elif renderer.format in {Format.MARKDOWN, Format.PLAIN}:
        data = _parse_instruction_text(output)
    elif renderer.format is Format.CSV:
        rows = list(csv.DictReader(io.StringIO(output)))
        data = {
            "role": rows[0]["role"],
            "context": rows[0]["context"],
            "instructions": [row["instruction"] for row in rows if row["kind"] == "instruction"],
            "examples": [
                {"input": row["example_input"], "output": row["example_output"]}
                for row in rows
                if row["kind"] == "example"
            ],
        }
    elif renderer.format is Format.TOON:
        data = _parse_instruction_toon(output)
    else:
        raise AssertionError(renderer.format)

    return {
        "role": data["role"],
        "context": data["context"],
        "instructions": tuple(data["instructions"]),
        "examples": tuple(tuple(example.items()) for example in data["examples"]),
    }


def _parse_key_value_lines(output: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(2, result)]
    for line in output.splitlines():
        if not line or line.startswith("columns:"):
            continue
        heading = re.match(r"^(#+)\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            key = heading.group(2)
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1]
            parent.setdefault(key, {})
            if isinstance(parent[key], dict):
                stack.append((level, parent[key]))
            continue
        if ": " in line:
            key, value = line.split(": ", 1)
            stack[-1][1][key.strip()] = _parse_scalar(value.strip())
    return result


def _parse_path_value_lines(output: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in output.splitlines():
        key, value = line.split(": ", 1)
        rows.append((key, value))
    return rows


def _unflatten(flat: dict[str, Any]) -> Any:
    result: dict[str, Any] = {}
    for path, value in flat.items():
        _assign_path(result, _parse_path(path), value)
    return _collapse_index_dicts(result)


def _parse_path(path: str) -> list[str | int]:
    parts: list[str | int] = []
    for segment in path.split("."):
        while "[" in segment:
            name, rest = segment.split("[", 1)
            if name:
                parts.append(name)
            index, segment = rest.split("]", 1)
            parts.append(int(index))
        if segment:
            parts.append(segment)
    return parts


def _assign_path(target: dict[str, Any], parts: list[str | int], value: Any) -> None:
    cursor: Any = target
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        if is_last:
            cursor[part] = value
            return
        next_part = parts[index + 1]
        cursor = cursor.setdefault(part, {} if isinstance(next_part, str) else {})


def _collapse_index_dicts(value: Any) -> Any:
    if isinstance(value, dict):
        collapsed = {key: _collapse_index_dicts(item) for key, item in value.items()}
        if collapsed and all(isinstance(key, int) for key in collapsed):
            return [collapsed[index] for index in sorted(collapsed)]
        if collapsed and all(_is_item_key(key) for key in collapsed):
            indexed = {
                int(key.removeprefix("item_")): item
                for key, item in collapsed.items()
            }
            return [indexed[index] for index in sorted(indexed)]
        return collapsed
    if isinstance(value, list):
        return [_collapse_index_dicts(item) for item in value]
    return value


def _is_item_key(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"item_\d+", value) is not None
    return result


def _parse_scalar(value: str) -> Any:
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _xml_element_to_value(element: ET.Element) -> Any:
    if len(element) == 0:
        return _parse_scalar(element.text or "")
    return {child.tag: _xml_element_to_value(child) for child in element}


def _parse_toon_object(output: str) -> dict[str, Any]:
    rows = list(csv.reader(io.StringIO("\n".join(output.splitlines()[1:]))))
    return {key: _parse_scalar(value) for key, value in rows}


def _parse_instruction_text(output: str) -> dict[str, Any]:
    data: dict[str, Any] = {"instructions": [], "examples": []}
    section = None
    current_example: dict[str, Any] | None = None
    for line in output.splitlines():
        if not line:
            continue
        if line in {"role:", "context:", "instructions:", "examples:"}:
            section = line[:-1]
            continue
        if section in {"role", "context"}:
            data[section] = line
        elif section == "instructions" and line.startswith("- "):
            data["instructions"].append(line[2:])
        elif section == "examples":
            if line.startswith("- input: "):
                current_example = {"input": line.removeprefix("- input: ")}
                data["examples"].append(current_example)
            elif line.startswith("  output: ") and current_example is not None:
                current_example["output"] = line.removeprefix("  output: ")
    return data


def _parse_instruction_toon(output: str) -> dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO("\n".join(output.splitlines()[1:])), fieldnames=["kind", "name", "value"]))
    data: dict[str, Any] = {"instructions": [], "examples": []}
    pending_input = None
    for row in rows:
        if row["kind"] in {"role", "context"}:
            data[row["kind"]] = row["value"]
        elif row["kind"] == "instruction":
            data["instructions"].append(row["value"])
        elif row["kind"] == "example_input":
            pending_input = row["value"]
        elif row["kind"] == "example_output":
            data["examples"].append({"input": pending_input, "output": row["value"]})
    return data
