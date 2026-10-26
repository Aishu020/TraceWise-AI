from pathlib import Path
import pandas as pd
from huggingface_hub import snapshot_download

root = Path(".")
data = root / "data"

full = pd.read_csv(data / "rcaeval_case_manifest.csv")
selected = pd.read_csv(data / "rcaeval_25_case_evaluation.csv")

used = set(selected["case"])
bad_case = "re1ob_currencyservice_loss_1"

heldout = full[
    (~full["case"].isin(used)) &
    (full["case"] != bad_case)
].copy()

out = data / "rcaeval_heldout_99.csv"
heldout.to_csv(out, index=False)

print("Held-out cases:", len(heldout))
print("Service-fault combinations:", heldout.groupby(
    ["root_cause_service", "fault"]
).ngroups)
print("Cases per combination:")
print(heldout.groupby(["root_cause_service", "fault"]).size().value_counts().to_string())
print("Manifest saved:", out)

snapshot_download(
    repo_id="phamquiluan/RCAEval",
    repo_type="dataset",
    allow_patterns=[f"{case}/**" for case in heldout["case"]],
    local_dir=str(data / "rcaeval_hf"),
)

print("Download completed.")
