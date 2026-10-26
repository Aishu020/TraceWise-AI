
from pathlib import Path
import numpy as np
import pandas as pd

case = "re1ob_adservice_delay_1"
data_dir = Path("data/rcaeval_hf") / case

df = pd.read_parquet(data_dir / "metrics.parquet")
inject_time = int(
    (data_dir / "inject_time.txt").read_text().strip()
)

pre = df[
    (df["time"] >= inject_time - 300)
    & (df["time"] <= inject_time - 60)
]
post = df[
    (df["time"] >= inject_time + 60)
    & (df["time"] <= inject_time + 300)
]

metrics = [
    "main_mem",
    "adservice_mem",
    "main_cpu",
    "adservice_cpu",
]

print(f"Case: {case}")
print(f"Injection timestamp: {inject_time}")
print(f"Pre-fault rows: {len(pre)}")
print(f"Post-fault rows: {len(post)}")

for metric in metrics:
    if metric not in df.columns:
        print(f"\nSkipping missing metric: {metric}")
        continue

    before = pre[metric].dropna()
    after = post[metric].dropna()

    pre_median = before.median()
    post_median = after.median()
    mad = (before - pre_median).abs().median()
    robust_scale = 1.4826 * mad

    # Match the baseline's fallback scale.
    if robust_scale <= 1e-12:
        robust_scale = max(abs(pre_median) * 0.05, 1e-9)

    raw_change = abs(post_median - pre_median)
    normalized_change = raw_change / robust_scale

    print(f"\n--- {metric} ---")
    print(f"Pre median:       {pre_median:.6f}")
    print(f"Post median:      {post_median:.6f}")
    print(f"Absolute change:  {raw_change:.6f}")
    print(f"Pre-fault MAD:    {mad:.6f}")
    print(f"Robust scale:     {robust_scale:.6f}")
    print(f"Normalized score:{normalized_change:10.4f}")
    print(f"Pre-fault IQR:    {before.quantile(.75) - before.quantile(.25):.6f}")
    print(f"Post-fault IQR:   {after.quantile(.75) - after.quantile(.25):.6f}")
