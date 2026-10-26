from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path("experiments/results")
DETAILS = OUT / "temporal_metric_family_loss_details.csv"

df = pd.read_csv(DETAILS)

FAMILIES = ["cpu", "latency_p50", "latency_p90"]
COMBINATIONS = {
    "cpu_plus_p50": ["cpu", "latency_p50"],
    "cpu_plus_p90": ["cpu", "latency_p90"],
    "p50_plus_p90": ["latency_p50", "latency_p90"],
    "cpu_plus_p50_plus_p90": ["cpu", "latency_p50", "latency_p90"],
}

def make_normalized_ranks(group):
    """Lower normalized rank is better; undetected services receive the worst rank."""
    group = group.copy()
    n_services = len(group)
    detected = group["detected"].fillna(False).astype(bool)

    group["normalized_rank"] = 1.0

    if detected.any():
        ranks = group.loc[detected, "onset_delay_seconds"].rank(
            method="min", ascending=True
        )
        group.loc[detected, "normalized_rank"] = (
            ranks / (n_services + 1)
        )

    return group

# Build a common service list per case across all available families.
case_services = (
    df[["case", "known_root_cause", "service"]]
    .drop_duplicates()
)

rank_tables = {}

for family in FAMILIES:
    sub = df[df["metric_family"] == family].copy()
    normalized = []

    for case, group in sub.groupby("case"):
        normalized.append(make_normalized_ranks(group))

    if normalized:
        normalized = pd.concat(normalized, ignore_index=True)
        rank_tables[family] = normalized[
            ["case", "service", "normalized_rank", "detected"]
        ].rename(columns={
            "normalized_rank": f"{family}_rank",
            "detected": f"{family}_detected",
        })

combined = case_services.copy()

for family, table in rank_tables.items():
    combined = combined.merge(
        table, on=["case", "service"], how="left"
    )

# Single-family rankings and multi-family rank fusion.
for family in FAMILIES:
    combined[f"score_{family}"] = combined[f"{family}_rank"]

for method, families in COMBINATIONS.items():
    rank_cols = [f"{f}_rank" for f in families]
    combined[f"score_{method}"] = combined[rank_cols].mean(
        axis=1, skipna=False
    )

methods = (
    [f"score_{f}" for f in FAMILIES]
    + [f"score_{m}" for m in COMBINATIONS]
)

case_results = []

for (case, root), group in combined.groupby(
    ["case", "known_root_cause"]
):
    for method in methods:
        ranked = group.sort_values(
            [method, "service"], ascending=[True, True]
        ).reset_index(drop=True)

        root_positions = ranked.index[
            ranked["service"] == root
        ].tolist()

        if not root_positions:
            continue

        rank = root_positions[0] + 1

        case_results.append({
            "case": case,
            "known_root_cause": root,
            "method": method.replace("score_", ""),
            "root_rank": rank,
            "hit_at_1": int(rank == 1),
            "hit_at_3": int(rank <= 3),
            "reciprocal_rank": 1.0 / rank,
        })

case_results = pd.DataFrame(case_results)

summary = (
    case_results.groupby("method")
    .agg(
        cases=("case", "nunique"),
        hit_at_1=("hit_at_1", "mean"),
        hit_at_3=("hit_at_3", "mean"),
        mrr=("reciprocal_rank", "mean"),
        mean_root_rank=("root_rank", "mean"),
    )
    .reset_index()
)

for col in ["hit_at_1", "hit_at_3", "mrr"]:
    summary[col] = (100 * summary[col]).round(2) if col != "mrr" else summary[col].round(4)

summary["mean_root_rank"] = summary["mean_root_rank"].round(3)

case_path = OUT / "temporal_rank_fusion_loss_case_results.csv"
summary_path = OUT / "temporal_rank_fusion_loss_summary.csv"

case_results.to_csv(case_path, index=False)
summary.to_csv(summary_path, index=False)

print("\n=== TEMPORAL RANK-FUSION COMPARISON ===")
print("Hit@1 and Hit@3 are percentages; MRR is on a 0–1 scale.")
print(summary.sort_values("mrr", ascending=False).to_string(index=False))

print("\nSaved case results:", case_path.resolve())
print("Saved summary:", summary_path.resolve())
