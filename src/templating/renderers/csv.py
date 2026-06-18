"""
Render canonical content as CSV.

Input: Canonical content objects.

Processing: Emits deterministic comma-separated rows with standard csv quoting.

Output: CSV text.
"""

from __future__ import annotations

from templating.canonical import CanonicalContent, Document, Format, InstructionBlock, NestedRecord, Renderer, Table
from templating.renderers._helpers import dispatch_content, flatten_mapping, render_csv_rows


class CsvRenderer(Renderer):
    format = Format.CSV

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
        return render_csv_rows(flatten_mapping(content.data))

    def _render_table(self, content: Table) -> str:
        rows = [content.column_names]
        rows.extend(content.rows_as_tuples)
        return render_csv_rows(rows)

    def _render_document(self, content: Document) -> str:
        metadata = content.metadata
        return render_csv_rows(
            [
                ("id", "title", "source", "text"),
                (metadata.id, metadata.title, metadata.source, content.text),
            ]
        )

    def _render_instruction_block(self, content: InstructionBlock) -> str:
        rows = [("kind", "role", "context", "instruction", "example_input", "example_output")]
        role = content.role or ""
        context = content.context or ""
        for instruction in content.instructions:
            rows.append(("instruction", role, context, instruction, "", ""))
        for example in content.examples:
            rows.append(("example", role, context, "", example.input, example.output))
        return render_csv_rows(rows)
