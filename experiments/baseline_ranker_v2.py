
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# TRACEWISE AI - BASELINE RANKER V2
# Experimental change: minimum scale floor of 1% of baseline
# median magnitude.
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data" / "rcaeval_hf"
MANIFEST_PATH = ROOT / "data" / "rcaeval_case_manifest.csv"
RESULTS_DIR = ROOT / "experiments" / "results"

CASES = [
    "re1ob_adservice_cpu_1",
    "re1ob_adservice_delay_1",
    "re1ob_adservice_disk_1",
    "re1ob_adservice_loss_1",
    "re1ob_adservice_mem_1",
]

METRIC_SUFFIXES = (
    "_cpu",
    "_mem",
    "_load",
    "_latency",
    "_error",
)

# Experimental parameter: relative minimum scale.
SCALE_FLOOR_RATIO = 0.01


def robust_scale(values):
    """
    Calculate robust scale using the median absolute deviation.
    """
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    return 1.4826 * mad


def calculate_change_score(pre_values, post_values):
    """
    Calculate the normalized change between pre-fault and
    post-fault metric medians.

    V2 differs from V1 by applying a minimum scale equal to
    1% of the absolute pre-fault median.
    """
    pre_median = float(np.median(pre_values))
    post_median = float(np.median(post_values))

    scale = robust_scale(pre_values)

    relative_scale_floor = (
        SCALE_FLOOR_RATIO * abs(pre_median)
    )

    # Prevent division by a near-zero scale.
    scale = max(
        scale,
        relative_scale_floor,
        1e-9,
    )

    absolute_change = abs(post_median - pre_median)
    change_score = absolute_change / scale

    return {
        "pre_median": pre_median,
        "post_median": post_median,
        "absolute_change": absolute_change,
        "robust_scale": robust_scale(pre_values),
        "relative_scale_floor": relative_scale_floor,
        "effective_scale": scale,
        "change_score": change_score,
    }


