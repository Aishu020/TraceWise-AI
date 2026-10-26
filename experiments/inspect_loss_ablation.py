from pathlib import Path
import pandas as pd

results_dir = Path("experiments/results")
input_file = results_dir / "heldout_98_aggregation_ablation_case_results.csv"

df = pd.read_csv(input_file)

required = {
    "case", "fault", "known_root_cause", "method", "rank",
    "hit_at_1", "hit_at_3", "reciprocal_rank"
}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {sorted(missing)}")

methods = [
    "Top-two mean",
    "All-metric median",
    "All-metric mean",
    "Top-two maximum",
]

wide = df.pivot(
    index=["case", "fault", "known_root_cause"],
    columns="method",
    values="rank",
).reset_index()

for method in methods:
    if method not in wide.columns:
        raise ValueError(f"Missing method in results: {method}")

# Positive rank change means the candidate moved the true service upward.
for method in methods:
    if method != "Top-two mean":
        wide[f"{method}_rank_gain"] = (
            wide["Top-two mean"] - wide[method]
        )

loss = wide[wide["fault"].astype(str).str.lower() == "loss"].copy()

print("\n=== LOSS-FAULT RANKS: ALL 19 CASES ===")
print(
    loss[
        [
            "case", "known_root_cause",
            "Top-two mean", "All-metric median",
            "All-metric mean", "Top-two maximum",
        ]
    ].sort_values(["known_root_cause", "case"]).to_string(index=False)
)

print("\n=== PRODUCTCATALOGSERVICE LOSS CASES ===")
product_loss = loss[
    loss["known_root_cause"] == "productcatalogservice"
].copy()

if product_loss.empty:
    print("No productcatalogservice loss cases found.")
else:
    print(
        product_loss[
            [
                "case", "Top-two mean", "All-metric median",
                "All-metric mean", "Top-two maximum",
                "All-metric mean_rank_gain",
            ]
        ].sort_values("case").to_string(index=False)
    )

print("\n=== SUMMARY FOR LOSS FAULTS ===")
summary = (
    df[df["fault"].astype(str).str.lower() == "loss"]
    .groupby("method", as_index=False)
    .agg(
        cases=("case", "nunique"),
        hit_at_1=("hit_at_1", "mean"),
        hit_at_3=("hit_at_3", "mean"),
        mrr=("reciprocal_rank", "mean"),
        mean_correct_rank=("rank", "mean"),
    )
)

print(summary.round(4).to_string(index=False))

out = results_dir / "heldout_98_loss_case_comparison.csv"
loss.to_csv(out, index=False)
print(f"\nSaved detailed comparison to: {out.resolve()}")
