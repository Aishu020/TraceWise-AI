from pathlib import Path
import pandas as pd

ROOT = Path(".")
RESULTS = ROOT / "experiments" / "results"
VERSION = "V2_1pct"

evidence_path = RESULTS / "heldout_98_metric_evidence.csv"
cases_path = RESULTS / "heldout_98_case_results.csv"

evidence = pd.read_csv(evidence_path)
case_results = pd.read_csv(cases_path)

required_evidence = {
    "case", "version", "service", "metric", "change_score"
}
required_cases = {
    "case", "version", "fault", "known_root_cause"
}

if not required_evidence.issubset(evidence.columns):
    raise ValueError(
        f"Metric evidence is missing columns: "
        f"{required_evidence - set(evidence.columns)}"
    )

if not required_cases.issubset(case_results.columns):
    raise ValueError(
        f"Case results are missing columns: "
        f"{required_cases - set(case_results.columns)}"
    )

# Use the same V2 scores and the same case set for every method.
evidence = evidence[evidence["version"] == VERSION].copy()
cases = case_results[case_results["version"] == VERSION].copy()

if evidence.empty or cases.empty:
    raise ValueError(
        f"No data found for version {VERSION}. "
        "Check the version labels in the CSV files."
    )

evidence["change_score"] = pd.to_numeric(
    evidence["change_score"], errors="coerce"
)
evidence = evidence.dropna(
    subset=["case", "service", "metric", "change_score"]
)

cases = cases[["case", "fault", "known_root_cause"]].drop_duplicates()

if cases["case"].duplicated().any():
    raise ValueError("Case labels are inconsistent across result rows.")

if evidence.duplicated(["case", "service", "metric"]).any():
    raise ValueError(
        "Duplicate case/service/metric rows detected in metric evidence."
    )

case_ids = set(cases["case"])
evidence_ids = set(evidence["case"])

if case_ids != evidence_ids:
    raise ValueError(
        f"Case mismatch: {len(case_ids)} labeled cases versus "
        f"{len(evidence_ids)} cases in metric evidence. "
        f"Missing evidence: {sorted(case_ids - evidence_ids)[:5]}; "
        f"missing labels: {sorted(evidence_ids - case_ids)[:5]}"
    )

# Recalculate four service-level aggregation methods from identical
# per-metric V2 scores. Larger scores indicate stronger anomaly evidence.
def aggregate_service(group):
    scores = group["change_score"].sort_values(ascending=False)
    top_two = scores.head(2)

    return pd.Series({
        "top_two_mean": top_two.mean(),
        "all_metric_median": scores.median(),
        "all_metric_mean": scores.mean(),
        "top_two_max": top_two.max(),
        "metric_count": len(scores),
    })

service_scores = (
    evidence.groupby(["case", "service"], sort=False)
    .apply(aggregate_service, include_groups=False)
    .reset_index()
)

methods = {
    "top_two_mean": "Top-two mean",
    "all_metric_median": "All-metric median",
    "all_metric_mean": "All-metric mean",
    "top_two_max": "Top-two maximum",
}

rank_frames = []

for score_column, method_name in methods.items():
    current = service_scores[
        ["case", "service", score_column]
    ].copy()

    current = current.rename(
        columns={score_column: "service_score"}
    )
    current["method"] = method_name

    # Competition ranking: tied scores receive the same rank.
    current["rank"] = current.groupby("case")[
        "service_score"
    ].rank(method="min", ascending=False)

    rank_frames.append(current)

rankings = pd.concat(rank_frames, ignore_index=True)

rankings = rankings.merge(
    cases, on="case", how="left", validate="many_to_one"
)

rankings["is_root_cause"] = (
    rankings["service"] == rankings["known_root_cause"]
)

root_ranks = rankings[rankings["is_root_cause"]].copy()

if root_ranks["case"].nunique() != len(cases):
    missing = set(cases["case"]) - set(root_ranks["case"])
    raise ValueError(
        f"Could not rank the known root cause for cases: "
        f"{sorted(missing)[:10]}"
    )

root_ranks["hit_at_1"] = (root_ranks["rank"] <= 1).astype(int)
root_ranks["hit_at_3"] = (root_ranks["rank"] <= 3).astype(int)
root_ranks["reciprocal_rank"] = 1 / root_ranks["rank"]

summary_rows = []

for method_name in methods.values():
    subset = root_ranks[root_ranks["method"] == method_name]

    summary_rows.append({
        "method": method_name,
        "cases": subset["case"].nunique(),
        "hit_at_1": subset["hit_at_1"].mean(),
        "hit_at_1_pct": 100 * subset["hit_at_1"].mean(),
        "hit_at_3": subset["hit_at_3"].mean(),
        "hit_at_3_pct": 100 * subset["hit_at_3"].mean(),
        "mrr": subset["reciprocal_rank"].mean(),
        "mean_correct_rank": subset["rank"].mean(),
    })

