
from pathlib import Path
import pandas as pd

path = Path("data/rcaeval_25_case_evaluation.csv")
df = pd.read_csv(path)

old_case = "re1ob_currencyservice_loss_1"
new_case = "re1ob_currencyservice_loss_2"

mask = df["case"] == old_case

if mask.sum() != 1:
    raise ValueError(
        f"Expected exactly one {old_case} row; found {mask.sum()}"
    )

if new_case in df["case"].values:
    raise ValueError(f"{new_case} is already selected.")

df.loc[mask, "case"] = new_case
df.loc[mask, "inject_time"] = 1692646911

df.to_csv(path, index=False)

print("Replaced the invalid case in the evaluation manifest.")
print(df.loc[mask, ["case", "root_cause_service", "fault", "inject_time"]])
print(f"\nCases selected: {df['case'].nunique()}")
print(f"Manifest saved: {path}")
