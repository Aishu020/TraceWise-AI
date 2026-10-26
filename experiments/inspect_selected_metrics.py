
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "rcaeval_hf"

case = "re1ob_adservice_cpu_1"
case_dir = DATA_DIR / case

metrics_path = case_dir / "metrics.parquet"
injection_path = case_dir / "inject_time.txt"

if not metrics_path.exists():
    raise FileNotFoundError(
        f"Missing metrics file: {metrics_path}"
    )

if not injection_path.exists():
    raise FileNotFoundError(
        f"Missing injection timestamp: {injection_path}"
    )

metrics = pd.read_parquet(metrics_path)
injection_time = int(
    injection_path.read_text().strip()
)

print("Case:", case)
print("Rows:", len(metrics))
print("Columns:", len(metrics.columns))
print("Injection timestamp:", injection_time)
print("\nColumn names:")
print(metrics.columns.tolist())
print("\nFirst five rows:")
print(metrics.head().to_string(index=False))
print("\nMissing values:")
print(metrics.isna().sum().sum())
print("\nTimestamp range:")
print(metrics["time"].min(), "to", metrics["time"].max())
