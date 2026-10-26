
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "experiments" / "results"

MANIFEST = DATA_DIR / "rcaeval_25_case_evaluation.csv"
HF_DIR = DATA_DIR / "rcaeval_hf"

METRIC_SUFFIXES = (
    "_cpu", "_mem", "_load", "_latency", "_error"
)

PRE_START = -300
PRE_END = -60
POST_START = 60
POST_END = 300


def service_for_metric(metric):
    for suffix in METRIC_SUFFIXES:
        if metric.endswith(suffix):
            return metric[:-len(suffix)]
    return None


def calculate_scale(pre_values, version):
    median = float(np.median(pre_values))
    mad = float(np.median(np.abs(pre_values - median)))
    robust_scale = 1.4826 * mad

    if version == "V1":
        if robust_scale <= 1e-12:
            return max(abs(median) * 0.05, 1e-9)
        return robust_scale

    if version == "V2":
        floor = 0.01 * abs(median)
        return max(robust_scale, floor, 1e-9)

    raise ValueError(f"Unknown version: {version}")


def evaluate_case(case, known_root_cause):
    case_dir = HF_DIR / case
    metrics_path = case_dir / "metrics.parquet"
    inject_path = case_dir / "inject_time.txt"

    if not metrics_path.exists() or not inject_path.exists():
        raise FileNotFoundError(
            f"Required data missing for {case}: {case_dir}"
        )

    df = pd.read_parquet(metrics_path)
    inject_time = int(inject_path.read_text().strip())

    pre = df[
        (df["time"] >= inject_time + PRE_START)
        & (df["time"] <= inject_time + PRE_END)
    ]
    post = df[
        (df["time"] >= inject_time + POST_START)
        & (df["time"] <= inject_time + POST_END)
    ]

    print(
        f"\n{case}: root cause={known_root_cause}, "
        f"pre={len(pre)}, post={len(post)}"
    )

    metric_columns = [
        col for col in df.columns
        if service_for_metric(col) is not None
    ]

    evidence = []

    for metric in metric_columns:
        service = service_for_metric(metric)

        before = pre[metric].dropna().to_numpy(dtype=float)
        after = post[metric].dropna().to_numpy(dtype=float)

        if len(before) == 0 or len(after) == 0:
            continue

        pre_median = float(np.median(before))
        post_median = float(np.median(after))
        raw_change = abs(post_median - pre_median)

        for version in ("V1", "V2"):
            scale = calculate_scale(before, version)
            change_score = raw_change / scale

            evidence.append({
                "case": case,
                "version": version,
                "service": service,
                "metric": metric,
                "pre_median": pre_median,
                "post_median": post_median,
                "raw_change": raw_change,
                "scale": scale,
                "change_score": change_score,
            })

    evidence_df = pd.DataFrame(evidence)

    if evidence_df.empty:
        raise ValueError(f"No usable metric evidence for {case}")

    rankings = []

    for version in ("V1", "V2"):
        version_evidence = evidence_df[
            evidence_df["version"] == version
        ].copy()

        # Match the baseline approach: average each service's
        # two largest metric-change scores.
        strongest_metrics = (
            version_evidence
            .sort_values("change_score", ascending=False)
            .groupby("service", group_keys=False)
            .head(2)
        )

        service_scores = (
            strongest_metrics
            .groupby("service", as_index=False)["change_score"]
            .mean()
            .rename(columns={"change_score": "score"})
            .sort_values(
                ["score", "service"],
                ascending=[False, True],
            )
            .reset_index(drop=True)
        )

        service_scores["rank"] = np.arange(
            1, len(service_scores) + 1
        )
        service_scores["case"] = case
        service_scores["version"] = version
        service_scores["known_root_cause"] = known_root_cause
        service_scores["is_correct"] = (
            service_scores["service"] == known_root_cause
        )

        rankings.append(service_scores)

    return evidence_df, pd.concat(rankings, ignore_index=True)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(MANIFEST)

    required = {"case", "root_cause_service"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")

    manifest = manifest.dropna(
        subset=["case", "root_cause_service"]
    ).drop_duplicates(subset=["case"])

    print("=" * 60)
    print("TRACEWISE AI: V1 vs V2 EVALUATION")
    print("=" * 60)
    print(f"Cases in manifest: {len(manifest)}")
    print("Both versions use identical cases and time windows.")

    all_evidence = []
    all_rankings = []

    for _, row in manifest.iterrows():
        evidence, rankings = evaluate_case(
            str(row["case"]),
            str(row["root_cause_service"]),
        )
        all_evidence.append(evidence)
        all_rankings.append(rankings)

    evidence_df = pd.concat(all_evidence, ignore_index=True)
    rankings_df = pd.concat(all_rankings, ignore_index=True)

    case_results = []

    for (version, case), group in rankings_df.groupby(
        ["version", "case"]
    ):
        truth = group["known_root_cause"].iloc[0]
        matching = group[group["service"] == truth]

        correct_rank = (
            int(matching["rank"].iloc[0])
            if not matching.empty else None
        )

        case_results.append({
            "version": version,
            "case": case,
            "known_root_cause": truth,
            "correct_root_cause_rank": correct_rank,
            "hit_at_1": (
                correct_rank == 1 if correct_rank is not None else False
            ),
            "hit_at_3": (
                correct_rank <= 3 if correct_rank is not None else False
            ),
            "reciprocal_rank": (
                1.0 / correct_rank
                if correct_rank is not None else 0.0
            ),
        })

    case_df = pd.DataFrame(case_results)

    summary = (
        case_df.groupby("version")
        .agg(
            cases=("case", "nunique"),
            hit_at_1=("hit_at_1", "mean"),
            hit_at_3=("hit_at_3", "mean"),
            mrr=("reciprocal_rank", "mean"),
        )
        .reset_index()
    )

    summary["hit_at_1_pct"] = summary["hit_at_1"] * 100
    summary["hit_at_3_pct"] = summary["hit_at_3"] * 100

    rankings_df.to_csv(
        RESULTS_DIR / "evaluation_25_rankings.csv", index=False
    )
    evidence_df.to_csv(
        RESULTS_DIR / "evaluation_25_metric_evidence.csv", index=False
    )
    case_df.to_csv(
        RESULTS_DIR / "evaluation_25_case_results.csv", index=False
    )
    summary.to_csv(
        RESULTS_DIR / "evaluation_25_summary.csv", index=False
    )

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(
        summary[
            ["version", "cases", "hit_at_1_pct",
             "hit_at_3_pct", "mrr"]
        ].to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )

    print("\nPer-case results:")
    print(
        case_df.pivot(
            index="case",
            columns="version",
            values="correct_root_cause_rank",
        ).to_string()
    )

    print("\nSaved four result files in:")
    print(RESULTS_DIR)


if __name__ == "__main__":
    main()
