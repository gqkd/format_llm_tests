# Project Memory

This repository contains the scaffold for a scientific benchmark that measures how prompt format affects LLM performance across XML, Markdown, JSON, YAML, plain text, CSV, and TOON. The protocol targets current production API models plus one local Ollama fallback model used as a comparable open-weight reference where the experiment semantics allow it.

## Models Under Test

- OpenAI GPT-5.5: `gpt-5.5`
- OpenAI GPT-5.4: `gpt-5.4`
- Anthropic Claude Opus 4.8: `claude-opus-4-8`
- Anthropic Claude Sonnet 4.6: `claude-sonnet-4-6`
- Anthropic Claude Haiku 4.5: `claude-haiku-4-5`

Verify vendor API slugs against current API documentation before implementing runners.

## Local/Ollama Models

- Qwen 2.5 7B Instruct local quantized: `qwen2.5:7b-instruct-q4_K_M` via Ollama generation.

Qwen is included as a peer model in all experiments where the comparison is meaningful, except D3 because native structured output is not comparable to vendor strict structured-output APIs. For D3/D4 only, reasoning effort is an explicit variable with `low`, `medium`, and `high`; every other experiment uses and records `medium` effort.

## Repository Layout

- `src/templating/`: render the same task content in different prompt formats.
- `src/runners/`: model/vendor API runners.
- `src/scoring/`: metrics and validation.
- `src/suites/`: definitions for the 8 benchmark suites: classification, reasoning, extraction, find-replace, nested data, tabular, long context, and multi-agent.
- `src/stats/`: statistical analysis.
- `data/`: versioned task inputs and gold answers.
- `results/`: run outputs; raw outputs stay ignored, aggregate summaries stay trackable.
- `configs/`: PromptFoo configs and run parameters.
- `tests/`: unit tests for suite code, not benchmark task cases.
- `notebooks/`: final analysis notebooks.

## Safety And Method Rules

API keys must never appear in code, commits, or logs. Load them only from environment variables with `python-dotenv`; keep local values in `.env`, never tracked.

Never vary input format (Q-IN) and output format (Q-OUT) in the same comparison. Each benchmark contrast must isolate exactly one of those axes.

Keep content identical across format conditions. Only the deterministic rendering wrapper may change; report results per model, never aggregated across vendors.
