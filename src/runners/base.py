"""
Define shared model-runner contracts, retry handling, and raw JSONL logging.

Input: Prompt text, run parameters, model client calls, and metadata.

Processing: Executes calls with bounded retry/backoff and normalizes success or error output.

Output: Standardized run result objects and JSON-lines raw events on disk.
"""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


_RESERVED_PARAM_KEYS = frozenset(
    {
        "model",
        "temperature",
        "seed",
        "native_output",
        "dropped_params",
    }
)


class RunParams(BaseModel):
    """Parameters and metadata for one model call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    task_id: str | None = None
    input_format: str | None = None
    output_format: str | None = None
    seed: int | None = None
    temperature: float | None = None
    native_output: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_reserved_or_unserializable_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        reserved_keys = sorted(set(value) & _RESERVED_PARAM_KEYS)
        if reserved_keys:
            raise ValueError(f"metadata contains reserved runner keys: {reserved_keys}")
        try:
            json.dumps(value, ensure_ascii=False)
        except TypeError as exc:
            raise ValueError("metadata must be JSON-serializable") from exc
        return value


class RunResult(BaseModel):
    """Standardized result returned by every model runner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    model: str
    response_text: str
    input_tokens: int | None
    output_tokens: int | None
    error: dict[str, str] | None
    response_time_seconds: float
    params_used: dict[str, Any]


class ModelRunner(ABC):
    """Common interface for vendor-specific model runners."""

    def __init__(
        self,
        *,
        raw_log_dir: str | Path = "results/raw",
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        clock: Callable[[], float] = time.perf_counter,
        sleep_func: Callable[[float], None] = time.sleep,
        transient_errors: tuple[type[BaseException], ...] = (),
    ) -> None:
        self.raw_log_dir = Path(raw_log_dir)
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.clock = clock
        self.sleep_func = sleep_func
        self.transient_errors = transient_errors

    def run(self, prompt: str, params: RunParams) -> RunResult:
        """Execute one prompt and return a standardized result without raising run errors."""

        run_id = uuid.uuid4().hex
        started_at = self.clock()
        params_used = self._initial_params(params)
        try:
            response_text, input_tokens, output_tokens, params_used = self._call_with_retries(
                prompt,
                params,
                params_used,
            )
            result = RunResult(
                run_id=run_id,
                model=params.model,
                response_text=response_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=None,
                response_time_seconds=self.clock() - started_at,
                params_used=params_used,
            )
        except _RunCallError as exc:
            result = RunResult(
                run_id=run_id,
                model=params.model,
                response_text="",
                input_tokens=None,
                output_tokens=None,
                error={"type": type(exc.original).__name__, "message": str(exc.original)},
                response_time_seconds=self.clock() - started_at,
                params_used=exc.params_used,
            )
        except Exception as exc:  # noqa: BLE001 - nonrecoverable run errors are captured.
            result = RunResult(
                run_id=run_id,
                model=params.model,
                response_text="",
                input_tokens=None,
                output_tokens=None,
                error={"type": type(exc).__name__, "message": str(exc)},
                response_time_seconds=self.clock() - started_at,
                params_used=params_used,
            )
        result = self._write_raw_event(run_id, prompt, params, result)
        return result

    def _call_with_retries(
        self,
        prompt: str,
        params: RunParams,
        params_used: dict[str, Any],
    ) -> tuple[str, int | None, int | None, dict[str, Any]]:
        attempt = 0
        while True:
            try:
                return self._execute(prompt, params, params_used)
            except Exception as exc:  # noqa: BLE001 - retry classifier decides.
                new_params = self._drop_unsupported_param(exc, params_used)
                if new_params is not None:
                    params_used = new_params
                    continue
                if not self._is_transient_error(exc) or attempt >= self.max_retries - 1:
                    raise _RunCallError(exc, params_used) from exc
                self.sleep_func(self.backoff_base_seconds * (2**attempt))
                attempt += 1

    def _initial_params(self, params: RunParams) -> dict[str, Any]:
        params_used: dict[str, Any] = {"model": params.model}
        if params.temperature is not None:
            params_used["temperature"] = params.temperature
        if params.seed is not None:
            params_used["seed"] = params.seed
        if params.native_output is not None:
            params_used["native_output"] = params.native_output
        return params_used

    def _is_transient_error(self, exc: Exception) -> bool:
        return isinstance(exc, self.transient_errors) or _message_contains_any(
            str(exc).lower(),
            ("rate limit", "timeout", "temporar", "transient", "server error", "429", "500", "502", "503", "504"),
        )

    def _drop_unsupported_param(self, exc: Exception, params_used: dict[str, Any]) -> dict[str, Any] | None:
        message = str(exc).lower()
        for param_name in ("temperature", "seed"):
            if param_name in params_used and param_name in message and _message_contains_any(message, ("unsupported", "not supported", "unknown", "unrecognized")):
                updated = dict(params_used)
                updated.pop(param_name)
                dropped_params = list(updated.get("dropped_params", []))
                dropped_params.append(param_name)
                updated["dropped_params"] = dropped_params
                return updated
        return None

    def _write_raw_event(self, run_id: str, prompt: str, params: RunParams, result: RunResult) -> RunResult:
        event = {
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "model": params.model,
            "task_id": params.task_id,
            "input_format": params.input_format,
            "output_format": params.output_format,
            "prompt": prompt,
            "metadata": params.metadata,
            "result": result.model_dump(mode="json"),
        }
        log_path = self.raw_log_dir / f"{run_id}.jsonl"
        try:
            self.raw_log_dir.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=False) + "\n")
        except OSError as exc:
            return result.model_copy(
                update={
                    "error": {
                        "type": type(exc).__name__,
                        "message": f"raw logging failed: {exc}",
                    }
                }
            )
        return result

    @abstractmethod
    def _execute(
        self,
        prompt: str,
        params: RunParams,
        params_used: dict[str, Any],
    ) -> tuple[str, int | None, int | None, dict[str, Any]]:
        """Execute one vendor call."""


def _message_contains_any(message: str, needles: tuple[str, ...]) -> bool:
    return any(needle in message for needle in needles)


class _RunCallError(Exception):
    def __init__(self, original: Exception, params_used: dict[str, Any]) -> None:
        super().__init__(str(original))
        self.original = original
        self.params_used = params_used
