"""
Render canonical content in plain text.

Input: Canonical content objects.

Processing: Emits stable key-value, row, document, or instruction text.

Output: Plain text.
"""

from __future__ import annotations

from templating.canonical import CanonicalContent, Document, Format, InstructionBlock, NestedRecord, Renderer, Table
from templating.renderers._helpers import dispatch_content, flatten_mapping, render_instruction_lines, scalar_to_text


class PlainRenderer(Renderer):
    format = Format.PLAIN

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
        return "\n".join(
            f"{path}: {scalar_to_text(value)}"
            for path, value in flatten_mapping(content.data)
        )

    def _render_table(self, content: Table) -> str:
        lines = ["columns: " + " | ".join(content.column_names)]
        lines.extend(
            " | ".join(scalar_to_text(value) for value in row)
            for row in content.rows_as_tuples
        )
        return "\n".join(lines)

    def _render_document(self, content: Document) -> str:
        metadata = content.metadata
        return "\n".join(
            [
                f"id: {metadata.id}",
                f"title: {metadata.title}",
                f"source: {metadata.source}",
                f"text: {content.text}",
            ]
        )

    def _render_instruction_block(self, content: InstructionBlock) -> str:
        return "\n".join(render_instruction_lines(content))
