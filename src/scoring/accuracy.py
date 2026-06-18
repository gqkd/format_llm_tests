"""
Score deterministic answer and extraction tasks.

Input: Model outputs, gold answers, and field dictionaries.

Processing: Canonicalizes comparable values and computes exact, substring, or field-level F1 scores.

Output: Pydantic score objects with metric details.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict


class BinaryAccuracyScore(BaseModel):
    """Boolean score for exact or substring answer checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_correct: bool
    prediction_normalized: str
    gold_normalized: str


class FieldF1Score(BaseModel):
    """Field-level extraction score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    correct_fields: int
    predicted_fields: int
    gold_fields: int
    precision: float
    recall: float
    f1: float


def normalize_answer(value: Any) -> str:
    """Normalize whitespace, casing, and simple numeric representations."""

    text = " ".join(str(value).strip().lower().split())
    numeric = _normalize_number(text)
    return numeric if numeric is not None else text


def exact_match_score(prediction: Any, gold: Any) -> BinaryAccuracyScore:
    prediction_normalized = normalize_answer(prediction)
    gold_normalized = normalize_answer(gold)
    return BinaryAccuracyScore(
        is_correct=prediction_normalized == gold_normalized,
        prediction_normalized=prediction_normalized,
        gold_normalized=gold_normalized,
    )


def substring_score(prediction: Any, gold: Any) -> BinaryAccuracyScore:
    prediction_normalized = normalize_answer(prediction)
    gold_normalized = normalize_answer(gold)
    search_space = _normalize_embedded_numbers(prediction_normalized)
    return BinaryAccuracyScore(
        is_correct=gold_normalized in search_space,
        prediction_normalized=prediction_normalized,
        gold_normalized=gold_normalized,
    )


def extraction_field_f1(prediction: dict[str, Any], gold: dict[str, Any]) -> FieldF1Score:
    correct = 0
    for key, gold_value in gold.items():
        if key in prediction and normalize_answer(prediction[key]) == normalize_answer(gold_value):
            correct += 1
    predicted_count = len(prediction)
    gold_count = len(gold)
    precision = correct / predicted_count if predicted_count else 0.0
    recall = correct / gold_count if gold_count else 0.0
    f1 = _harmonic_mean(precision, recall)
    return FieldF1Score(
        correct_fields=correct,
        predicted_fields=predicted_count,
        gold_fields=gold_count,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _normalize_number(text: str) -> str | None:
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text):
        return None
    try:
        number = Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


def _normalize_embedded_numbers(text: str) -> str:
    """Normalize numeric tokens that appear inside otherwise free-form text."""

    def replace(match: re.Match[str]) -> str:
        normalized = _normalize_number(match.group(0))
        return normalized if normalized is not None else match.group(0)

    return re.sub(r"(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?(?!\w)", replace, text)


def _harmonic_mean(precision: float, recall: float) -> float:
    if precision == 0.0 and recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
