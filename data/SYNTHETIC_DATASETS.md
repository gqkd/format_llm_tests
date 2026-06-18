# Synthetic Dataset Manifest

No external benchmark dataset is currently materialized in this repository.

The suite generators under `src/suites/` therefore emit deterministic synthetic
stand-ins and mark every item with `dataset_source.is_synthetic = true`.

Run this command from the repository root to write a reproducible JSONL manifest:

```powershell
uv run python data/build_synthetic_suites.py
```

Replace the synthetic subsets with real dataset loaders when access is available:

- MMLU, DDXPlus, BIG-Bench Sports for classification.
- GSM8K, ZebraLogic, and MATH-500 for reasoning.
- ExtractBench-style documents for extraction.
- Audited hand-built bug/unit-test pairs for find-replace.
- Calibrated Terraform-style configs for nested data.
- Final tabular benchmark tables for tabular.
- Real long-context/RAG corpora at 8K, 32K, 128K, and 1M where supported.
- GAIA-style tasks and fixed-orchestrator traces for multi-agent.