summary = pd.DataFrame(summary_rows)

per_fault = (
    root_ranks.groupby(["method", "fault"], as_index=False)
    .agg(
        cases=("case", "nunique"),
        hit_at_1=("hit_at_1", "mean"),
        hit_at_3=("hit_at_3", "mean"),
        mrr=("reciprocal_rank", "mean"),
        mean_correct_rank=("rank", "mean"),
    )
)

case_metrics = root_ranks[
    [
        "case", "fault", "known_root_cause", "method",
        "rank", "hit_at_1", "hit_at_3", "reciprocal_rank"
    ]
].sort_values(["case", "method"])

# Compare every alternative against the existing top-two-mean method.
baseline = (
    case_metrics[case_metrics["method"] == "Top-two mean"]
    [["case", "rank", "hit_at_1", "hit_at_3", "reciprocal_rank"]]
    .rename(columns={
        "rank": "baseline_rank",
        "hit_at_1": "baseline_hit_at_1",
        "hit_at_3": "baseline_hit_at_3",
        "reciprocal_rank": "baseline_reciprocal_rank",
    })
)

paired = case_metrics.merge(
    baseline, on="case", how="left", validate="many_to_one"
)
paired["rank_change"] = paired["baseline_rank"] - paired["rank"]
paired["rank_improved"] = paired["rank_change"] > 0
paired["rank_unchanged"] = paired["rank_change"] == 0
paired["rank_worsened"] = paired["rank_change"] < 0

paired_summary = (
    paired[paired["method"] != "Top-two mean"]
    .groupby("method", as_index=False)
    .agg(
        cases=("case", "nunique"),
        rank_improved=("rank_improved", "sum"),
        rank_unchanged=("rank_unchanged", "sum"),
        rank_worsened=("rank_worsened", "sum"),
        hit1_wrong_to_correct=(
            "baseline_hit_at_1",
            lambda s: 0
        ),
    )
)

# Calculate paired Hit@1 and Hit@3 transitions explicitly.
transition_rows = []
for method_name in methods.values():
    if method_name == "Top-two mean":
        continue

    subset = paired[paired["method"] == method_name]
    transition_rows.append({
        "method": method_name,
        "hit1_wrong_to_correct": int(
            ((subset["baseline_hit_at_1"] == 0) &
             (subset["hit_at_1"] == 1)).sum()
        ),
        "hit1_correct_to_wrong": int(
            ((subset["baseline_hit_at_1"] == 1) &
             (subset["hit_at_1"] == 0)).sum()
        ),
        "hit3_outside_to_inside": int(
            ((subset["baseline_hit_at_3"] == 0) &
             (subset["hit_at_3"] == 1)).sum()
        ),
        "hit3_inside_to_outside": int(
            ((subset["baseline_hit_at_3"] == 1) &
             (subset["hit_at_3"] == 0)).sum()
        ),
    })

transitions = pd.DataFrame(transition_rows)

# Save separate files so the original evaluation remains untouched.
summary.to_csv(
    RESULTS / "heldout_98_aggregation_ablation_summary.csv",
    index=False
)
per_fault.to_csv(
    RESULTS / "heldout_98_aggregation_ablation_by_fault.csv",
    index=False
)
case_metrics.to_csv(
    RESULTS / "heldout_98_aggregation_ablation_case_results.csv",
    index=False
)
rankings.to_csv(
    RESULTS / "heldout_98_aggregation_ablation_service_rankings.csv",
    index=False
)
paired.to_csv(
    RESULTS / "heldout_98_aggregation_ablation_paired.csv",
    index=False
)
transitions.to_csv(
    RESULTS / "heldout_98_aggregation_ablation_transitions.csv",
    index=False
)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 180)

print("\n=== AGGREGATION ABLATION: HELDOUT 98 ===")
print(f"Cases evaluated: {len(cases)}")
print(f"Metric evidence rows: {len(evidence)}")
print("\n=== OVERALL SUMMARY ===")
print(summary.round(4).to_string(index=False))

print("\n=== RESULTS BY FAULT ===")
print(per_fault.round(4).to_string(index=False))

print("\n=== PAIRED RANK CHANGES VS TOP-TWO MEAN ===")
print(
    paired_summary.drop(columns=["hit1_wrong_to_correct"])
    .to_string(index=False)
)

print("\n=== HIT@1 / HIT@3 TRANSITIONS ===")
print(transitions.to_string(index=False))

print("\nSaved six CSV files in:", RESULTS.resolve())
