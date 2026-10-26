
from pathlib import Path
import pandas as pd

path = Path("experiments/results/baseline_metric_evidence.csv")
df = pd.read_csv(path)

print("Available columns:")
print(df.columns.tolist())

case = "re1ob_adservice_delay_1"
delay = df[df["case"] == case].copy()

if delay.empty:
    print(f"\nNo evidence rows found for {case}")
else:
    score_column = "change_score"

    print("\nTop 15 metric-level changes for the delay case:")
    print(
        delay.sort_values(score_column, ascending=False)
        .head(15)
        .to_string(index=False)
    )

    print("\nEvidence for the two competing services:")
    if "service" in delay.columns:
        print(
            delay[delay["service"].isin(["adservice", "main"])]
            .sort_values(score_column, ascending=False)
            .to_string(index=False)
        )
