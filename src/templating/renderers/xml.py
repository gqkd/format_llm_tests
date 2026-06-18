"""
Render canonical content as XML.

Input: Canonical content objects.

Processing: Emits deterministic XML tags and escaped text values.

Output: XML text.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from templating.canonical import CanonicalContent, Document, Format, InstructionBlock, NestedRecord, Renderer, Table
from templating.renderers._helpers import dispatch_content, render_xml_element, scalar_to_text


class XmlRenderer(Renderer):
    format = Format.XML

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
        return render_xml_element("record", content.data)

    def _render_table(self, content: Table) -> str:
        rows = []
        for row in content.rows:
            cells = "".join(
                render_xml_element(column.name, row[column.name])
                for column in content.columns
            )
            rows.append(f"<row>{cells}</row>")
        return f"<table>{''.join(rows)}</table>"

    def _render_document(self, content: Document) -> str:
        metadata = content.metadata
        return (
            "<document>"
            f"<id>{escape(metadata.id)}</id>"
            f"<title>{escape(metadata.title)}</title>"
            f"<source>{escape(metadata.source)}</source>"
            f"<text>{escape(content.text)}</text>"
            "</document>"
        )

    def _render_instruction_block(self, content: InstructionBlock) -> str:
        parts: list[str] = ["<instructions_block>"]
        self._append_optional_text(parts, "role", content.role)
        self._append_optional_text(parts, "context", content.context)
        parts.append(self._render_instructions(content))
        parts.append(self._render_examples(content))
        parts.append("</instructions_block>")
        return "".join(parts)

    def _append_optional_text(self, parts: list[str], tag: str, value: str | None) -> None:
        if value is not None:
            parts.append(f"<{tag}>{escape(value)}</{tag}>")

    def _render_instructions(self, content: InstructionBlock) -> str:
        instructions = "".join(
            f"<instruction>{escape(instruction)}</instruction>"
            for instruction in content.instructions
        )
        return f"<instructions>{instructions}</instructions>"

    def _render_examples(self, content: InstructionBlock) -> str:
        examples = "".join(
            "<example>"
            f"<input>{escape(scalar_to_text(example.input))}</input>"
            f"<output>{escape(scalar_to_text(example.output))}</output>"
            "</example>"
            for example in content.examples
        )
        return f"<examples>{examples}</examples>"
