"""
Generate find-replace code repair benchmark items.

Input: None.

Processing: Builds deterministic buggy Python snippets paired with unit tests.

Output: A list of SuiteItem objects scored by pass@1.
"""

from __future__ import annotations

from suites._synthetic import document, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec
from templating.canonical import Format


SPEC = SuiteSpec(
    name="find_replace",
    axis=ExperimentAxis.Q_OUT,
    formats=(Format.PLAIN, Format.JSON),
    metric="pass_at_1",
    description="Hand-built code repair tasks scored by unit tests.",
)


def load_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-handbuilt-find-replace",
        "Replace with the final 30 manually audited bug/unit-test pairs.",
    )
    items: list[SuiteItem] = []
    for index in range(30):
        op = ("add", "multiply", "is_even")[index % 3]
        code, tests = _bug_and_tests(op)
        item_id = f"find-replace-{index:03d}"
        items.append(
            SuiteItem(
                item_id=item_id,
                suite=SPEC,
                content=document(
                    item_id,
                    f"Bug repair task {index}",
                    source.name,
                    f"Fix this Python code and return the corrected file only.\n\n{code}",
                ),
                gold_answer=None,
                metric=SPEC.metric,
                dataset_source=source,
                unit_tests=tests,
                metadata={"source_dataset": source.name, "bug_family": op},
            )
        )
    return items


def _bug_and_tests(op: str) -> tuple[str, str]:
    if op == "add":
        return (
            "def solve(a, b):\n    return a - b\n",
            "from solution import solve\n\n"
            "def test_solve_adds():\n"
            "    assert solve(2, 3) == 5\n"
            "    assert solve(-1, 4) == 3\n",
        )
    if op == "multiply":
        return (
            "def solve(a, b):\n    return a + b\n",
            "from solution import solve\n\n"
            "def test_solve_multiplies():\n"
            "    assert solve(2, 3) == 6\n"
            "    assert solve(-1, 4) == -4\n",
        )
    return (
        "def solve(n):\n    return n % 2 == 1\n",
        "from solution import solve\n\n"
        "def test_solve_evenness():\n"
        "    assert solve(2) is True\n"
        "    assert solve(3) is False\n",
    )
