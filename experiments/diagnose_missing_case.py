
from pathlib import Path
import pandas as pd

case = "re1ob_currencyservice_loss_1"
case_dir = Path("data/rcaeval_hf") / case

metrics_path = case_dir / "metrics.parquet"
inject_path = case_dir / "inject_time.txt"

print(f"Case: {case}")
print(f"Case directory exists: {case_dir.exists()}")
print(f"Metrics file exists: {metrics_path.exists()}")
print(f"Injection file exists: {inject_path.exists()}")

if not metrics_path.exists() or not inject_path.exists():
    raise FileNotFoundError(
        "The case's metrics or injection timestamp file is missing."
    )

df = pd.read_parquet(metrics_path)
inject_time = int(inject_path.read_text().strip())

print(f"\nRows in metrics file: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Injection timestamp: {inject_time}")

if "time" not in df.columns:
    raise ValueError("The metrics file has no 'time' column.")

print(f"Time column dtype: {df['time'].dtype}")

if not df.empty:
    print(f"Minimum time: {df['time'].min()}")
    print(f"Maximum time: {df['time'].max()}")
    print(f"First five time values: {df['time'].head().tolist()}")

    print("\nTime differences from injection timestamp:")
    print(f"Minimum difference: {df['time'].min() - inject_time}")
    print(f"Maximum difference: {df['time'].max() - inject_time}")

    print("\nRows in candidate windows:")
    for name, start, end in [
        ("Pre-fault", inject_time - 300, inject_time - 60),
        ("Post-fault", inject_time + 60, inject_time + 300),
    ]:
        count = df["time"].between(start, end).sum()
        print(f"{name}: {count}")

    print("\nMetric columns:")
    print([
        col for col in df.columns
        if col != "time"
    ])
else:
    print("\nThe metrics file itself contains zero rows.")
