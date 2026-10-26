
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CASE = "re1ob_currencyservice_loss_1"

manifest = pd.read_csv(DATA_DIR / "rcaeval_25_case_evaluation.csv")
row = manifest[manifest["case"] == CASE]

print("=== Evaluation manifest ===")
if row.empty:
    print("Case not found in evaluation manifest.")
else:
    print(row.to_string(index=False))

case_dir = DATA_DIR / "rcaeval_hf" / CASE
inject_path = case_dir / "inject_time.txt"
metrics_path = case_dir / "metrics.parquet"

print("\n=== Raw injection timestamp file ===")
if inject_path.exists():
    raw = inject_path.read_bytes()
    print("Raw bytes:", repr(raw))
    print("Decoded text:", repr(raw.decode("utf-8", errors="replace")))
else:
    print("Injection file missing.")

print("\n=== Telemetry range ===")
if metrics_path.exists():
    df = pd.read_parquet(metrics_path)
    print("Rows:", len(df))
    print("Minimum time:", df["time"].min())
    print("Maximum time:", df["time"].max())
    print("Midpoint:", (df["time"].min() + df["time"].max()) // 2)

print("\n=== Nearby case timestamp comparison ===")
for other_case in [
    "re1ob_currencyservice_disk_1",
    "re1ob_currencyservice_mem_1",
    "re1ob_currencyservice_cpu_1",
    "re1ob_currencyservice_delay_1",
]:
    other_dir = DATA_DIR / "rcaeval_hf" / other_case
    other_inject = other_dir / "inject_time.txt"
    other_metrics = other_dir / "metrics.parquet"

    if other_inject.exists():
        print(f"\n{other_case}")
        print("Injection file:", repr(other_inject.read_text()))

    if other_metrics.exists():
        other_df = pd.read_parquet(other_metrics)
        print(
            "Telemetry range:",
            other_df["time"].min(),
            "to",
            other_df["time"].max(),
        )
