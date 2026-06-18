"""
Count model-specific tokens for rendered benchmark prompts.

Input: Rendered text and a model name.

Processing: Uses tiktoken for OpenAI models and Anthropic count_tokens for Claude models.

Output: Integer token count.
"""

from __future__ import annotations

import anthropic
import tiktoken
from dotenv import load_dotenv


def count_tokens(rendered_output: str, model_name: str) -> int:
    """Count tokens for rendered text with the vendor-specific tokenizer/API."""

    normalized = model_name.lower()
    if normalized.startswith("gpt-") or normalized.startswith("o"):
        return _count_openai_tokens(rendered_output, model_name)
    if normalized.startswith("claude-"):
        return _count_anthropic_tokens(rendered_output, model_name)
    raise ValueError(f"unsupported model for token counting: {model_name}")


def _count_openai_tokens(rendered_output: str, model_name: str) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(rendered_output))


def _count_anthropic_tokens(rendered_output: str, model_name: str) -> int:
    load_dotenv()
    client = anthropic.Anthropic()
    response = client.messages.count_tokens(
        model=model_name,
        messages=[{"role": "user", "content": rendered_output}],
    )
    return int(response.input_tokens)
