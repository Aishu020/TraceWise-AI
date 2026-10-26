from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data/rcaeval_hf")
MANIFEST = Path("data/rcaeval_heldout_98.csv")
OUT_DIR = Path("experiments/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_SECONDS = 120
THRESHOLD = 3.0
PERSISTENCE = 5
SCALE_FLOOR_RATIO = 0.01
EPSILON = 1e-9

FAMILIES = {
    "cpu": "_cpu",
    "memory": "_mem",
    "workload": "_workload",
    "latency_p50": "_latency-50",
    "latency_p90": "_latency-90",
}

manifest = pd.read_csv(MANIFEST)
loss_cases = manifest[
    manifest["fault"].astype(str).str.lower().eq("loss")
]

all_rows = []
summary_rows = []

for _, record in loss_cases.iterrows():
    case = str(record["case"])
    root = str(record["root_cause_service"])

    folder = DATA_DIR / case
    parquet_path = folder / "metrics.parquet"
    inject_path = folder / "inject_time.txt"

    if not parquet_path.exists() or not inject_path.exists():
        print(f"SKIP {case}: missing telemetry or injection timestamp")
        continue

    df = pd.read_parquet(parquet_path).sort_values("time").reset_index(drop=True)
    inject = int(inject_path.read_text(encoding="utf-8").strip())

    baseline = df[
        (df["time"] >= inject - BASELINE_SECONDS)
        & (df["time"] < inject)
    ]
    post = df[df["time"] >= inject].copy().reset_index(drop=True)

    if len(baseline) < 30 or len(post) < PERSISTENCE:
        print(f"SKIP {case}: insufficient observations")
        continue

    for family, suffix in FAMILIES.items():
        columns = [
            col for col in df.columns
            if col.endswith(suffix) and col != "time"
        ]

        family_rows = []

        for col in columns:
            service = col[:-len(suffix)]
            pre = pd.to_numeric(baseline[col], errors="coerce").dropna()
            values = pd.to_numeric(post[col], errors="coerce")

            if len(pre) < 30:
                continue

            median = float(pre.median())
            mad = float((pre - median).abs().median())
            scale = max(
                1.4826 * mad,
                SCALE_FLOOR_RATIO * abs(median),
                EPSILON,
            )

            deviation = (values - median).abs() / scale
            exceeds = (deviation >= THRESHOLD) & values.notna()

            rolling = exceeds.astype(int).rolling(
                PERSISTENCE, min_periods=PERSISTENCE
            ).sum()

            hits = np.flatnonzero(rolling.to_numpy() >= PERSISTENCE)

            onset_delay = np.nan
            onset_score = np.nan

            if len(hits):
                start = int(hits[0]) - PERSISTENCE + 1
                onset_delay = int(post.iloc[start]["time"]) - inject
                onset_score = float(deviation.iloc[start])

            family_rows.append({
                "case": case,
                "fault": "loss",
                "known_root_cause": root,
                "metric_family": family,
                "service": service,
                "detected": pd.notna(onset_delay),
                "onset_delay_seconds": onset_delay,
                "onset_deviation_score": onset_score,
            })

        family_df = pd.DataFrame(family_rows)

        if family_df.empty:
            continue

        detected = family_df[family_df["detected"]].copy()

        if not detected.empty:
            detected["onset_rank"] = detected[
                "onset_delay_seconds"
            ].rank(method="min", ascending=True)

            family_df = family_df.merge(
                detected[["service", "onset_rank"]],
                on="service",
                how="left",
            )
        else:
            family_df["onset_rank"] = np.nan

        all_rows.extend(family_df.to_dict("records"))

        root_rows = family_df[
            family_df["service"] == root
        ]

        # A missing root metric is not counted as a successful detection.
        root_row = root_rows.iloc[0] if not root_rows.empty else None
        root_detected = (
            bool(root_row["detected"])
            if root_row is not None else False
        )
        root_rank = (
            root_row["onset_rank"]
            if root_row is not None else np.nan
        )

        summary_rows.append({
            "case": case,
            "known_root_cause": root,
            "metric_family": family,
            "root_metric_available": root_row is not None,
            "root_metric_detected": root_detected,
            "root_onset_delay_seconds": (
                root_row["onset_delay_seconds"]
                if root_row is not None else np.nan
            ),
            "root_onset_rank": root_rank,
            "root_earliest": bool(
                root_detected and pd.notna(root_rank) and root_rank == 1
            ),
            "root_top3": bool(
                root_detected and pd.notna(root_rank) and root_rank <= 3
            ),
        })

details = pd.DataFrame(all_rows)
case_summary = pd.DataFrame(summary_rows)

details_path = OUT_DIR / "temporal_metric_family_loss_details.csv"
case_path = OUT_DIR / "temporal_metric_family_loss_case_summary.csv"

details.to_csv(details_path, index=False)
case_summary.to_csv(case_path, index=False)

aggregated = []

for family in FAMILIES:
    group = case_summary[
        case_summary["metric_family"] == family
    ]

    n = len(group)
    available = int(group["root_metric_available"].sum())
    detected = int(group["root_metric_detected"].sum())
    earliest = int(group["root_earliest"].sum())
    top3 = int(group["root_top3"].sum())

    aggregated.append({
        "metric_family": family,
        "cases_evaluated": n,
        "root_metric_available": available,
        "root_detected": detected,
        "root_detection_pct": round(100 * detected / n, 1) if n else np.nan,
        "root_earliest": earliest,
        "root_earliest_pct": round(100 * earliest / n, 1) if n else np.nan,
        "root_top3": top3,
        "root_top3_pct": round(100 * top3 / n, 1) if n else np.nan,
    })

aggregate = pd.DataFrame(aggregated)
aggregate_path = OUT_DIR / "temporal_metric_family_loss_summary.csv"
aggregate.to_csv(aggregate_path, index=False)

print("\n=== TEMPORAL LOCALIZATION BY METRIC FAMILY ===")
print(aggregate.to_string(index=False))

print("\nSaved aggregate:", aggregate_path.resolve())
print("Saved case details:", case_path.resolve())
print("Saved service details:", details_path.resolve())
