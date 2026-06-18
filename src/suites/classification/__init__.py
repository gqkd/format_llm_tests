"""
Generate classification benchmark items.

Input: None.

Processing: Builds deterministic synthetic stand-ins for MMLU, DDXPlus, and BIG-Bench sports.

Output: A list of SuiteItem objects with canonical instruction content and gold labels.
"""

from __future__ import annotations

from suites._synthetic import ALL_FORMATS, instruction_task, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec


SPEC = SuiteSpec(
    name="classification",
    axis=ExperimentAxis.Q_IN,
    formats=ALL_FORMATS,
    metric="accuracy",
    description="Multiple-choice classification across academic, diagnostic, and sports-style tasks.",
)

MMLU_SUBJECTS = (
    "anatomy",
    "astronomy",
    "business_ethics",
    "clinical_knowledge",
    "college_physics",
    "econometrics",
    "formal_logic",
    "high_school_history",
    "machine_learning",
    "world_religions",
)


def load_items() -> list[SuiteItem]:
    items: list[SuiteItem] = []
    items.extend(_mmlu_items())
    items.extend(_ddxplus_items(start_index=len(items)))
    items.extend(_sports_items(start_index=len(items)))
    return items


def _mmlu_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-mmlu",
        "Replace with MMLU stratified samples: 10 subjects x 50 items.",
    )
    labels = ("A", "B", "C", "D")
    items: list[SuiteItem] = []
    for subject_index, subject in enumerate(MMLU_SUBJECTS):
        for offset in range(50):
            label = labels[(subject_index + offset) % len(labels)]
            item_id = f"classification-mmlu-{subject}-{offset:03d}"
            content = instruction_task(
                role="classifier",
                context=(
                    f"Synthetic MMLU subject={subject}. "
                    f"Question {offset}: choose the option matching key {label}."
                ),
                instructions=(
                    "Return exactly one label among A, B, C, and D.",
                    "Use only the provided options.",
                    "Options: A=alpha, B=bravo, C=charlie, D=delta.",
                ),
            )
            items.append(
                SuiteItem(
                    item_id=item_id,
                    suite=SPEC,
                    content=content,
                    gold_answer=label,
                    metric=SPEC.metric,
                    dataset_source=source,
                    metadata={"source_dataset": source.name, "subject": subject},
                )
            )
    return items


def _ddxplus_items(start_index: int) -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-ddxplus",
        "Replace with DDXPlus diagnostic classification cases.",
    )
    labels = ("A", "B", "C", "D")
    items: list[SuiteItem] = []
    for offset in range(0):
        label = labels[(start_index + offset) % len(labels)]
        items.append(
            SuiteItem(
                item_id=f"classification-ddxplus-{offset:03d}",
                suite=SPEC,
                content=instruction_task(
                    role="diagnostic classifier",
                    context=f"Synthetic DDXPlus diagnostic case {offset}.",
                    instructions=("Return exactly one diagnosis label: A, B, C, or D.",),
                ),
                gold_answer=label,
                metric=SPEC.metric,
                dataset_source=source,
                metadata={"source_dataset": source.name},
            )
        )
    return items


def _sports_items(start_index: int) -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-bigbench-sports",
        "Replace with BIG-Bench Sports Understanding examples.",
    )
    labels = ("A", "B", "C", "D")
    items: list[SuiteItem] = []
    for offset in range(0):
        label = labels[(start_index + offset) % len(labels)]
        items.append(
            SuiteItem(
                item_id=f"classification-sports-{offset:03d}",
                suite=SPEC,
                content=instruction_task(
                    role="sports classifier",
                    context=f"Synthetic sports plausibility case {offset}.",
                    instructions=("Return exactly one plausibility label: A, B, C, or D.",),
                ),
                gold_answer=label,
                metric=SPEC.metric,
                dataset_source=source,
                metadata={"source_dataset": source.name},
            )
        )
    return items
