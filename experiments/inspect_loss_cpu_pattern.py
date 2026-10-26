from pathlib import Path
import pandas as pd

path = Path("experiments/results/heldout_98_metric_evidence.csv")
df = pd.read_csv(path)

df = df[df["version"] == "V2_1pct"].copy()
df["change_score"] = pd.to_numeric(df["change_score"], errors="coerce")
df["raw_change"] = pd.to_numeric(df["raw_change"], errors="coerce")

loss = df[df["case"].str.contains("_loss_", na=False)].copy()

# Recover the known root-cause service from the case name.
loss["known_root_cause"] = loss["case"].str.extract(
    r"^re1ob_(.+)_loss_\d+$"
)[0]

loss = loss.dropna(subset=["known_root_cause", "change_score"])

print("\n=== LOSS CASES: ROOT-CAUSE CPU VS STRONGEST COMPETING CPU ===")

rows = []

for case, group in loss.groupby("case"):
    root = group["known_root_cause"].iloc[0]

    cpu = group[group["metric"].astype(str).str.endswith("_cpu")].copy()
    root_cpu = cpu[cpu["service"] == root]

    if root_cpu.empty:
        root_score = float("nan")
        root_change = float("nan")
        root_cpu_rank = None
    else:
        root_row = root_cpu.sort_values("change_score", ascending=False).iloc[0]
        root_score = root_row["change_score"]
        root_change = root_row["raw_change"]
        root_cpu_rank = int(
            cpu["change_score"].rank(ascending=False, method="min")[
                root_row.name
            ]
        )

    competitors = cpu[cpu["service"] != root].sort_values(
        "change_score", ascending=False
    )

    if competitors.empty:
        competitor_service = None
        competitor_score = float("nan")
        competitor_change = float("nan")
    else:
        competitor = competitors.iloc[0]
        competitor_service = competitor["service"]
        competitor_score = competitor["change_score"]
        competitor_change = competitor["raw_change"]

    rows.append({
        "case": case,
        "root_cause": root,
        "root_cpu_score": root_score,
        "root_cpu_raw_change": root_change,
        "root_cpu_rank": root_cpu_rank,
        "strongest_competitor": competitor_service,
        "competitor_cpu_score": competitor_score,
        "competitor_cpu_raw_change": competitor_change,
        "root_cpu_score_beats_competitor": (
            root_score > competitor_score
            if pd.notna(root_score) and pd.notna(competitor_score)
            else None
        ),
    })

summary = pd.DataFrame(rows).sort_values(["root_cause", "case"])

print(summary.round(3).to_string(index=False))

print("\n=== OVERALL DIAGNOSTIC SUMMARY ===")
print(f"Loss cases analyzed: {len(summary)}")
print(
    "Root CPU score exceeds strongest competing CPU:",
    int(summary["root_cpu_score_beats_competitor"].fillna(False).sum()),
    "of", len(summary)
)
print(
    "Root CPU change negative:",
    int((summary["root_cpu_raw_change"] < 0).sum()),
    "of", int(summary["root_cpu_raw_change"].notna().sum())
)

print("\n=== MOST FREQUENT STRONGEST COMPETING SERVICES ===")
print(summary["strongest_competitor"].value_counts().to_string())

out = Path("experiments/results/heldout_98_loss_cpu_diagnostic.csv")
summary.to_csv(out, index=False)
print(f"\nSaved: {out.resolve()}")
