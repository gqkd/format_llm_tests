"""
Calculate per-run model cost from token usage and configured prices.

Input: Standardized run results and a pricing YAML file or mapping.

Processing: Looks up input/output per-million-token prices and multiplies by token counts.

Output: Cost breakdown in USD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from runners.base import RunResult


class ModelPricing(BaseModel):
    """Per-million-token prices for one model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_per_million: float
    output_per_million: float


class PricingTable(BaseModel):
    """Pricing table keyed by model name."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    models: dict[str, ModelPricing]


class CostResult(BaseModel):
    """Input, output, and total cost in USD."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    input_usd: float
    output_usd: float
    total_usd: float


def load_pricing(path: str | Path = "configs/pricing.yaml") -> PricingTable:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return PricingTable.model_validate(data)


def calculate_cost_usd(result: RunResult, pricing: PricingTable | dict[str, Any]) -> CostResult:
    table = pricing if isinstance(pricing, PricingTable) else PricingTable.model_validate(pricing)
    model_pricing = table.models[result.model]
    input_tokens = result.input_tokens or 0
    output_tokens = result.output_tokens or 0
    input_usd = input_tokens / 1_000_000 * model_pricing.input_per_million
    output_usd = output_tokens / 1_000_000 * model_pricing.output_per_million
    return CostResult(
        model=result.model,
        input_usd=input_usd,
        output_usd=output_usd,
        total_usd=input_usd + output_usd,
    )
