"""
Create deterministic synthetic suite fixtures.

Input: Suite names, dataset labels, and small structured task parameters.

Processing: Builds canonical instruction blocks and provenance markers.

Output: Reusable helpers for synthetic benchmark subsets.
"""

from __future__ import annotations

from templating.canonical import Document, DocumentMetadata, Format, InstructionBlock

from .base import DatasetSource


ALL_FORMATS: tuple[Format, ...] = tuple(Format)


def synthetic_source(dataset_name: str, replacement: str) -> DatasetSource:
    return DatasetSource(
        name=dataset_name,
        is_synthetic=True,
        replacement_hint=replacement,
    )


def instruction_task(
    role: str,
    context: str,
    instructions: tuple[str, ...],
) -> InstructionBlock:
    return InstructionBlock(
        role=role,
        context=context,
        instructions=instructions,
    )


def document(item_id: str, title: str, source: str, text: str) -> Document:
    return Document(
        text=text,
        metadata=DocumentMetadata(id=item_id, title=title, source=source),
    )