def evaluate_case(case, manifest):
    """
    Load telemetry for one case and rank services by the mean
    of their two strongest metric-level change scores.
    """
    case_rows = manifest[manifest["case"] == case]

    if case_rows.empty:
        print(f"\nSkipping {case}: not found in manifest.")
        return None, None

    root_cause = str(
        case_rows.iloc[0]["root_cause_service"]
    )

    case_dir = DATA_DIR / case
    metrics_path = case_dir / "metrics.parquet"
    injection_path = case_dir / "inject_time.txt"

    if not metrics_path.exists():
        print(f"\nSkipping {case}: metrics.parquet not found.")
        return None, None

    if not injection_path.exists():
        print(f"\nSkipping {case}: inject_time.txt not found.")
        return None, None

    df = pd.read_parquet(metrics_path)
    inject_time = int(injection_path.read_text().strip())

    # Five-minute windows, excluding the 60 seconds around
    # injection to reduce contamination near the boundary.
    pre = df[
        (df["time"] >= inject_time - 300)
        & (df["time"] <= inject_time - 60)
    ]

    post = df[
        (df["time"] >= inject_time + 60)
        & (df["time"] <= inject_time + 300)
    ]

    print("\n" + "=" * 60)
    print(f"Case: {case}")
    print(f"Known root cause: {root_cause}")
    print(f"Injection timestamp: {inject_time}")
    print(f"Pre-fault rows: {len(pre)}")
    print(f"Post-fault rows: {len(post)}")

    if pre.empty or post.empty:
        print("Skipping: an analysis window is empty.")
        return None, None

    evidence_rows = []

    for metric in df.columns:
        if not metric.endswith(METRIC_SUFFIXES):
            continue

        pre_values = pre[metric].dropna().to_numpy(
            dtype=float
        )
        post_values = post[metric].dropna().to_numpy(
            dtype=float
        )

        if len(pre_values) == 0 or len(post_values) == 0:
            continue

        scores = calculate_change_score(
            pre_values,
            post_values,
        )

        # Strip the metric suffix to obtain its entity name.
        service = metric.rsplit("_", 1)[0]

        evidence_rows.append({
            "case": case,
            "service": service,
            "metric": metric,
            **scores,
        })

    evidence_df = pd.DataFrame(evidence_rows)

    if evidence_df.empty:
        print("Skipping: no usable metrics found.")
        return None, None

    # Preserve the original aggregation strategy:
    # average the two largest metric scores per entity.
    top_metrics = (
        evidence_df.sort_values(
            "change_score",
            ascending=False,
        )
        .groupby("service", group_keys=False)
        .head(2)
    )

    ranked = (
        top_metrics.groupby("service")["change_score"]
        .mean()
        .rename("score")
        .reset_index()
        .sort_values(
            "score",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    ranked.insert(0, "case", case)
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    ranked["root_cause_service"] = root_cause
    ranked["known_root_cause"] = (
        ranked["service"] == root_cause
    )
    ranked["hit_at_1"] = (
        (ranked["rank"] == 1)
        & ranked["known_root_cause"]
    )

    print("\nTop five ranked entities:")
    print(
        ranked.head(5)[
            ["rank", "service", "score"]
        ].to_string(index=False)
    )

    predicted = str(ranked.iloc[0]["service"])
    correct = predicted == root_cause

    print(f"\nPredicted top-1: {predicted}")
    print(f"Known root cause: {root_cause}")
    print(f"Correct top-1 prediction: {correct}")

    evidence_df["root_cause_service"] = root_cause

    return ranked, evidence_df


def main():
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}"
        )

    manifest = pd.read_csv(MANIFEST_PATH)

    all_rankings = []
    all_evidence = []

    print("=" * 60)
    print("TRACEWISE AI - BASELINE RANKER V2")
    print("=" * 60)
    print(
        "Normalization: MAD with a 1% relative scale floor"
    )
    print(f"Scale floor ratio: {SCALE_FLOOR_RATIO:.1%}")
    print(f"Cases requested: {len(CASES)}")

    for case in CASES:
        rankings, evidence = evaluate_case(
            case,
            manifest,
        )

        if rankings is not None:
            all_rankings.append(rankings)

        if evidence is not None:
            all_evidence.append(evidence)

    if not all_rankings:
        print("\nNo cases were successfully evaluated.")
        return

    rankings_df = pd.concat(
        all_rankings,
        ignore_index=True,
    )

    evidence_df = pd.concat(
        all_evidence,
        ignore_index=True,
    )

    rankings_path = (
        RESULTS_DIR / "baseline_rankings_v2.csv"
    )

    evidence_path = (
        RESULTS_DIR / "baseline_metric_evidence_v2.csv"
    )

    rankings_df.to_csv(
        rankings_path,
        index=False,
    )

    evidence_df.to_csv(
        evidence_path,
        index=False,
    )

    # Evaluate the first-ranked entity in each case.
    top_predictions = (
        rankings_df.sort_values("rank")
        .groupby("case", as_index=False)
        .first()
    )

    hits = (
        top_predictions["service"]
        == top_predictions["root_cause_service"]
    )

    hit_at_1 = float(hits.mean())

    print("\n" + "=" * 60)
    print("V2 SMOKE-TEST SUMMARY")
    print("=" * 60)
    print(f"Cases evaluated: {len(top_predictions)}")
    print(
        f"Correct top-1 predictions: {int(hits.sum())}"
        f" / {len(hits)}"
    )
    print(f"Hit@1: {hit_at_1:.3f}")

    print("\nSaved Version 2 results:")
    print(rankings_path)
    print(evidence_path)

    print("\nImportant:")
    print(
        "This is an exploratory smoke test, not a validated "
        "research result."
    )
    print(
        "The 1% scale floor is an experimental design choice "
        "that must be evaluated on more cases."
    )


if __name__ == "__main__":
    main()
