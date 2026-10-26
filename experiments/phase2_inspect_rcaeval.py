"""Inspect the RCAEval case index without downloading full telemetry files.

Run from the project root:
    python experiments/phase2_inspect_rcaeval.py --suite RE1-OB

This downloads/reads only the benchmark's case index. It does not download the
full RE1/RE2/RE3 telemetry archives. The resulting CSV is a local research
manifest, not a model result.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

INDEX_URI = "hf://datasets/phamquiluan/RCAEval/cases.parquet"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        default="RE1-OB",
        help="Dataset subset to inspect, e.g. RE1-OB, RE1-SS, RE1-TT, RE2-OB (default: RE1-OB).",
    )
    parser.add_argument(
        "--output",
        default="data/rcaeval_case_manifest.csv",
        help="CSV path for the filtered case manifest (relative to project root by default).",
    )
    args = parser.parse_args()

    print("Reading the RCAEval case index. Full telemetry is not being downloaded.")
    try:
        cases = pd.read_parquet(INDEX_URI)
    except Exception as exc:  # show useful setup guidance for common network/dependency errors
        print("Could not read the remote Parquet index.")
        print("Check your internet connection and install experiments/requirements-research.txt")
        print(f"Details: {exc}")
        return 1

    print(f"Index rows: {len(cases)}")
    print("Columns:", ", ".join(str(column) for column in cases.columns))

    if "dataset" not in cases.columns:
        print("Expected a 'dataset' column, but it was not present. Inspect the columns above.")
        return 1

    available = sorted(cases["dataset"].dropna().astype(str).unique())
    print("Available dataset subsets:")
    for name in available:
        print(f"  - {name}")

    selected_name = args.suite.strip().upper()
    filtered = cases[cases["dataset"].astype(str).str.upper() == selected_name].copy()
    if filtered.empty:
        print(f"No rows matched '{selected_name}'. Use one of the subset names printed above.")
        return 2

    useful_columns = [
        column
        for column in (
            "dataset", "case", "root_cause_service", "fault", "inject_time",
            "n_metrics", "n_logs", "n_traces",
        )
        if column in filtered.columns
    ]
    manifest = filtered[useful_columns].sort_values(
        by=[column for column in ("dataset", "case") if column in useful_columns]
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output, index=False)

    print(f"\nSubset: {selected_name}")
    print(f"Cases in subset: {len(manifest)}")
    if "root_cause_service" in manifest.columns:
        print("Root-cause service counts:")
        print(manifest["root_cause_service"].value_counts(dropna=False).to_string())
    if "fault" in manifest.columns:
        print("\nFault type counts:")
        print(manifest["fault"].value_counts(dropna=False).to_string())
    print(f"\nSaved case manifest to: {output}")
    print("Next: review the manifest and choose a small, reproducible set of cases before fetching telemetry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
