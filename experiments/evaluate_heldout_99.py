from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HF = DATA / "rcaeval_hf"
OUT = ROOT / "experiments" / "results"
MANIFEST = DATA / "rcaeval_heldout_98.csv"

SUFFIXES = ("_cpu", "_mem", "_load", "_latency", "_error")
FLOOR = 0.01

def service_for_metric(metric):
    for suffix in SUFFIXES:
        if metric.endswith(suffix):
            return metric[:-len(suffix)]
    return None

def get_scale(values, version):
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    robust = 1.4826 * mad

    if version == "V1":
        if robust <= 1e-12:
            return max(abs(median) * 0.05, 1e-9)
        return robust

    return max(robust, FLOOR * abs(median), 1e-9)

def evaluate_case(item):
    case = item["case"]
    truth = item["root_cause_service"]
    folder = HF / case
    metrics_path = folder / "metrics.parquet"
    inject_path = folder / "inject_time.txt"

    if not metrics_path.exists() or not inject_path.exists():
        raise FileNotFoundError(f"Missing telemetry for {case}")

    df = pd.read_parquet(metrics_path)
    inject = int(inject_path.read_text().strip())

    pre = df[(df["time"] >= inject - 300) & (df["time"] <= inject - 60)]
    post = df[(df["time"] >= inject + 60) & (df["time"] <= inject + 300)]

    if len(pre) == 0 or len(post) == 0:
        raise ValueError(
            f"Empty window for {case}: pre={len(pre)}, post={len(post)}"
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

        pre_median = float(np.median(before))
        raw_change = abs(float(np.median(after)) - pre_median)

        for version in ("V1", "V2_1pct"):
            scale = get_scale(before, version)
            evidence.append({
                "case": case,
                "version": version,
                "service": service,
                "metric": metric,
                "pre_median": pre_median,
                "post_median": float(np.median(after)),
                "raw_change": raw_change,
                "scale": scale,
                "change_score": raw_change / scale,
            })

    ev = pd.DataFrame(evidence)
    if ev.empty:
        raise ValueError(f"No usable metric evidence for {case}")

    case_results = []
    case_rankings = []

    for version in ("V1", "V2_1pct"):
        part = ev[ev["version"] == version].copy()

        strongest = (
            part.sort_values("change_score", ascending=False)
            .groupby("service", group_keys=False)
            .head(2)
        )
        scores = (
            strongest.groupby("service")["change_score"]
            .mean()
            .sort_values(ascending=False)
        )

        ranking = list(scores.index)
        rank = ranking.index(truth) + 1 if truth in ranking else len(ranking) + 1

        case_results.append({
            "case": case,
            "dataset": item["dataset"],
            "fault": item["fault"],
            "known_root_cause": truth,
            "version": version,
            "correct_root_cause_rank": rank,
            "hit_at_1": rank == 1,
            "hit_at_3": rank <= 3,
            "reciprocal_rank": 1.0 / rank,
            "pre_samples": len(pre),
            "post_samples": len(post),
            "usable_metrics": part["metric"].nunique(),
        })

        for position, (service, score) in enumerate(scores.items(), start=1):
            case_rankings.append({
                "case": case,
                "version": version,
                "service": service,
                "score": float(score),
                "rank": position,
                "known_root_cause": truth,
            })

    return pd.DataFrame(case_results), pd.DataFrame(case_rankings), ev

manifest = pd.read_csv(MANIFEST)
all_results = []
all_rankings = []
all_evidence = []

for _, item in manifest.iterrows():
    results, rankings, evidence = evaluate_case(item)
    all_results.append(results)
    all_rankings.append(rankings)
    all_evidence.append(evidence)

    print(
        f"Processed {item['case']}: "
        f"{len(results)} method results"
    )

results = pd.concat(all_results, ignore_index=True)
rankings = pd.concat(all_rankings, ignore_index=True)
evidence = pd.concat(all_evidence, ignore_index=True)

OUT.mkdir(parents=True, exist_ok=True)
results.to_csv(OUT / "heldout_98_case_results.csv", index=False)
rankings.to_csv(OUT / "heldout_98_rankings.csv", index=False)
evidence.to_csv(OUT / "heldout_98_metric_evidence.csv", index=False)

summary = results.groupby("version").agg(
    cases=("case", "nunique"),
    hit_at_1=("hit_at_1", "mean"),
    hit_at_3=("hit_at_3", "mean"),
    mrr=("reciprocal_rank", "mean"),
    mean_correct_rank=("correct_root_cause_rank", "mean"),
).reset_index()

summary["hit_at_1_pct"] = (100 * summary["hit_at_1"]).round(2)
summary["hit_at_3_pct"] = (100 * summary["hit_at_3"]).round(2)
summary["mrr"] = summary["mrr"].round(3)
summary["mean_correct_rank"] = summary["mean_correct_rank"].round(3)
summary.to_csv(OUT / "heldout_98_summary.csv", index=False)

print("\nHELD-OUT RESULTS — 99 CASES")
print(summary[[
    "version", "cases", "hit_at_1_pct", "hit_at_3_pct",
    "mrr", "mean_correct_rank"
]].to_string(index=False))

print("\nRESULTS BY FAULT TYPE")
by_fault = results.groupby(["fault", "version"]).agg(
    cases=("case", "nunique"),
    hit_at_1=("hit_at_1", "mean"),
    hit_at_3=("hit_at_3", "mean"),
    mrr=("reciprocal_rank", "mean"),
).reset_index()
by_fault["hit_at_1_pct"] = (100 * by_fault["hit_at_1"]).round(1)
by_fault["hit_at_3_pct"] = (100 * by_fault["hit_at_3"]).round(1)
by_fault["mrr"] = by_fault["mrr"].round(3)
print(by_fault[[
    "fault", "version", "cases", "hit_at_1_pct", "hit_at_3_pct", "mrr"
]].to_string(index=False))

print("\nSaved results in:", OUT)
