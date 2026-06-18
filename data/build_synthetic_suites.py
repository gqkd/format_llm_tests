"""
Materialize synthetic suite manifests.

Input: Suite generators under src/suites.

Processing: Loads deterministic synthetic items and writes provenance/gold summaries.

Output: data/synthetic_suite_manifest.jsonl for reproducibility checks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from suites import classification, extraction, find_replace, long_context, multi_agent, nested_data, reasoning, tabular  # noqa: E402


LOADERS = (
    classification.load_items,
    reasoning.load_items,
    extraction.load_items,
    find_replace.load_items,
    nested_data.load_items,
    tabular.load_items,
    long_context.load_items,
    multi_agent.load_items,
)


def main() -> None:
    output_path = ROOT / "data" / "synthetic_suite_manifest.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for loader in LOADERS:
            for item in loader():
                record = {
                    "item_id": item.item_id,
                    "suite": item.suite.name,
                    "axis": item.suite.axis.value,
                    "formats": [fmt.value for fmt in item.suite.formats],
                    "metric": item.metric,
                    "dataset_source": item.dataset_source.name,
                    "is_synthetic": item.dataset_source.is_synthetic,
                    "replacement_hint": item.dataset_source.replacement_hint,
                    "metadata": item.metadata,
                    "has_gold": item.gold_answer is not None,
                    "has_schema": item.output_schema is not None,
                    "has_unit_tests": item.unit_tests is not None,
                }
                handle.write(json.dumps(record, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
