from pathlib import Path
import pandas as pd

ROOT = Path("data")
OUT = Path("experiments/results")
OUT.mkdir(parents=True, exist_ok=True)

files = {
    "original_manifest": ROOT / "rcaeval_case_manifest.csv",
    "tuning_25": ROOT / "rcaeval_25_case_evaluation.csv",
    "heldout_98": ROOT / "rcaeval_heldout_98.csv",
}

frames = {}
for name, path in files.items():
    if not path.exists():
        print(f"MISSING: {path}")
        continue

    df = pd.read_csv(path)
    if "case" not in df.columns:
        print(f"ERROR: {path} has no 'case' column")
        continue

    df["case"] = df["case"].astype(str).str.strip()
    frames[name] = df

print("\n=== MANIFEST AUDIT ===")
for name, df in frames.items():
    print(
        f"{name}: rows={len(df)}, "
        f"unique_cases={df['case'].nunique()}, "
        f"duplicate_rows={df['case'].duplicated().sum()}"
    )

print("\n=== OVERLAP AUDIT ===")
names = list(frames)
overlap_rows = []

for i, first in enumerate(names):
    for second in names[i + 1:]:
        a = set(frames[first]["case"])
        b = set(frames[second]["case"])
        overlap = sorted(a & b)

        print(
            f"{first} vs {second}: "
            f"overlap={len(overlap)}, "
            f"only_first={len(a - b)}, "
            f"only_second={len(b - a)}"
        )

        for case in overlap:
            overlap_rows.append({
                "manifest_a": first,
                "manifest_b": second,
                "case": case,
            })

pd.DataFrame(overlap_rows).to_csv(
    OUT / "evaluation_split_overlap_audit.csv", index=False
)

# Summarize existing experiment outputs to determine which cases
# have already influenced results or analysis.
result_files = [
    OUT / "evaluation_25_case_results.csv",
    OUT / "heldout_98_case_results.csv",
    OUT / "heldout_98_aggregation_ablation_case_results.csv",
    OUT / "heldout_98_detailed_error_audit.csv",
    OUT / "temporal_rank_fusion_corrected_cases.csv",
    OUT / "temporal_rank_fusion_common_services_cases.csv",
]

seen_rows = []
for path in result_files:
    if not path.exists():
        print(f"Result file not found (skipped): {path}")
        continue

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        print(f"Could not read {path}: {exc}")
        continue

    if "case" not in df.columns:
        print(f"No case column (skipped): {path}")
        continue

    cases = sorted(set(df["case"].dropna().astype(str).str.strip()))
    print(f"Previously evaluated: {path.name}: {len(cases)} unique cases")

    for case in cases:
        seen_rows.append({
            "source_file": path.name,
            "case": case,
        })

seen_df = pd.DataFrame(seen_rows)
seen_df.to_csv(OUT / "previously_evaluated_cases_audit.csv", index=False)

if "original_manifest" in frames:
    original = set(frames["original_manifest"]["case"])
    seen = set(seen_df["case"]) if not seen_df.empty else set()

    summary = pd.DataFrame([{
        "original_manifest_cases": len(original),
        "cases_seen_in_existing_result_files": len(original & seen),
        "cases_not_found_in_listed_result_files": len(original - seen),
        "cases_in_result_files_not_in_original_manifest": len(seen - original),
    }])
    summary.to_csv(OUT / "evaluation_split_audit_summary.csv", index=False)

    print("\n=== COVERAGE SUMMARY ===")
    print(summary.to_string(index=False))

print("\nAudit files saved under:", OUT.resolve())
print("No source manifests or experiment results were modified.")
