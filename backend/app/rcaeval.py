
"""Read-only access to saved RCAEval RE2-OB evaluation results."""

from pathlib import Path
import csv

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/research/rcaeval", tags=["RCAEval"])

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "experiments" / "results"

CASE_RESULTS_FILE = RESULTS_DIR / "locked_candidate_re2ob_90_case_results.csv"
RANKINGS_FILE = RESULTS_DIR / "locked_candidate_re2ob_90_rankings.csv"
EVIDENCE_FILE = RESULTS_DIR / "locked_candidate_re2ob_90_metric_evidence.csv"


def read_csv(path: Path) -> list[dict]:
    """Read a saved CSV without modifying the benchmark files."""
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Required saved evaluation file is missing: {path.name}",
        )

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def as_int(value: str) -> int:
    return int(float(value))


def as_float(value: str) -> float:
    return float(value)


@router.get("/cases")
def list_cases(
    search: str = Query(default="", max_length=150),
    limit: int = Query(default=25, ge=1, le=90),
    offset: int = Query(default=0, ge=0),
):
    """List unique cases in the saved 90-case RE2-OB evaluation."""
    rows = read_csv(CASE_RESULTS_FILE)

    # Each case appears once per candidate version. Deduplicate by case ID.
    unique = {}
    for row in rows:
        case_id = row["case"]
        if case_id not in unique:
            unique[case_id] = {
                "case_id": case_id,
                "fault_type": row["fault"],
                "available_versions": [],
            }
        if row["version"] not in unique[case_id]["available_versions"]:
            unique[case_id]["available_versions"].append(row["version"])

    cases = sorted(unique.values(), key=lambda item: item["case_id"])

    if search.strip():
        needle = search.strip().lower()
        cases = [
            item for item in cases
            if needle in item["case_id"].lower()
            or needle in item["fault_type"].lower()
        ]

    total = len(cases)
    return {
        "dataset": "RCAEval",
        "evaluation_split": "RE2-OB saved 90-case evaluation",
        "evaluation_status": "benchmark_results_not_live_inference",
        "total": total,
        "offset": offset,
        "limit": limit,
        "cases": cases[offset:offset + limit],
        "note": (
            "These are previously evaluated benchmark cases. "
            "This endpoint does not analyze new telemetry."
        ),
    }


@router.get("/cases/{case_id}")
def get_case_results(case_id: str):
    """Return saved V2_1pct and V1 rankings and metric evidence for a case."""
    case_rows = [
        row for row in read_csv(CASE_RESULTS_FILE)
        if row["case"] == case_id
    ]

    if not case_rows:
        raise HTTPException(status_code=404, detail="RCAEval case not found")

    ranking_rows = [
        row for row in read_csv(RANKINGS_FILE)
        if row["case"] == case_id
    ]
    evidence_rows = [
        row for row in read_csv(EVIDENCE_FILE)
        if row["case"] == case_id
    ]

    def format_case(row):
        return {
            "version": row["version"],
            "correct_root_cause_rank": as_int(row["correct_root_cause_rank"]),
            "hit_at_1": bool(as_int(row["hit_at_1"])),
            "hit_at_3": bool(as_int(row["hit_at_3"])),
            "reciprocal_rank": as_float(row["reciprocal_rank"]),
            "pre_rows": as_int(row["pre_rows"]),
            "post_rows": as_int(row["post_rows"]),
            "usable_metrics": as_int(row["usable_metrics"]),
            "services_ranked": as_int(row["services_ranked"]),
            "tied_at_top": bool(as_int(row["tied_at_top"])),
        }

    def format_ranking(row):
        return {
            "service": row["service"],
            "service_score": as_float(row["service_score"]),
            "metric_count": as_int(row["metric_count"]),
            "rank": as_int(row["rank"]),
        }

    def format_evidence(row):
        return {
            "service": row["service"],
            "metric": row["metric"],
            "pre_samples": as_int(row["pre_samples"]),
            "post_samples": as_int(row["post_samples"]),
            "pre_median": as_float(row["pre_median"]),
            "post_median": as_float(row["post_median"]),
            "robust_scale": as_float(row["robust_scale"]),
            "effective_scale": as_float(row["effective_scale"]),
            "change_score": as_float(row["change_score"]),
        }

    versions = {}
    for case_row in case_rows:
        version = case_row["version"]
        versions[version] = {
            "evaluation": format_case(case_row),
            "rankings": sorted(
                [
                    format_ranking(row)
                    for row in ranking_rows
                    if row["version"] == version
                ],
                key=lambda item: (item["rank"], item["service"]),
            ),
            "metric_evidence": sorted(
                [
                    format_evidence(row)
                    for row in evidence_rows
                    if row["version"] == version
                ],
                key=lambda item: (-item["change_score"], item["metric"]),
            ),
        }

    # Ground truth is deliberately not returned by this investigation endpoint.
    # It remains in the saved evaluation files for benchmark scoring.
    first = case_rows[0]
    return {
        "case_id": case_id,
        "dataset": "RCAEval",
        "evaluation_split": "RE2-OB",
        "fault_type": first["fault"],
        "evaluation_status": "saved_benchmark_result_not_live_inference",
        "versions": versions,
        "interpretation": (
            "Rankings are previously computed benchmark results, not a live "
            "diagnosis. Scores indicate relative metric deviations and do not "
            "establish causality. Ground-truth labels are withheld from this "
            "case-inspection response to avoid presenting them as predictions."
        ),
    }
