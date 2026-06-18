"""
Render canonical content as TOON.

Input: Canonical content objects.

Processing: Emits deterministic Token-Oriented Object Notation rows.

Output: TOON text.
"""

from __future__ import annotations

from templating.canonical import CanonicalContent, Document, Format, InstructionBlock, NestedRecord, Renderer, Table
from templating.renderers._helpers import csv_line, dispatch_content, flatten_mapping


class ToonRenderer(Renderer):
    format = Format.TOON

    def render(self, canonical_content: CanonicalContent) -> str:
        return dispatch_content(
            canonical_content,
            (
                (NestedRecord, self._render_nested_record),
                (Table, self._render_table),
                (Document, self._render_document),
                (InstructionBlock, self._render_instruction_block),
            ),
        )

    def _render_nested_record(self, content: NestedRecord) -> str:
        rows = flatten_mapping(content.data)
        return _render_toon_rows("[{count}]{key,value}:", rows)

    def _render_table(self, content: Table) -> str:
        columns = ",".join(content.column_names)
        header = f"[{{count}}]{{{columns}}}:"
        return _render_toon_rows(header, content.rows_as_tuples)

    def _render_document(self, content: Document) -> str:
        metadata = content.metadata
        rows = [(metadata.id, metadata.title, metadata.source, content.text)]
        return _render_toon_rows("[{count}]{id,title,source,text}:", rows)

    def _render_instruction_block(self, content: InstructionBlock) -> str:
        rows = _instruction_rows(content)
        return _render_toon_rows("[{count}]{kind,name,value}:", rows)


def _render_toon_rows(header_template: str, rows: list[tuple[object, ...]] | tuple[tuple[object, ...], ...]) -> str:
    lines = [header_template.replace("{count}", str(len(rows)))]
    lines.extend(csv_line(row) for row in rows)
    return "\n".join(lines)


def _instruction_rows(content: InstructionBlock) -> list[tuple[object, object, object]]:
    rows: list[tuple[object, object, object]] = []
    if content.role is not None:
        rows.append(("role", "", content.role))
    if content.context is not None:
        rows.append(("context", "", content.context))
    rows.extend(("instruction", index, instruction) for index, instruction in enumerate(content.instructions))
    for index, example in enumerate(content.examples):
        rows.append(("example_input", index, example.input))
        rows.append(("example_output", index, example.output))
    return rows
