"""
Run prompts against Anthropic Claude models through the SDK.

Input: Prompt text, run parameters, and optional injected Anthropic client.

Processing: Builds Messages API calls, including optional strict tool schema output.

Output: Standardized run result from the shared ModelRunner base class.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from runners.base import ModelRunner, RunParams

ANTHROPIC_THINKING_BUDGET_TOKENS = {
    "low": 1024,
    "medium": 4096,
    "high": 8192,
}


class AnthropicRunner(ModelRunner):
    """Runner for Claude Opus 4.8, Sonnet 4.6, and Haiku 4.5 compatible models."""

    def __init__(self, *, client: Any | None = None, raw_log_dir: str | Path = "results/raw", **kwargs: Any) -> None:
        super().__init__(raw_log_dir=raw_log_dir, **kwargs)
        if client is None:
            load_dotenv()
            client = Anthropic()
        self.client = client

    def _execute(
        self,
        prompt: str,
        params: RunParams,
        params_used: dict[str, Any],
    ) -> tuple[str, int | None, int | None, dict[str, Any]]:
        input_tokens = self._count_input_tokens(prompt, params_used["model"])
        request = self._build_request(prompt, params_used)
        response = self.client.messages.create(**request)
        return (
            _extract_response_text(response),
            input_tokens,
            _extract_usage_value(response, "output_tokens"),
            params_used,
        )

    def _count_input_tokens(self, prompt: str, model: str) -> int | None:
        response = self.client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return getattr(response, "input_tokens", None)

    def _build_request(self, prompt: str, params_used: dict[str, Any]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": params_used["model"],
            "max_tokens": params_used.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}],
        }
        if "temperature" in params_used:
            request["temperature"] = params_used["temperature"]
        if "reasoning_effort" in params_used:
            budget_tokens = ANTHROPIC_THINKING_BUDGET_TOKENS[params_used["reasoning_effort"]]
            request["thinking"] = {"type": "enabled", "budget_tokens": budget_tokens}
            params_used["anthropic_thinking_budget_tokens"] = budget_tokens
        if "native_output" in params_used:
            request.update(_anthropic_tool_config(params_used["native_output"]))
        return request


def _anthropic_tool_config(native_output: dict[str, Any]) -> dict[str, Any]:
    tool = {
        "name": "benchmark_response",
        "description": "Return the benchmark response using the requested schema.",
        "input_schema": native_output["schema"],
        "strict": True,
    }
    return {
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": "benchmark_response"},
    }


def _extract_response_text(response: Any) -> str:
    content = getattr(response, "content", None)
    if content:
        return _extract_content_blocks_text(content)
    if isinstance(response, dict):
        content = response.get("content") or []
        return _extract_content_blocks_text(content)
    return ""


def _extract_content_blocks_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        text = _extract_text_block(block)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_text_block(block: Any) -> str:
    if isinstance(block, dict):
        if block.get("type") == "tool_use":
            return json.dumps(block.get("input", {}), ensure_ascii=False, separators=(",", ":"))
        return str(block.get("text", ""))
    if getattr(block, "type", None) == "tool_use":
        return json.dumps(getattr(block, "input", {}), ensure_ascii=False, separators=(",", ":"))
    return str(getattr(block, "text", ""))


def _extract_usage_value(response: Any, key: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is not None:
        return getattr(usage, key, None)
    if isinstance(response, dict) and isinstance(response.get("usage"), dict):
        return response["usage"].get(key)
    return None
