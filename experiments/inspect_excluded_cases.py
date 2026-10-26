from pathlib import Path
import pandas as pd

data = Path("data")
out = Path("experiments/results")

original = pd.read_csv(data / "rcaeval_case_manifest.csv")
tuning = pd.read_csv(data / "rcaeval_25_case_evaluation.csv")
heldout = pd.read_csv(data / "rcaeval_heldout_98.csv")

original_cases = set(original["case"].astype(str))
tuning_cases = set(tuning["case"].astype(str))
heldout_cases = set(heldout["case"].astype(str))

missing = sorted(original_cases - tuning_cases - heldout_cases)

print("\n=== CASES NOT IN EITHER EVALUATION MANIFEST ===")
if not missing:
    print("No missing cases.")
else:
    details = original[original["case"].astype(str).isin(missing)]
    print(details.to_string(index=False))

    details.to_csv(
        out / "excluded_case_review.csv",
        index=False
    )
    print("\nSaved:", (out / "excluded_case_review.csv").resolve())

print("\n=== CASE COUNTS ===")
print("Original:", len(original_cases))
print("Tuning:", len(tuning_cases))
print("Heldout:", len(heldout_cases))
print("Overlap:", len(tuning_cases & heldout_cases))
print("Missing from both:", len(missing))
