"""
Render canonical content in Markdown.

Input: Canonical content objects.

Processing: Emits fixed heading, table, document, and instruction Markdown conventions.

Output: Markdown text.
"""

from __future__ import annotations

from templating.canonical import CanonicalContent, Document, Format, InstructionBlock, NestedRecord, Renderer, Table
from templating.renderers._helpers import dispatch_content, escape_markdown_table_cell, render_instruction_lines, render_markdown_mapping


class MarkdownRenderer(Renderer):
    format = Format.MARKDOWN

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
        return render_markdown_mapping(content.data)

    def _render_table(self, content: Table) -> str:
        header = "| " + " | ".join(escape_markdown_table_cell(name) for name in content.column_names) + " |"
        separator = "| " + " | ".join("---" for _ in content.columns) + " |"
        rows = [
            "| " + " | ".join(escape_markdown_table_cell(value) for value in row) + " |"
            for row in content.rows_as_tuples
        ]
        return "\n".join([header, separator, *rows])

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
