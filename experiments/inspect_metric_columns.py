from pathlib import Path
import pandas as pd

case = "re1ob_adservice_loss_2"
path = Path("data/rcaeval_hf") / case / "metrics.parquet"

df = pd.read_parquet(path)

print("Total columns:", len(df.columns))
print("\nAll metric columns:")
for col in df.columns:
    if col != "time":
        print(col)

keywords = [
    "cpu", "mem", "load", "latency", "duration",
    "response", "request", "error", "throughput",
    "traffic", "network", "disk", "loss"
]

print("\n=== COLUMNS GROUPED BY SEARCH KEYWORD ===")
for keyword in keywords:
    matches = [c for c in df.columns if keyword in c.lower()]
    if matches:
        print(f"\n{keyword.upper()} ({len(matches)}):")
        for col in matches[:20]:
            print(" ", col)
