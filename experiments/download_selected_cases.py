
from pathlib import Path

from huggingface_hub import snapshot_download

CASES = [
    "re1ob_adservice_cpu_1",
    "re1ob_adservice_delay_1",
    "re1ob_adservice_disk_1",
    "re1ob_adservice_loss_1",
    "re1ob_adservice_mem_1",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "rcaeval_hf"

DATA_DIR.mkdir(parents=True, exist_ok=True)

patterns = [
    f"{case}/**"
    for case in CASES
]

print("Downloading selected RCAEval telemetry cases...")
print(f"Cases selected: {len(CASES)}")
print(f"Destination: {DATA_DIR}")

snapshot_download(
    repo_id="phamquiluan/RCAEval",
    repo_type="dataset",
    allow_patterns=patterns,
    local_dir=str(DATA_DIR),
)

print("\nDownload finished. Checking case files...")

for case in CASES:
    case_dir = DATA_DIR / case
    metrics_file = case_dir / "metrics.parquet"
    injection_file = case_dir / "inject_time.txt"

    print(f"\n{case}")
    print(f"  Metrics: {metrics_file.exists()}")
    print(f"  Injection time: {injection_file.exists()}")

print("\nNext: inspect metrics and verify timestamps.")
