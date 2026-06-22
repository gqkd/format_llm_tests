"""
Run prompts against local Ollama models.

Input: Prompt text plus local Ollama model names.

Processing: Posts JSON to Ollama generation endpoints through an injectable client.

Output: Standardized RunResult objects for generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from runners.base import ModelRunner, RunParams


class OllamaHttpClient:
    """Small JSON client for Ollama's local HTTP API."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout_seconds: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{endpoint}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - local user-configured Ollama endpoint.
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ConnectionError(f"Ollama request failed: {exc}") from exc


class OllamaRunner(ModelRunner):
    """Generation runner for local Ollama chat/instruct models."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        base_url: str = "http://localhost:11434",
        raw_log_dir: str | Path = "results/raw",
        keep_alive: str | None = None,
        raw: bool | None = None,
        timeout_seconds: float = 120.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(raw_log_dir=raw_log_dir, **kwargs)
        self.client = client or OllamaHttpClient(base_url=base_url, timeout_seconds=timeout_seconds)
        self.keep_alive = keep_alive
        self.raw = raw

    def _execute(
        self,
        prompt: str,
        params: RunParams,
        params_used: dict[str, Any],
    ) -> tuple[str, int | None, int | None, dict[str, Any]]:
        response = self.client.post_json("/api/generate", self._build_request(prompt, params_used))
        model_version = str(response.get("model") or params_used["model"])
        params_used = dict(params_used)
        params_used["model_version"] = model_version
        if "reasoning_effort" in params_used:
            params_used["effort_not_enforced"] = True
        return (
            str(response.get("response", "")),
            _optional_int(response.get("prompt_eval_count")),
            _optional_int(response.get("eval_count")),
            params_used,
        )

    def _build_request(self, prompt: str, params_used: dict[str, Any]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": params_used["model"],
            "prompt": prompt,
            "stream": False,
        }
        options = _ollama_options(params_used)
        if options:
            request["options"] = options
        if "native_output" in params_used:
            request["format"] = params_used["native_output"].get("schema") or "json"
        if self.keep_alive is not None:
            request["keep_alive"] = self.keep_alive
        if self.raw is not None:
            request["raw"] = self.raw
        return request


def _ollama_options(params_used: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if "temperature" in params_used:
        options["temperature"] = params_used["temperature"]
    if "seed" in params_used:
        options["seed"] = params_used["seed"]
    return options


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
