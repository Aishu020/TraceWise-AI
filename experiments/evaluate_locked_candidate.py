from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HF = DATA / "rcaeval_hf"
OUT = ROOT / "experiments" / "results"
MANIFEST = DATA / "rcaeval_heldout_98.csv"
PROTOCOL = ROOT / "experiments" / "tracewise_protocol.json"

SUFFIXES = ("_cpu", "_mem", "_load", "_latency", "_error")
FLOOR = 0.01
EPS = 1e-9


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
    folder = HF / case
    metrics_path = folder / "metrics.parquet"
    inject_path = folder / "inject_time.txt"

    if not metrics_path.exists() or not inject_path.exists():
        raise FileNotFoundError(f"{case}: missing telemetry or injection file")

    df = pd.read_parquet(metrics_path)
    inject = int(inject_path.read_text(encoding="utf-8-sig").strip())

    if "time" not in df.columns:
        raise ValueError(f"{case}: missing time column")

    # Fixed protocol windows: [injection-300, injection-60]
    # and [injection+60, injection+300], inclusive.
    pre = df[(df["time"] >= inject - 300) & (df["time"] <= inject - 60)]
    post = df[(df["time"] >= inject + 60) & (df["time"] <= inject + 300)]

    if pre.empty or post.empty:
        raise ValueError(
            f"{case}: empty window (pre={len(pre)}, post={len(post)}); "
            "do not silently skip cases."
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
                "fault": str(item["fault"]),
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

        # Candidate method: arithmetic mean across all available
        # metric scores for each service.
        scores = (
            subset.groupby("service", as_index=False)
            .agg(service_score=("change_score", "mean"),
                 metric_count=("metric", "nunique"))
        )

        # Competition ranking: exact score ties share the same rank.
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
            "fault": str(item["fault"]),
            "root_cause_service": truth,
            "version": version,
            "correct_root_cause_rank": root_rank,
            "hit_at_1": int(root_rank <= 1),
            "hit_at_3": int(root_rank <= 3),
            "reciprocal_rank": 1.0 / root_rank,
            "pre_rows": len(pre),
            "post_rows": len(post),
            "usable_metrics": int(
                subset["metric"].nunique()
            ),
            "services_ranked": int(scores["service"].nunique()),
            "tied_at_top": int((scores["rank"] == 1).sum()),
        })
        rankings.append(scores)

    return pd.DataFrame(case_results), pd.concat(rankings), ev


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    with PROTOCOL.open("r", encoding="utf-8-sig") as f:
        protocol = json.load(f)

    manifest = pd.read_csv(MANIFEST)
    if manifest["case"].duplicated().any():
        raise ValueError("Duplicate cases found in evaluation manifest")

    expected = int(protocol["evaluation"]["exploratory_case_count"])
    if len(manifest) != expected:
        raise ValueError(
            f"Expected {expected} cases from protocol, found {len(manifest)}"
        )

    all_results, all_rankings, all_evidence = [], [], []

    for _, item in manifest.iterrows():
        result, ranking, evidence = evaluate_case(item)
        all_results.append(result)
        all_rankings.append(ranking)
        all_evidence.append(evidence)
        print(f"Evaluated {item['case']}")

    results = pd.concat(all_results, ignore_index=True)
    rankings = pd.concat(all_rankings, ignore_index=True)
    evidence = pd.concat(all_evidence, ignore_index=True)

    if results["case"].nunique() != expected:
        raise ValueError("Evaluated case count does not match manifest")

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

    prefix = OUT / "locked_candidate_98"
    output_files = [
        Path(f"{prefix}_case_results.csv"),
        Path(f"{prefix}_rankings.csv"),
        Path(f"{prefix}_metric_evidence.csv"),
        Path(f"{prefix}_summary.csv"),
    ]

    existing = [str(path) for path in output_files if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing evaluation results:\n"
            + "\n".join(existing)
            + "\nUse the separate reproduction script or choose a new output prefix."
        )

    results.to_csv(output_files[0], index=False)
    rankings.to_csv(output_files[1], index=False)
    evidence.to_csv(output_files[2], index=False)
    summary.to_csv(output_files[3], index=False)

    print("\n=== LOCKED CANDIDATE EVALUATION ===")
    print("Manifest:", MANIFEST)
    print("Cases evaluated:", results["case"].nunique())
    print("Aggregation: all-metric arithmetic mean")
    print("V2 relative scale floor:", FLOOR)
    print("Windows: injection +/- 60 to 300 seconds, inclusive")
    print("Ties: competition rank; tied minimum rank counts as a hit")
    print("\n", summary.round(4).to_string(index=False))
    print("\nSaved new results with prefix:", prefix)
    print("New result files were created; existing outputs were checked before writing.")


if __name__ == "__main__":
    main()
