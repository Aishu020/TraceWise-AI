
from pathlib import Path
import pandas as pd

manifest_path = Path("data/rcaeval_case_manifest.csv")
manifest = pd.read_csv(manifest_path)

subset = manifest[manifest["dataset"] == "RE1-OB"].copy()

# One case for each root-cause service × fault type.
selected = (
    subset.sort_values("case")
    .drop_duplicates(
        subset=["root_cause_service", "fault"],
        keep="first",
    )
    .sort_values(["root_cause_service", "fault"])
)

output_path = Path("data/rcaeval_25_case_evaluation.csv")
selected.to_csv(output_path, index=False)

print(f"Selected cases: {len(selected)}")
print("\nCases per root-cause service:")
print(selected["root_cause_service"].value_counts().sort_index())

print("\nCases per fault type:")
print(selected["fault"].value_counts().sort_index())

print("\nSelected case IDs:")
print(selected[["case", "root_cause_service", "fault"]].to_string(index=False))

print(f"\nSaved to: {output_path}")
