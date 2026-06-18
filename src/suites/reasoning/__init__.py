"""
Generate reasoning benchmark items.

Input: None.

Processing: Builds deterministic synthetic GSM8K, ZebraLogic, and MATH-500 style tasks.

Output: A list of SuiteItem objects with final-answer gold labels.
"""

from __future__ import annotations

from suites._synthetic import ALL_FORMATS, instruction_task, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec


SPEC = SuiteSpec(
    name="reasoning",
    axis=ExperimentAxis.Q_IN,
    formats=ALL_FORMATS,
    metric="accuracy_final_answer",
    description="Final-answer reasoning tasks across arithmetic, logic grids, and contest math.",
)


def load_items() -> list[SuiteItem]:
    items: list[SuiteItem] = []
    items.extend(_gsm8k_items())
    items.extend(_zebralogic_items())
    items.extend(_math500_items())
    return items


def _gsm8k_items() -> list[SuiteItem]:
    source = synthetic_source("synthetic-gsm8k", "Replace with GSM8K test items.")
    items: list[SuiteItem] = []
    for index in range(300):
        apples = 3 + index % 17
        boxes = 2 + index % 9
        answer = apples * boxes
        items.append(
            SuiteItem(
                item_id=f"reasoning-gsm8k-{index:03d}",
                suite=SPEC,
                content=instruction_task(
                    role="math solver",
                    context=f"There are {boxes} boxes with {apples} apples in each box.",
                    instructions=("Compute the total number of apples.", "Return only the final integer."),
                ),
                gold_answer=str(answer),
                metric=SPEC.metric,
                dataset_source=source,
                metadata={"source_dataset": source.name},
            )
        )
    return items


def _zebralogic_items() -> list[SuiteItem]:
    source = synthetic_source("synthetic-zebralogic", "Replace with ZebraLogic benchmark items.")
    colors = ("red", "blue", "green")
    names = ("Ada", "Ben", "Cy")
    items: list[SuiteItem] = []
    for index in range(300):
        answer = names[index % len(names)]
        color = colors[index % len(colors)]
        items.append(
            SuiteItem(
                item_id=f"reasoning-zebralogic-{index:03d}",
                suite=SPEC,
                content=instruction_task(
                    role="logic solver",
                    context=(
                        f"Three people Ada, Ben, and Cy own red, blue, and green houses. "
                        f"In this synthetic puzzle, the {color} house owner is {answer}."
                    ),
                    instructions=(f"Who owns the {color} house?", "Return only the person's name."),
                ),
                gold_answer=answer,
                metric=SPEC.metric,
                dataset_source=source,
                metadata={"source_dataset": source.name},
            )
        )
    return items


def _math500_items() -> list[SuiteItem]:
    source = synthetic_source("synthetic-math500", "Replace with MATH-500 problems.")
    items: list[SuiteItem] = []
    for index in range(300):
        base = index % 50 + 1
        answer = base * base - base
        items.append(
            SuiteItem(
                item_id=f"reasoning-math500-{index:03d}",
                suite=SPEC,
                content=instruction_task(
                    role="contest math solver",
                    context=f"Let n={base}. Evaluate n^2 - n.",
                    instructions=("Return only the final integer.",),
                ),
                gold_answer=str(answer),
                metric=SPEC.metric,
                dataset_source=source,
                metadata={"source_dataset": source.name},
            )
        )
    return items
