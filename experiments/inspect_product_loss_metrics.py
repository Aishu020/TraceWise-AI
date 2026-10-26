from pathlib import Path
import pandas as pd

results_dir = Path("experiments/results")
evidence_file = results_dir / "heldout_98_metric_evidence.csv"

df = pd.read_csv(evidence_file)

required = {"case", "version", "service", "metric", "change_score"}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {sorted(missing)}")

cases = [
    "re1ob_productcatalogservice_loss_2",
    "re1ob_productcatalogservice_loss_3",
    "re1ob_productcatalogservice_loss_4",
    "re1ob_productcatalogservice_loss_5",
]

# Use the same V2-normalized metric evidence for all aggregation methods.
v2 = df[df["version"] == "V2_1pct"].copy()
v2["change_score"] = pd.to_numeric(v2["change_score"], errors="coerce")
v2 = v2.dropna(subset=["change_score"])

for case in cases:
    case_df = v2[v2["case"] == case].copy()

    if case_df.empty:
        print(f"\nNo V2_1pct evidence found for {case}")
        continue

    print("\n" + "=" * 90)
    print(f"CASE: {case}")
    print("=" * 90)

    # Compare service scores using the same evidence and four aggregations.
    grouped = case_df.groupby("service")["change_score"]

    scores = pd.DataFrame({
        "all_metric_mean": grouped.mean(),
        "all_metric_median": grouped.median(),
        "top_two_mean": grouped.apply(
            lambda x: x.nlargest(2).mean()
        ),
        "top_two_maximum": grouped.max(),
        "metric_count": grouped.size(),
    })

    for method in [
        "top_two_mean",
        "all_metric_median",
        "all_metric_mean",
        "top_two_maximum",
    ]:
        scores[f"{method}_rank"] = scores[method].rank(
            ascending=False, method="min"
        )

    print("\n--- Service-level scores and ranks ---")
    print(
        scores.sort_values("top_two_mean_rank")[
            [
                "metric_count",
                "top_two_mean", "top_two_mean_rank",
                "all_metric_median", "all_metric_median_rank",
                "all_metric_mean", "all_metric_mean_rank",
                "top_two_maximum", "top_two_maximum_rank",
            ]
        ].round(3).to_string()
    )

    print("\n--- Root-cause service: individual metric evidence ---")
    root = case_df[
        case_df["service"] == "productcatalogservice"
    ].sort_values("change_score", ascending=False)

    print(root.head(12).to_string(index=False))

    print("\n--- Strongest individual metrics across all services ---")
    print(
        case_df.sort_values("change_score", ascending=False)
        .head(15)
        .to_string(index=False)
    )

print("\nFinished. No input files were modified.")
