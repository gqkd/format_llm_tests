"""
Define shared suite item contracts.

Input: Canonical task content, suite metadata, gold answers, and optional schemas/tests.

Processing: Stores immutable benchmark suite descriptors and per-item metadata.

Output: Dataclass objects consumed by prompt construction, scoring, and tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel

from templating.canonical import CanonicalContent, Format


class ExperimentAxis(str, Enum):
    """Single benchmark axis varied in a suite comparison."""

    Q_IN = "q-in"
    Q_OUT = "q-out"


@dataclass(frozen=True)
class DatasetSource:
    """Dataset provenance for a suite item."""

    name: str
    is_synthetic: bool
    replacement_hint: str


@dataclass(frozen=True)
class SuiteSpec:
    """Static suite-level protocol declaration."""

    name: str
    axis: ExperimentAxis
    formats: tuple[Format, ...]
    metric: str
    description: str


@dataclass(frozen=True)
class SuiteItem:
    """One benchmark item with canonical content and scoring metadata."""

    item_id: str
    suite: SuiteSpec
    content: CanonicalContent
    gold_answer: Any
    metric: str
    dataset_source: DatasetSource
    metadata: dict[str, Any] = field(default_factory=dict)
    output_schema: type[BaseModel] | None = None
    unit_tests: str | None = None
