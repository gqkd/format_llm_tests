"""
Validate structured JSON outputs against Pydantic schemas.

Input: Rendered model output and a Pydantic model class.

Processing: Parses JSON and validates the parsed object on the first attempt.

Output: Compliance result with validity and error details.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


class SchemaComplianceResult(BaseModel):
    """JSON schema compliance metric for Q-OUT tasks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_valid: bool
    error_type: str | None
    error_message: str | None
    parsed: dict[str, Any] | None


def validate_json_schema(output: str, schema_model: type[BaseModel]) -> SchemaComplianceResult:
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        return SchemaComplianceResult(
            is_valid=False,
            error_type="json_invalid",
            error_message=str(exc),
            parsed=None,
        )
    try:
        validated = schema_model.model_validate(parsed)
    except ValidationError as exc:
        return SchemaComplianceResult(
            is_valid=False,
            error_type="schema_invalid",
            error_message=str(exc),
            parsed=parsed if isinstance(parsed, dict) else None,
        )
    return SchemaComplianceResult(
        is_valid=True,
        error_type=None,
        error_message=None,
        parsed=validated.model_dump(mode="json"),
    )
