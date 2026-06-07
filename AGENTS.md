# Project Memory

This repository contains the scaffold for a scientific benchmark that measures how prompt format affects LLM performance across XML, Markdown, JSON, YAML, plain text, CSV, and TOON.

## Models Under Test

- OpenAI GPT-5 Nano: `gpt-5-nano`
- OpenAI GPT-5.2: `gpt-5.2`
- OpenAI GPT-5.4 Nano: `gpt-5.4-nano`
- Anthropic Claude Haiku 4.5: `claude-haiku-4-5`
- Anthropic Claude Sonnet 4.5: `claude-sonnet-4-5`

## Repository Layout

- `src/templating/`: render the same task content in different prompt formats.
- `src/runners/`: model/vendor API runners.
- `src/scoring/`: metrics and validation.
- `src/suites/`: definitions for the 8 benchmark suites.
- `src/stats/`: statistical analysis.
- `data/`: versioned task inputs and gold answers.
- `results/`: run outputs; raw outputs stay ignored except aggregate summaries.
- `configs/`: PromptFoo configs and run parameters.
- `tests/`: unit tests for suite code, not benchmark task cases.
- `notebooks/`: final analysis notebooks.

## Safety And Method Rules

API keys must never appear in code, commits, or logs. Load them only from environment variables with `python-dotenv`; keep local values in `.env`, never tracked.

Never vary input format (Q-IN) and output format (Q-OUT) in the same comparison. Each benchmark contrast must isolate exactly one of those axes.
