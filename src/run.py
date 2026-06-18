"""
Expose the experiment orchestrator CLI.

Input: CLI flags selecting experiment id, dry-run mode, limits, and result paths.

Processing: Delegates planning/execution to ExperimentOrchestrator and prints a concise summary.

Output: Process exit code and result files under results/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orchestrator import ExperimentOrchestrator, OrchestratorPaths  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    orchestrator = ExperimentOrchestrator(
        paths=OrchestratorPaths(
            results_dir=Path(args.results_dir),
            experiments_config=Path(args.experiments_config),
            pricing_config=Path(args.pricing_config),
        )
    )
    summary = orchestrator.run_experiment(
        args.experiment,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    _print_summary(summary)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run configured prompt-format benchmark experiments.")
    parser.add_argument("--experiment", required=True, help="Experiment id such as D5, or all.")
    parser.add_argument("--dry-run", action="store_true", help="Plan prompts and estimate calls/cost without API calls.")
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N items per cell.")
    parser.add_argument("--results-dir", default="results", help="Directory for raw and aggregated outputs.")
    parser.add_argument("--experiments-config", default="configs/experiments.yaml", help="Experiment YAML path.")
    parser.add_argument("--pricing-config", default="configs/pricing.yaml", help="Pricing YAML path.")
    return parser


def _print_summary(summary) -> None:
    print(f"Experiment(s): {', '.join(summary.experiment_ids)}")
    print(f"Planned calls: {summary.planned_calls}")
    print(f"Skipped existing: {summary.skipped_existing}")
    print(f"API calls made: {summary.api_calls_made}")
    print(f"Estimated cost USD: {summary.estimated_cost_usd:.6f}")
    for path in summary.aggregated_paths:
        print(f"Aggregated: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
