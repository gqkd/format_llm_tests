"""
Generate nested-data benchmark items.

Input: None.

Processing: Builds Terraform-style nested records with deterministic lookup questions.

Output: A list of SuiteItem objects scored by answer accuracy and token cost.
"""

from __future__ import annotations

from suites._synthetic import ALL_FORMATS, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec
from templating.canonical import NestedRecord


SPEC = SuiteSpec(
    name="nested_data",
    axis=ExperimentAxis.Q_IN,
    formats=ALL_FORMATS,
    metric="accuracy_token",
    description="Deeply nested infrastructure configs with lookup questions.",
)


def load_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-terraform-nested",
        "Replace with calibrated Terraform-style configs and questions at 40-60% baseline accuracy.",
    )
    items: list[SuiteItem] = []
    for index in range(1000):
        region = f"region_{index % 8}"
        service = f"service_{index % 12}"
        env = ("dev", "stage", "prod")[index % 3]
        answer = f"subnet-{index:04d}"
        record = {
            "provider": {
                "cloud": {
                    region: {
                        "accounts": {
                            f"account_{index % 5}": {
                                "environments": {
                                    env: {
                                        "services": {
                                            service: {
                                                "network": {
                                                    "primary_subnet": answer,
                                                    "replicas": index % 4 + 1,
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "question": {
                "path": (
                    f"provider.cloud.{region}.accounts.account_{index % 5}."
                    f"environments.{env}.services.{service}.network.primary_subnet"
                )
            },
        }
        items.append(
            SuiteItem(
                item_id=f"nested-data-{index:04d}",
                suite=SPEC,
                content=NestedRecord(data=record),
                gold_answer=answer,
                metric=SPEC.metric,
                dataset_source=source,
                metadata={
                    "source_dataset": source.name,
                    "target_accuracy_band": "40-60%",
                    "depth": 7,
                },
            )
        )
    return items
