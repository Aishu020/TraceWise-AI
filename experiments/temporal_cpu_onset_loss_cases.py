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

manifest = pd.read_csv(MANIFEST)

required = {"case", "root_cause_service", "fault"}
missing = required - set(manifest.columns)
if missing:
    raise ValueError(f"Missing manifest columns: {sorted(missing)}")

loss_cases = manifest[
    manifest["fault"].astype(str).str.lower().eq("loss")
].copy()

all_rows = []
case_rows = []

for _, record in loss_cases.iterrows():
    case = str(record["case"])
    root_cause = str(record["root_cause_service"])

    parquet_path = DATA_DIR / case / "metrics.parquet"
    inject_path = DATA_DIR / case / "inject_time.txt"

    if not parquet_path.exists() or not inject_path.exists():
        print(f"SKIP {case}: telemetry or injection timestamp missing")
        continue

    df = pd.read_parquet(parquet_path).sort_values("time").reset_index(drop=True)
    inject_time = int(inject_path.read_text(encoding="utf-8").strip())

    baseline = df[
        (df["time"] >= inject_time - BASELINE_SECONDS)
        & (df["time"] < inject_time)
    ]
    post = df[df["time"] >= inject_time].copy().reset_index(drop=True)

    if len(baseline) < 30 or len(post) < PERSISTENCE:
        print(f"SKIP {case}: insufficient baseline or post-injection data")
        continue

    cpu_columns = [c for c in df.columns if c.endswith("_cpu")]
    case_results = []

    for col in cpu_columns:
        service = col[:-4]

        pre_values = pd.to_numeric(baseline[col], errors="coerce").dropna()
        post_values = pd.to_numeric(post[col], errors="coerce")

        if len(pre_values) < 30:
            continue

        pre_median = float(pre_values.median())
        mad = float((pre_values - pre_median).abs().median())
        scale = max(
            1.4826 * mad,
            SCALE_FLOOR_RATIO * abs(pre_median),
            EPSILON,
        )

        deviation = (post_values - pre_median).abs() / scale
        exceeds = (deviation >= THRESHOLD) & post_values.notna()

        rolling = exceeds.astype(int).rolling(
            PERSISTENCE, min_periods=PERSISTENCE
        ).sum()

        hits = np.flatnonzero(rolling.to_numpy() >= PERSISTENCE)

        onset_time = None
        onset_delay = None
        onset_score = None

        if len(hits):
            start = int(hits[0]) - PERSISTENCE + 1
            onset_time = int(post.iloc[start]["time"])
            onset_delay = onset_time - inject_time
            onset_score = float(deviation.iloc[start])

        case_results.append({
            "case": case,
            "fault": "loss",
            "known_root_cause": root_cause,
            "service": service,
            "onset_time": onset_time,
            "onset_delay_seconds": onset_delay,
            "onset_deviation_score": onset_score,
            "detected": onset_time is not None,
        })

    if not case_results:
        print(f"SKIP {case}: no usable CPU metrics")
        continue

    result = pd.DataFrame(case_results)
    detected = result[result["detected"]].copy()
    detected["onset_rank"] = detected["onset_delay_seconds"].rank(
        method="min", ascending=True
    )

    result = result.merge(
        detected[["service", "onset_rank"]],
        on="service",
        how="left",
    )

    all_rows.extend(result.to_dict("records"))

    root_rows = result[result["service"] == root_cause]

    if root_rows.empty:
        root_detected = False
        root_delay = np.nan
        root_rank = np.nan
    else:
        root_row = root_rows.iloc[0]
        root_detected = bool(root_row["detected"])
        root_delay = root_row["onset_delay_seconds"]
        root_rank = root_row["onset_rank"]

    first_service = None
    first_delay = np.nan
    if not detected.empty:
        first_row = detected.sort_values(
            ["onset_delay_seconds", "service"]
        ).iloc[0]
        first_service = first_row["service"]
        first_delay = first_row["onset_delay_seconds"]

    case_rows.append({
        "case": case,
        "known_root_cause": root_cause,
        "root_cpu_detected": root_detected,
        "root_onset_delay_seconds": root_delay,
        "root_onset_rank": root_rank,
        "earliest_detected_service": first_service,
        "earliest_onset_delay_seconds": first_delay,
        "root_cause_is_earliest": (
            root_detected and root_rank == 1
            if pd.notna(root_rank) else False
        ),
        "root_cause_in_top3_onset": (
            root_detected and root_rank <= 3
            if pd.notna(root_rank) else False
        ),
        "detected_cpu_services": len(detected),
    })

case_summary = pd.DataFrame(case_rows)
service_details = pd.DataFrame(all_rows)

case_out = OUT_DIR / "temporal_cpu_onset_loss_summary.csv"
details_out = OUT_DIR / "temporal_cpu_onset_loss_services.csv"

case_summary.to_csv(case_out, index=False)
service_details.to_csv(details_out, index=False)

print("\n=== ROOT-CAUSE TEMPORAL RANKING: LOSS CASES ===")
if case_summary.empty:
    print("No cases were successfully evaluated.")
else:
    print(case_summary.sort_values("case").round(3).to_string(index=False))

    n = len(case_summary)
    detected_n = int(case_summary["root_cpu_detected"].sum())
    earliest_n = int(case_summary["root_cause_is_earliest"].sum())
    top3_n = int(case_summary["root_cause_in_top3_onset"].sum())

    print("\n=== SUMMARY ===")
    print(f"Cases evaluated: {n}")
    print(f"Root CPU anomaly detected: {detected_n}/{n} ({100*detected_n/n:.1f}%)")
    print(f"Root cause earliest: {earliest_n}/{n} ({100*earliest_n/n:.1f}%)")
    print(f"Root cause in onset top 3: {top3_n}/{n} ({100*top3_n/n:.1f}%)")

    print("\n=== EARLIEST DETECTED SERVICES ===")
    print(
        case_summary["earliest_detected_service"]
        .fillna("No CPU anomaly detected")
        .value_counts()
        .to_string()
    )

print(f"\nSaved case summary: {case_out.resolve()}")
print(f"Saved service details: {details_out.resolve()}")
