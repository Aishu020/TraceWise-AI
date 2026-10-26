from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data/rcaeval_hf")
OUT_DIR = Path("experiments/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CASES = {
    "re1ob_adservice_loss_2": "adservice",
    "re1ob_currencyservice_loss_4": "currencyservice",
    "re1ob_productcatalogservice_loss_4": "productcatalogservice",
}

BASELINE_SECONDS = 120
THRESHOLD = 3.0
PERSISTENCE = 5
SCALE_FLOOR_RATIO = 0.01
EPSILON = 1e-9

all_rows = []

for case, root_cause in CASES.items():
    case_dir = DATA_DIR / case
    parquet_path = case_dir / "metrics.parquet"
    inject_path = case_dir / "inject_time.txt"

    if not parquet_path.exists() or not inject_path.exists():
        print(f"SKIP {case}: telemetry or injection timestamp missing")
        continue

    df = pd.read_parquet(parquet_path).sort_values("time").reset_index(drop=True)
    inject_time = int(inject_path.read_text(encoding="utf-8").strip())

    if "time" not in df.columns:
        print(f"SKIP {case}: no time column")
        continue

    baseline = df[
        (df["time"] >= inject_time - BASELINE_SECONDS)
        & (df["time"] < inject_time)
    ]

    post = df[df["time"] >= inject_time].copy()

    print(f"\n{'=' * 72}")
    print(f"CASE: {case} | ROOT CAUSE: {root_cause}")
    print(f"Injection: {inject_time}")
    print(f"Baseline rows: {len(baseline)} | Post-injection rows: {len(post)}")

    if len(baseline) < 30 or len(post) < PERSISTENCE:
        print("Insufficient baseline or post-injection observations.")
        continue

    cpu_columns = [
        col for col in df.columns
        if col.endswith("_cpu")
    ]

    case_rows = []

    for col in cpu_columns:
        service = col[:-4]

        pre_values = pd.to_numeric(baseline[col], errors="coerce").dropna()
        post_values = pd.to_numeric(post[col], errors="coerce")

        if len(pre_values) < 30:
            continue

        pre_median = float(pre_values.median())
        mad = float((pre_values - pre_median).abs().median())
        robust_scale = 1.4826 * mad
        scale = max(
            robust_scale,
            SCALE_FLOOR_RATIO * abs(pre_median),
            EPSILON,
        )

        valid = post_values.notna()
        deviations = (post_values - pre_median).abs() / scale
        exceeds = (deviations >= THRESHOLD) & valid

        # Require five consecutive observations above threshold.
        rolling_count = (
            exceeds.astype(int)
            .rolling(PERSISTENCE, min_periods=PERSISTENCE)
            .sum()
        )
        hit_positions = np.flatnonzero(
            rolling_count.to_numpy() >= PERSISTENCE
        )

        onset_time = None
        onset_delay = None
        onset_score = None

        if len(hit_positions):
            end_position = int(hit_positions[0])
            start_position = end_position - PERSISTENCE + 1

            onset_time = int(post.iloc[start_position]["time"])
            onset_delay = onset_time - inject_time
            onset_score = float(deviations.iloc[start_position])

        row = {
            "case": case,
            "known_root_cause": root_cause,
            "service": service,
            "baseline_median": pre_median,
            "baseline_mad": mad,
            "effective_scale": scale,
            "threshold": THRESHOLD,
            "persistence_seconds": PERSISTENCE,
            "onset_time": onset_time,
            "onset_delay_seconds": onset_delay,
            "onset_deviation_score": onset_score,
            "detected": onset_time is not None,
        }

        case_rows.append(row)
        all_rows.append(row)

    result = pd.DataFrame(case_rows)

    result["onset_order"] = (
        result["onset_delay_seconds"]
        .rank(method="min", ascending=True)
    )

    result = result.sort_values(
        ["detected", "onset_delay_seconds", "service"],
        ascending=[False, True, True],
        na_position="last",
    )

    print("\nCPU anomaly onset results (earliest first):")
    print(
        result[
            [
                "service",
                "onset_delay_seconds",
                "onset_deviation_score",
                "onset_order",
            ]
        ].head(12).round(3).to_string(index=False)
    )

    root_rows = result[result["service"] == root_cause]

    if root_rows.empty:
        print(f"\nRoot CPU metric missing: {root_cause}_cpu")
    else:
        root_row = root_rows.iloc[0]
        print("\nRoot-cause CPU result:")
        print(f"  Detected: {root_row['detected']}")
        print(f"  Onset delay: {root_row['onset_delay_seconds']}")
        print(f"  Onset order: {root_row['onset_order']}")

out = OUT_DIR / "temporal_cpu_onset_3cases.csv"
pd.DataFrame(all_rows).to_csv(out, index=False)

print(f"\nSaved detailed results to: {out.resolve()}")
