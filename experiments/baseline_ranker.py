
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "rcaeval_hf"
MANIFEST = ROOT / "data" / "rcaeval_case_manifest.csv"
RESULTS_DIR = ROOT / "experiments" / "results"

CASES = [
    "re1ob_adservice_cpu_1",
    "re1ob_adservice_delay_1",
    "re1ob_adservice_disk_1",
    "re1ob_adservice_loss_1",
    "re1ob_adservice_mem_1",
]

METRIC_SUFFIXES = (
    "_cpu", "_mem", "_load", "_latency", "_error"
)


def robust_scale(values):
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    return 1.4826 * mad


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(MANIFEST)
    all_rankings = []
    all_evidence = []

    for case in CASES:
        case_rows = manifest[manifest["case"] == case]

        if case_rows.empty:
            print(f"Skipping {case}: not found in manifest")
            continue

        root_cause = case_rows.iloc[0]["root_cause_service"]
        case_dir = DATA_DIR / case
        metrics_path = case_dir / "metrics.parquet"
        inject_path = case_dir / "inject_time.txt"

        if not metrics_path.exists() or not inject_path.exists():
            print(f"Skipping {case}: telemetry files are missing")
            continue

        df = pd.read_parquet(metrics_path)
        inject_time = int(inject_path.read_text().strip())

        # Match the original five-minute windows, excluding
        # the 60 seconds immediately around injection.
        pre = df[
            (df["time"] >= inject_time - 300)
            & (df["time"] <= inject_time - 60)
        ]
        post = df[
            (df["time"] >= inject_time + 60)
            & (df["time"] <= inject_time + 300)
        ]

        print(f"\nCase: {case}")
        print(f"Known root cause: {root_cause}")
        print(f"Pre-fault rows: {len(pre)}")
        print(f"Post-fault rows: {len(post)}")

        if pre.empty or post.empty:
            print("Skipping: one of the analysis windows is empty")
            continue

        evidence = []

        for metric in df.columns:
            if not metric.endswith(METRIC_SUFFIXES):
                continue

            pre_values = pre[metric].dropna().to_numpy(dtype=float)
            post_values = post[metric].dropna().to_numpy(dtype=float)

            if len(pre_values) == 0 or len(post_values) == 0:
                continue

            pre_median = float(np.median(pre_values))
            post_median = float(np.median(post_values))

            scale = robust_scale(pre_values)

            # Preserve the original baseline's fallback behavior.
            if scale <= 1e-12:
                scale = max(abs(pre_median) * 0.05, 1e-9)

            change_score = abs(post_median - pre_median) / scale
            service = metric.rsplit("_", 1)[0]

            evidence.append({
                "case": case,
                "service": service,
                "metric": metric,
                "pre_median": pre_median,
                "post_median": post_median,
                "change_score": change_score,
            })

        evidence_df = pd.DataFrame(evidence)

        if evidence_df.empty:
            print("No usable metrics found")
            continue

        # Average the two strongest metric changes per service.
        top_metrics = (
            evidence_df.sort_values(
                "change_score", ascending=False
            )
            .groupby("service", group_keys=False)
            .head(2)
        )

        ranked = (
            top_metrics.groupby("service")["change_score"]
            .mean()
            .rename("score")
            .reset_index()
            .sort_values("score", ascending=False)
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

        print("\nTop five ranked services:")
        print(
            ranked.head(5)[["rank", "service", "score"]]
            .to_string(index=False)
        )

        hit = bool(ranked.iloc[0]["service"] == root_cause)
        print(f"\nCorrect top-1 prediction: {hit}")

        all_rankings.append(ranked)
        evidence_df["root_cause_service"] = root_cause
        all_evidence.append(evidence_df)

    if not all_rankings:
        print("\nNo cases were successfully evaluated.")
        return

    rankings = pd.concat(all_rankings, ignore_index=True)
    evidence = pd.concat(all_evidence, ignore_index=True)

    rankings.to_csv(
        RESULTS_DIR / "baseline_rankings.csv", index=False
    )
    evidence.to_csv(
        RESULTS_DIR / "baseline_metric_evidence.csv", index=False
    )

    summary = (
        rankings.sort_values("rank")
        .groupby("case", as_index=False)
        .first()
    )

    hit_at_1 = (
        summary["service"] == summary["root_cause_service"]
    ).mean()

    print("\n" + "=" * 55)
    print("SMOKE-TEST SUMMARY")
    print("=" * 55)
    print(f"Cases evaluated: {len(summary)}")
    print(f"Hit@1: {hit_at_1:.3f}")
    print("This is a smoke test, not a research result.")
    print("\nSaved:")
    print(RESULTS_DIR / "baseline_rankings.csv")
    print(RESULTS_DIR / "baseline_metric_evidence.csv")


if __name__ == "__main__":
    main()
