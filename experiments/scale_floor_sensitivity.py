from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HF = DATA / "rcaeval_hf"

manifest = pd.read_csv(DATA / "rcaeval_25_case_evaluation.csv")
suffixes = ("_cpu", "_mem", "_load", "_latency", "_error")
floors = [0.001, 0.0025, 0.005, 0.01, 0.02]

def service_for_metric(metric):
    for suffix in suffixes:
        if metric.endswith(suffix):
            return metric[:-len(suffix)]
    return None

all_results = []

for _, item in manifest.iterrows():
    case = item["case"]
    truth = item["root_cause_service"]
    folder = HF / case
    df = pd.read_parquet(folder / "metrics.parquet")
    inject = int((folder / "inject_time.txt").read_text().strip())

    pre = df[(df["time"] >= inject - 300) & (df["time"] <= inject - 60)]
    post = df[(df["time"] >= inject + 60) & (df["time"] <= inject + 300)]

    evidence = []

    for metric in df.columns:
        service = service_for_metric(metric)
        if service is None:
            continue

        before = pre[metric].dropna().to_numpy(dtype=float)
        after = post[metric].dropna().to_numpy(dtype=float)
        if len(before) == 0 or len(after) == 0:
            continue

        median = float(np.median(before))
        raw_change = abs(float(np.median(after)) - median)
        mad = float(np.median(np.abs(before - median)))
        robust_scale = 1.4826 * mad

        evidence.append({
            "service": service,
            "median": median,
            "raw_change": raw_change,
            "robust_scale": robust_scale,
        })

    for floor in floors:
        rows = []
        for e in evidence:
            scale = max(
                e["robust_scale"],
                floor * abs(e["median"]),
                1e-9,
            )
            rows.append({
                "service": e["service"],
                "score": e["raw_change"] / scale,
            })

        scores = pd.DataFrame(rows)
        top_two = (
            scores.sort_values("score", ascending=False)
            .groupby("service", group_keys=False)
            .head(2)
        )
        service_scores = (
            top_two.groupby("service")["score"]
            .mean()
            .sort_values(ascending=False)
        )

        ranking = list(service_scores.index)
        rank = ranking.index(truth) + 1 if truth in ranking else len(ranking) + 1

        all_results.append({
            "case": case,
            "fault": item["fault"],
            "floor": floor,
            "correct_rank": rank,
            "hit_at_1": rank == 1,
            "hit_at_3": rank <= 3,
            "reciprocal_rank": 1 / rank,
        })

results = pd.DataFrame(all_results)
summary = results.groupby("floor").agg(
    cases=("case", "count"),
    hit_at_1=("hit_at_1", "mean"),
    hit_at_3=("hit_at_3", "mean"),
    mrr=("reciprocal_rank", "mean"),
    mean_correct_rank=("correct_rank", "mean"),
).reset_index()

for col in ["hit_at_1", "hit_at_3", "mrr"]:
    summary[col] = (100 * summary[col]).round(2) if col != "mrr" else summary[col].round(3)

summary["floor_percent"] = summary["floor"].map(lambda x: f"{x * 100:g}%")
print("SCALE-FLOOR SENSITIVITY — same 25 cases")
print(summary[["floor_percent", "cases", "hit_at_1", "hit_at_3", "mrr", "mean_correct_rank"]].to_string(index=False))

out = ROOT / "experiments" / "results" / "scale_floor_sensitivity.csv"
out.parent.mkdir(parents=True, exist_ok=True)
results.to_csv(out, index=False)
print(f"\nPer-case results saved to: {out}")

