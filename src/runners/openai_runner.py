"""
Run prompts against OpenAI models through the SDK.

Input: Prompt text, run parameters, and optional injected OpenAI client.

Processing: Builds Responses API calls, including optional strict structured output.

Output: Standardized run result from the shared ModelRunner base class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from runners.base import ModelRunner, RunParams


class OpenAIRunner(ModelRunner):
    """Runner for GPT-5.5 and GPT-5.4 compatible OpenAI models."""

    def __init__(self, *, client: Any | None = None, raw_log_dir: str | Path = "results/raw", **kwargs: Any) -> None:
        super().__init__(raw_log_dir=raw_log_dir, **kwargs)
        if client is None:
            load_dotenv()
            client = OpenAI()
        self.client = client

    def _execute(
        self,
        prompt: str,
        params: RunParams,
        params_used: dict[str, Any],
    ) -> tuple[str, int | None, int | None, dict[str, Any]]:
        request = self._build_request(prompt, params_used)
        response = self.client.responses.create(**request)
        return (
            _extract_response_text(response),
            _extract_usage_value(response, "input_tokens"),
            _extract_usage_value(response, "output_tokens"),
            params_used,
        )

    def _build_request(self, prompt: str, params_used: dict[str, Any]) -> dict[str, Any]:
        request = {
            "model": params_used["model"],
            "input": prompt,
        }
        if "temperature" in params_used:
            request["temperature"] = params_used["temperature"]
        if "seed" in params_used:
            request["seed"] = params_used["seed"]
        if "reasoning_effort" in params_used:
            request["reasoning_effort"] = params_used["reasoning_effort"]
        if "native_output" in params_used:
            request["text"] = _openai_text_format(params_used["native_output"])
        return request


def _openai_text_format(native_output: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "benchmark_response",
            "schema": native_output["schema"],
            "strict": True,
        }
    }


def _extract_response_text(response: Any) -> str:
    _raise_for_response_error(response)
    output_text = getattr(response, "output_text", None)
    if output_text is not None:
        return str(output_text)
    if isinstance(response, dict) and "output_text" in response:
        return str(response["output_text"])
    output = _get_response_field(response, "output") or []
    return _extract_output_content_text(output)


def _raise_for_response_error(response: Any) -> None:
    status = _get_response_field(response, "status")
    if status not in {None, "completed"}:
        details = _get_response_field(response, "incomplete_details") or _get_response_field(response, "error")
        raise ValueError(f"OpenAI response not completed: status={status!r} details={details!r}")
    error = _get_response_field(response, "error")
    if error:
        raise ValueError(f"OpenAI response error: {error!r}")
    output = _get_response_field(response, "output") or []
    refusal = _find_refusal(output)
    if refusal is not None:
        raise ValueError(f"OpenAI response refusal: {refusal}")


def _get_response_field(response: Any, key: str) -> Any:
    if isinstance(response, dict):
        return response.get(key)
    return getattr(response, key, None)


def _extract_output_content_text(output: list[Any]) -> str:
    parts: list[str] = []
    for item in output:
        for content in _get_content_items(item):
            if _content_type(content) in {"output_text", "text"}:
                text = _content_text(content)
                if text:
                    parts.append(text)
    return "\n".join(parts)


def _find_refusal(output: list[Any]) -> str | None:
    for item in output:
        for content in _get_content_items(item):
            if _content_type(content) == "refusal":
                return _content_refusal(content)
    return None


def _get_content_items(item: Any) -> list[Any]:
    if isinstance(item, dict):
        return item.get("content") or []
    return getattr(item, "content", None) or []


def _content_type(content: Any) -> str | None:
    if isinstance(content, dict):
        return content.get("type")
    return getattr(content, "type", None)


def _content_text(content: Any) -> str:
    if isinstance(content, dict):
        return str(content.get("text", ""))
    return str(getattr(content, "text", ""))


def _content_refusal(content: Any) -> str:
    if isinstance(content, dict):
        return str(content.get("refusal", ""))
    return str(getattr(content, "refusal", ""))


def _extract_usage_value(response: Any, key: str) -> int | None:
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        return usage.get(key)
    if usage is not None:
        return getattr(usage, key, None)
    if isinstance(response, dict) and isinstance(response.get("usage"), dict):
        return response["usage"].get(key)
    return None
