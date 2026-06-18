"""
Generate multi-agent benchmark items.

Input: None.

Processing: Builds GAIA-style synthetic tasks with fixed orchestrator state records.

Output: A list of SuiteItem objects scored by success rate and total input tokens.
"""

from __future__ import annotations

from suites._synthetic import synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec
from templating.canonical import Format, NestedRecord


SPEC = SuiteSpec(
    name="multi_agent",
    axis=ExperimentAxis.Q_IN,
    formats=(Format.JSON, Format.MARKDOWN, Format.YAML),
    metric="success_rate_total_input_tokens",
    description="GAIA-style fixed-orchestrator tasks with state serialized in selected formats.",
)


def load_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-gaia-style",
        "Replace with 50 GAIA-style tasks and fixed-orchestrator traces.",
    )
    items: list[SuiteItem] = []
    for index in range(50):
        answer = f"target_{index % 11}"
        state = {
            "orchestrator": {
                "name": "fixed-simple-v1",
                "policy": "plan_then_call_tools_then_answer",
                "step_budget": 4,
            },
            "task": {
                "id": f"gaia_synthetic_{index:03d}",
                "question": f"Find the target value for synthetic evidence bundle {index}.",
                "tools_available": ["search_memory", "calculator", "extract_note"],
            },
            "state": {
                "observations": [
                    {"tool": "search_memory", "result": f"candidate={answer}"},
                    {"tool": "extract_note", "result": f"verified={answer}"},
                ],
                "scratchpad": {"current_best": answer, "confidence": "high"},
            },
        }
        items.append(
            SuiteItem(
                item_id=f"multi-agent-{index:03d}",
                suite=SPEC,
                content=NestedRecord(data=state),
                gold_answer=answer,
                metric=SPEC.metric,
                dataset_source=source,
                metadata={
                    "source_dataset": source.name,
                    "orchestrator": "fixed-simple-v1",
                    "state_formats": ["json", "markdown", "compact-pseudocode-yaml"],
                },
            )
        )
    return items
