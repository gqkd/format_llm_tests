"""
Generate tabular benchmark items.

Input: None.

Processing: Builds canonical tables at requested row counts with lookup, aggregation, and filter questions.

Output: A list of SuiteItem objects scored by accuracy and token cost.
"""

from __future__ import annotations

from suites._synthetic import ALL_FORMATS, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec
from templating.canonical import Table, TableColumn


SPEC = SuiteSpec(
    name="tabular",
    axis=ExperimentAxis.Q_IN,
    formats=ALL_FORMATS,
    metric="accuracy_token",
    description="Canonical tables with lookup, aggregation, and filtered count questions.",
)

ROW_COUNTS = (50, 500, 2000, 5000)
QUESTION_TYPES = ("lookup", "aggregation", "filter_count")


def load_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-tabular",
        "Replace with finalized tabular benchmark tables and calibrated questions.",
    )
    items: list[SuiteItem] = []
    for row_count in ROW_COUNTS:
        table = _table(row_count)
        for question_type in QUESTION_TYPES:
            gold = _answer(row_count, question_type)
            item_id = f"tabular-{row_count}-{question_type}"
            items.append(
                SuiteItem(
                    item_id=item_id,
                    suite=SPEC,
                    content=table,
                    gold_answer=str(gold),
                    metric=SPEC.metric,
                    dataset_source=source,
                    metadata={
                        "source_dataset": source.name,
                        "row_count": row_count,
                        "question_type": question_type,
                        "question": _question(row_count, question_type),
                    },
                )
            )
    return items


def _table(row_count: int) -> Table:
    columns = (
        TableColumn(name="id", dtype="integer"),
        TableColumn(name="region", dtype="string"),
        TableColumn(name="category", dtype="string"),
        TableColumn(name="value", dtype="integer"),
    )
    rows = tuple(
        {
            "id": row_index,
            "region": ("north", "south", "east", "west")[row_index % 4],
            "category": ("alpha", "beta", "gamma")[row_index % 3],
            "value": row_index % 100,
        }
        for row_index in range(row_count)
    )
    return Table(columns=columns, rows=rows)


def _question(row_count: int, question_type: str) -> str:
    if question_type == "lookup":
        return f"What is value for id {row_count // 2}?"
    if question_type == "aggregation":
        return "What is the sum of the value column?"
    return "How many rows have region north and category alpha?"


def _answer(row_count: int, question_type: str) -> int:
    if question_type == "lookup":
        return (row_count // 2) % 100
    if question_type == "aggregation":
        return sum(row_index % 100 for row_index in range(row_count))
    return sum(
        row_index % 4 == 0 and row_index % 3 == 0
        for row_index in range(row_count)
    )
