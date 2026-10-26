from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HF = DATA / "rcaeval_re2ob_candidate"
OUT = ROOT / "experiments" / "results"
METADATA = HF / "cases.parquet"

SUFFIXES = ("_cpu", "_mem", "_load", "_latency", "_error")
FLOOR = 0.01
EPS = 1e-9
EXPECTED_CASES = 90
PREFIX = "locked_candidate_re2ob_90"


def service_for_metric(metric):
    for suffix in SUFFIXES:
        if metric.endswith(suffix):
            return metric[:-len(suffix)]
    return None


def calculate_score(before, after, version):
    pre_median = float(np.median(before))
    post_median = float(np.median(after))
    mad = float(np.median(np.abs(before - pre_median)))
    robust = 1.4826 * mad

    if version == "V1":
        scale = robust if robust > 1e-12 else max(
            abs(pre_median) * 0.05, EPS
        )
    else:
        scale = max(robust, FLOOR * abs(pre_median), EPS)

    return {
        "pre_median": pre_median,
        "post_median": post_median,
        "robust_scale": robust,
        "effective_scale": scale,
        "change_score": abs(post_median - pre_median) / scale,
    }


def evaluate_case(item):
    case = str(item["case"])
    truth = str(item["root_cause_service"])
    fault = str(item["fault"])
    folder = HF / case
    metrics_path = folder / "metrics.parquet"
    inject_path = folder / "inject_time.txt"

    if not metrics_path.exists() or not inject_path.exists():
        raise FileNotFoundError(f"{case}: missing telemetry or injection file")

    df = pd.read_parquet(metrics_path)
    inject = int(inject_path.read_text(encoding="utf-8-sig").strip())

    if "time" not in df.columns:
        raise ValueError(f"{case}: missing time column")

    if inject != int(item["inject_time"]):
        raise ValueError(
            f"{case}: injection timestamp disagrees with official metadata"
        )

    # Frozen inclusive windows:
    # pre:  [injection-300, injection-60]
    # post: [injection+60, injection+300]
    pre = df[(df["time"] >= inject - 300) & (df["time"] <= inject - 60)]
    post = df[(df["time"] >= inject + 60) & (df["time"] <= inject + 300)]

    if pre.empty or post.empty:
        raise ValueError(
            f"{case}: empty window (pre={len(pre)}, post={len(post)})"
        )

    evidence = []
    for metric in df.columns:
        service = service_for_metric(metric)
        if service is None:
            continue

        before = pre[metric].dropna().to_numpy(dtype=float)
        after = post[metric].dropna().to_numpy(dtype=float)

        if len(before) == 0 or len(after) == 0:
            continue

        for version in ("V1", "V2_1pct"):
            score = calculate_score(before, after, version)
            evidence.append({
                "case": case,
                "fault": fault,
                "root_cause_service": truth,
                "version": version,
                "service": service,
                "metric": metric,
                "pre_samples": len(before),
                "post_samples": len(after),
                **score,
            })

    ev = pd.DataFrame(evidence)
    if ev.empty:
        raise ValueError(f"{case}: no usable metric evidence")

    case_results = []
    rankings = []

    for version in ("V1", "V2_1pct"):
        subset = ev[ev["version"] == version].copy()

        scores = (
            subset.groupby("service", as_index=False)
            .agg(
                service_score=("change_score", "mean"),
                metric_count=("metric", "nunique"),
            )
        )

        scores["rank"] = scores["service_score"].rank(
            method="min", ascending=False
        ).astype(int)
        scores["case"] = case
        scores["version"] = version
        scores["root_cause_service"] = truth
        scores["is_root_cause"] = scores["service"] == truth

        root_rows = scores[scores["is_root_cause"]]
        if root_rows.empty:
            raise ValueError(
                f"{case}: root-cause service {truth!r} has no usable score"
            )

        root_rank = int(root_rows["rank"].min())

        case_results.append({
            "case": case,
            "fault": fault,
            "root_cause_service": truth,
            "version": version,
            "correct_root_cause_rank": root_rank,
            "hit_at_1": int(root_rank <= 1),
            "hit_at_3": int(root_rank <= 3),
            "reciprocal_rank": 1.0 / root_rank,
            "pre_rows": len(pre),
            "post_rows": len(post),
            "usable_metrics": int(subset["metric"].nunique()),
            "services_ranked": int(scores["service"].nunique()),
            "tied_at_top": int((scores["rank"] == 1).sum()),
        })
        rankings.append(scores)

    return pd.DataFrame(case_results), pd.concat(rankings), ev


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    output_files = [
        OUT / f"{PREFIX}_case_results.csv",
        OUT / f"{PREFIX}_rankings.csv",
        OUT / f"{PREFIX}_metric_evidence.csv",
        OUT / f"{PREFIX}_summary.csv",
    ]

    # Check output paths before starting; never overwrite prior results.
    existing = [str(path) for path in output_files if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing files:\n" + "\n".join(existing)
        )

    if not METADATA.exists():
        raise FileNotFoundError(f"Missing metadata: {METADATA}")

    metadata = pd.read_parquet(METADATA)
    required = {"case", "dataset", "root_cause_service", "fault", "inject_time"}
    missing = required - set(metadata.columns)
    if missing:
        raise ValueError(f"Official metadata missing columns: {sorted(missing)}")

    manifest = metadata[
        metadata["dataset"].astype(str).str.upper().eq("RE2-OB")
    ].copy()

    if manifest["case"].duplicated().any():
        raise ValueError("Duplicate RE2-OB cases in official metadata")

    folders = {p.name for p in HF.glob("re2ob_*") if p.is_dir()}
    official_cases = set(manifest["case"].astype(str))

    if len(manifest) != EXPECTED_CASES:
        raise ValueError(
            f"Expected {EXPECTED_CASES} RE2-OB metadata cases; found {len(manifest)}"
        )

    if folders != official_cases:
        raise ValueError(
            "Downloaded folders and official RE2-OB metadata do not match. "
            f"Missing folders: {sorted(official_cases - folders)[:10]}; "
            f"unexpected folders: {sorted(folders - official_cases)[:10]}"
        )

    all_results, all_rankings, all_evidence = [], [], []

    for _, item in manifest.sort_values("case").iterrows():
        result, ranking, evidence = evaluate_case(item)
        all_results.append(result)
        all_rankings.append(ranking)
        all_evidence.append(evidence)
        print(f"Evaluated {item['case']}")

    results = pd.concat(all_results, ignore_index=True)
    rankings = pd.concat(all_rankings, ignore_index=True)
    evidence = pd.concat(all_evidence, ignore_index=True)

    if results["case"].nunique() != EXPECTED_CASES:
        raise ValueError("Evaluated case count does not match expected count")

    summary = (
        results.groupby("version", as_index=False)
        .agg(
            cases=("case", "nunique"),
            hit_at_1=("hit_at_1", "mean"),
            hit_at_3=("hit_at_3", "mean"),
            mrr=("reciprocal_rank", "mean"),
            mean_correct_rank=("correct_root_cause_rank", "mean"),
        )
    )
    summary["hit_at_1_pct"] = 100 * summary["hit_at_1"]
    summary["hit_at_3_pct"] = 100 * summary["hit_at_3"]

    # Recheck before writing in case output files appeared during evaluation.
    existing = [str(path) for path in output_files if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing files:\n" + "\n".join(existing)
        )

    results.to_csv(output_files[0], index=False)
    rankings.to_csv(output_files[1], index=False)
    evidence.to_csv(output_files[2], index=False)
    summary.to_csv(output_files[3], index=False)

    print("\n=== RE2-OB FROZEN CANDIDATE EVALUATION ===")
    print("Metadata:", METADATA)
    print("Telemetry folder:", HF)
    print("Cases evaluated:", results["case"].nunique())
    print("Aggregation: all-metric arithmetic mean")
    print("V2 relative scale floor:", FLOOR)
    print("Windows: injection -300 to -60 and +60 to +300 seconds, inclusive")
    print("Ties: competition ranking")
    print("\n", summary.round(4).to_string(index=False))
    print("\nCreated files:")
    for path in output_files:
        print(path)


if __name__ == "__main__":
    main()
