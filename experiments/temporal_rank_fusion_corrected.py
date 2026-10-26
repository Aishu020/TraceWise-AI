from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path("experiments/results")
SOURCE = OUT / "temporal_metric_family_loss_details.csv"

df = pd.read_csv(SOURCE)

FAMILIES = ["cpu", "latency_p50", "latency_p90"]

METHODS = {
    "cpu": ["cpu"],
    "latency_p50": ["latency_p50"],
    "cpu_plus_p50": ["cpu", "latency_p50"],
    "cpu_plus_p90": ["cpu", "latency_p90"],
    "p50_plus_p90": ["latency_p50", "latency_p90"],
    "cpu_plus_p50_plus_p90": ["cpu", "latency_p50", "latency_p90"],
}

# One row per case/service/family.
df = df.drop_duplicates(
    ["case", "known_root_cause", "metric_family", "service"]
).copy()

# Availability means the service has a row for that metric family.
# Detection means a persistent anomaly was actually found.
available = {}
onset = {}

for (case, family), group in df.groupby(["case", "metric_family"]):
    available[(case, family)] = set(group["service"].astype(str))

    for _, row in group.iterrows():
        onset[(case, family, str(row["service"]))] = (
            float(row["onset_delay_seconds"])
            if pd.notna(row["onset_delay_seconds"])
            else np.nan
        )

roots = (
    df[["case", "known_root_cause"]]
    .drop_duplicates()
    .set_index("case")["known_root_cause"]
    .astype(str)
    .to_dict()
)

case_results = []
service_results = []

for method, families in METHODS.items():
    cases = sorted(df["case"].unique())

    for case in cases:
        root = roots[case]

        # Use only services with all required metric families available.
        common_services = None
        for family in families:
            family_services = available.get((case, family), set())
            common_services = (
                family_services.copy()
                if common_services is None
                else common_services.intersection(family_services)
            )

        common_services = sorted(common_services or set())

        if not common_services:
            continue

        if root not in common_services:
            case_results.append({
                "method": method,
                "case": case,
                "known_root_cause": root,
                "services_compared": len(common_services),
                "root_in_comparison_set": False,
                "root_rank": np.nan,
                "hit_at_1": np.nan,
                "hit_at_3": np.nan,
                "reciprocal_rank": np.nan,
                "top_tie_size": np.nan,
            })
            continue

        n_services = len(common_services)
        scores = []

        for service in common_services:
            family_ranks = []
            detected_count = 0

            for family in families:
                delay = onset.get((case, family, service), np.nan)

                if pd.notna(delay):
                    detected_count += 1

                family_ranks.append((family, delay))

            # Rank each family over the same service universe.
            normalized = []

            for family, delay in family_ranks:
                family_delays = {
                    s: onset.get((case, family, s), np.nan)
                    for s in common_services
                }

                detected_services = [
                    s for s, d in family_delays.items()
                    if pd.notna(d)
                ]

                if pd.isna(delay):
                    # No detection gets the worst normalized score.
                    normalized.append(1.0)
                else:
                    earlier_or_equal = sum(
                        family_delays[s] <= delay
                        for s in detected_services
                    )
                    # Minimum rank gives tied onset times the same rank.
                    family_rank = sum(
                        family_delays[s] < delay
                        for s in detected_services
                    ) + 1

                    # Normalize using the common service-set size.
                    normalized.append(family_rank / (n_services + 1))

            scores.append({
                "method": method,
                "case": case,
                "known_root_cause": root,
                "service": service,
                "fusion_score": float(np.mean(normalized)),
                "detected_signal_count": detected_count,
                "signals_used": len(families),
            })

        service_df = pd.DataFrame(scores)

        # Lower fusion score is better. Ties receive the minimum rank.
        service_df["service_rank"] = service_df["fusion_score"].rank(
            method="min", ascending=True
        )

        root_row = service_df[
            service_df["service"] == root
        ].iloc[0]

        root_rank = float(root_row["service_rank"])
        best_score = float(service_df["fusion_score"].min())
        top_tie_size = int(
            np.isclose(
                service_df["fusion_score"].to_numpy(),
                best_score,
                rtol=1e-9,
                atol=1e-12,
            ).sum()
        )

        case_results.append({
            "method": method,
            "case": case,
            "known_root_cause": root,
            "services_compared": n_services,
            "root_in_comparison_set": True,
            "root_rank": root_rank,
            "hit_at_1": int(root_rank == 1),
            "hit_at_3": int(root_rank <= 3),
            "reciprocal_rank": 1.0 / root_rank,
            "top_tie_size": top_tie_size,
        })

        service_results.extend(service_df.to_dict("records"))

case_df = pd.DataFrame(case_results)
service_df = pd.DataFrame(service_results)

valid = case_df[case_df["root_in_comparison_set"] == True].copy()

summary = (
    valid.groupby("method")
    .agg(
        cases=("case", "nunique"),
        hit_at_1=("hit_at_1", "mean"),
        hit_at_3=("hit_at_3", "mean"),
        mrr=("reciprocal_rank", "mean"),
        mean_root_rank=("root_rank", "mean"),
        mean_services=("services_compared", "mean"),
        cases_with_top_ties=("top_tie_size", lambda x: int((x > 1).sum())),
    )
    .reset_index()
)

summary["hit_at_1"] = (summary["hit_at_1"] * 100).round(2)
summary["hit_at_3"] = (summary["hit_at_3"] * 100).round(2)
summary["mrr"] = summary["mrr"].round(4)
summary["mean_root_rank"] = summary["mean_root_rank"].round(3)
summary["mean_services"] = summary["mean_services"].round(2)

case_path = OUT / "temporal_rank_fusion_corrected_cases.csv"
service_path = OUT / "temporal_rank_fusion_corrected_services.csv"
summary_path = OUT / "temporal_rank_fusion_corrected_summary.csv"

case_df.to_csv(case_path, index=False)
service_df.to_csv(service_path, index=False)
summary.to_csv(summary_path, index=False)

print("\n=== CORRECTED TEMPORAL RANK-FUSION RESULTS ===")
print("Comparisons use each method's common service set.")
print("Hit@1/Hit@3 count tied minimum ranks as hits.")
print(summary.sort_values(
    ["hit_at_3", "mrr"], ascending=False
).to_string(index=False))

print("\n=== CASE COVERAGE ===")
print(
    case_df.groupby("method").agg(
        evaluated_cases=("case", "nunique"),
        root_in_set=("root_in_comparison_set", "sum"),
    ).to_string()
)

print("\nSaved summary:", summary_path.resolve())
print("Saved case results:", case_path.resolve())
print("Saved service rankings:", service_path.resolve())
