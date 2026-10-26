
from pathlib import Path
import pandas as pd
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
manifest_path = DATA_DIR / "rcaeval_25_case_evaluation.csv"

selected = pd.read_csv(manifest_path)
cases = selected["case"].dropna().astype(str).tolist()

print(f"Downloading data for {len(cases)} selected cases...")

snapshot_download(
    repo_id="phamquiluan/RCAEval",
    repo_type="dataset",
    allow_patterns=[f"{case}/**" for case in cases],
    local_dir=str(DATA_DIR / "rcaeval_hf"),
)

print("Download completed.")
