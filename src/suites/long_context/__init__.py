"""
Generate long-context benchmark items.

Input: None.

Processing: Builds compact synthetic documents tagged with target context lengths and citation gold.

Output: A list of SuiteItem objects for wrapping and instruction-position experiments.
"""

from __future__ import annotations

from suites._synthetic import ALL_FORMATS, document, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec


SPEC = SuiteSpec(
    name="long_context",
    axis=ExperimentAxis.Q_IN,
    formats=ALL_FORMATS,
    metric="accuracy_citation_fidelity",
    description="Long-context/RAG tasks for wrapping and instruction-position studies.",
)

CONTEXT_LENGTHS = (8000, 32000, 128000, 1000000)


def load_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-long-context",
        "Replace with real 8K/32K/128K/1M-token documents where supported.",
    )
    items: list[SuiteItem] = []
    for context_length in CONTEXT_LENGTHS:
        for index in range(200):
            item_id = f"long-context-{context_length}-{index:03d}"
            fact_id = f"FACT-{context_length}-{index:03d}"
            answer = f"answer_{index % 37}"
            citation = f"{fact_id}:p{index % 19 + 1}"
            text = (
                f"Synthetic compact placeholder for target context length {context_length}. "
                f"Needle {fact_id} states that the final answer is {answer}. "
                f"Citation marker: {citation}."
            )
            items.append(
                SuiteItem(
                    item_id=item_id,
                    suite=SPEC,
                    content=document(item_id, f"Long context synthetic {index}", source.name, text),
                    gold_answer={"answer": answer, "citation": citation},
                    metric=SPEC.metric,
                    dataset_source=source,
                    metadata={
                        "source_dataset": source.name,
                        "context_length": context_length,
                        "supports_instruction_position": True,
                        "supports_wrapping": True,
                        "materialized_text": "compact-placeholder",
                    },
                )
            )
    return items
