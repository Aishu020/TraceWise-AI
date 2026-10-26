from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path("experiments/results")
SOURCE = OUT / "temporal_metric_family_loss_details.csv"

df = pd.read_csv(SOURCE)
families = ["cpu", "latency_p50", "latency_p90"]

methods = {
    "cpu": ["cpu"],
    "latency_p50": ["latency_p50"],
    "latency_p90": ["latency_p90"],
    "cpu_plus_p50": ["cpu", "latency_p50"],
    "cpu_plus_p90": ["cpu", "latency_p90"],
    "p50_plus_p90": ["latency_p50", "latency_p90"],
    "cpu_plus_p50_plus_p90": ["cpu", "latency_p50", "latency_p90"],
}

df = df.drop_duplicates(
    ["case", "known_root_cause", "metric_family", "service"]
).copy()

case_roots = (
    df[["case", "known_root_cause"]]
    .drop_duplicates()
    .set_index("case")["known_root_cause"]
    .astype(str)
    .to_dict()
)

lookup = {}
available = {}

for (case, family), group in df.groupby(["case", "metric_family"]):
    available[(case, family)] = set(group["service"].astype(str))
    for _, row in group.iterrows():
        value = row["onset_delay_seconds"]
        lookup[(case, family, str(row["service"]))] = (
            float(value) if pd.notna(value) else np.nan
        )

case_rows = []
service_rows = []

for case, root in sorted(case_roots.items()):
    sets = [available.get((case, f), set()) for f in families]
    common_services = sorted(set.intersection(*sets)) if sets else []

    if root not in common_services:
        print(f"SKIP {case}: root cause not in common service set")
        continue

    n = len(common_services)
    family_scores = {}

    # Rank every family on exactly the same services.
    for family in families:
        delays = pd.Series({
            service: lookup.get((case, family, service), np.nan)
            for service in common_services
        })

        # Missing detections sort last. Equal onset times share minimum rank.
        sortable = delays.fillna(np.inf)
        ranks = sortable.rank(method="min", ascending=True)
        family_scores[family] = ranks / (n + 1)

    for method, selected_families in methods.items():
        rows = []

        for service in common_services:
            component_scores = [
                float(family_scores[f].loc[service])
                for f in selected_families
            ]
            score = float(np.mean(component_scores))

            detected_count = sum(
                pd.notna(lookup.get((case, f, service), np.nan))
                for f in selected_families
            )

            rows.append({
                "case": case,
                "known_root_cause": root,
                "method": method,
                "service": service,
                "fusion_score": score,
                "detected_signal_count": detected_count,
                "services_compared": n,
            })

        result = pd.DataFrame(rows)
        result["root_rank"] = result["fusion_score"].rank(
            method="min", ascending=True
        )

        root_rank = float(
            result.loc[result["service"] == root, "root_rank"].iloc[0]
        )

        best_score = result["fusion_score"].min()
        top_tie_size = int(np.isclose(
            result["fusion_score"].to_numpy(),
            best_score,
            rtol=1e-9,
            atol=1e-12,
        ).sum())

        case_rows.append({
            "case": case,
            "known_root_cause": root,
            "method": method,
            "services_compared": n,
            "root_rank": root_rank,
            "hit_at_1": int(root_rank == 1),
            "hit_at_3": int(root_rank <= 3),
            "reciprocal_rank": 1 / root_rank,
            "top_tie_size": top_tie_size,
        })

        service_rows.extend(result.to_dict("records"))

case_df = pd.DataFrame(case_rows)
service_df = pd.DataFrame(service_rows)

summary = (
    case_df.groupby("method")
    .agg(
        cases=("case", "nunique"),
        hit_at_1=("hit_at_1", "mean"),
        hit_at_3=("hit_at_3", "mean"),
        mrr=("reciprocal_rank", "mean"),
        mean_root_rank=("root_rank", "mean"),
        mean_services=("services_compared", "mean"),
        cases_with_top_ties=("top_tie_size", lambda s: int((s > 1).sum())),
    )
    .reset_index()
)

summary["hit_at_1"] = (summary["hit_at_1"] * 100).round(2)
summary["hit_at_3"] = (summary["hit_at_3"] * 100).round(2)
summary["mrr"] = summary["mrr"].round(4)
summary["mean_root_rank"] = summary["mean_root_rank"].round(3)

summary_path = OUT / "temporal_rank_fusion_common_services_summary.csv"
case_path = OUT / "temporal_rank_fusion_common_services_cases.csv"
service_path = OUT / "temporal_rank_fusion_common_services_details.csv"

summary.to_csv(summary_path, index=False)
case_df.to_csv(case_path, index=False)
service_df.to_csv(service_path, index=False)

print("\n=== FINAL FAIR COMPARISON: COMMON SERVICE SET ===")
print("All methods use the same services within each case.")
print("Tied minimum ranks count as Hit@1/Hit@3 hits.")
print(summary.sort_values(
    ["hit_at_3", "mrr"], ascending=False
).to_string(index=False))

print("\nSaved summary:", summary_path.resolve())
print("Saved case results:", case_path.resolve())
print("Saved service rankings:", service_path.resolve())
