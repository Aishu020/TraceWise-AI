"""TraceWise AI local API."""
import os
from copy import deepcopy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .analysis import analyze_incident
from .data import INCIDENTS, SERVICE_EDGES
from .rcaeval import router as rcaeval_router

app = FastAPI(
    title="TraceWise AI API",
    description="Local research prototype for evidence-grounded software incident investigation.",
    version="0.1.0",
)
app.include_router(rcaeval_router)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "").split(",")
    if origin.strip()
]

allowed_origins.extend([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "tracewise-ai", "mode": "local-demo"}


@app.get("/api/incidents")
def list_incidents():
    return [{k: v for k, v in item.items() if k != "signals"} for item in INCIDENTS]


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    incident = next((item for item in INCIDENTS if item["id"] == incident_id), None)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return deepcopy(incident)


@app.post("/api/incidents/{incident_id}/analyze")
def run_analysis(incident_id: str):
    incident = next((item for item in INCIDENTS if item["id"] == incident_id), None)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return analyze_incident(incident)


@app.get("/api/services/graph")
def service_graph():
    return {"nodes": sorted({edge[key] for edge in SERVICE_EDGES for key in ("source", "target")}), "edges": SERVICE_EDGES}



from pathlib import Path
import csv
import json


REPO_ROOT = Path(__file__).resolve().parents[2]


@app.get("/api/research/summary")
def research_summary():
    """Return saved RCAEval benchmark results and their evaluation context."""
    results_dir = REPO_ROOT / "experiments" / "results"
    summary_path = results_dir / "locked_candidate_98_summary.csv"
    protocol_path = REPO_ROOT / "experiments" / "tracewise_protocol.json"

    if not summary_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Benchmark summary not found. Run the locked candidate evaluator first.",
        )

    with summary_path.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise HTTPException(status_code=500, detail="Benchmark summary is empty.")

    def format_result(row):
        return {
            "version": row["version"],
            "cases": int(row["cases"]),
            "hit_at_1_pct": float(row["hit_at_1_pct"]),
            "hit_at_3_pct": float(row["hit_at_3_pct"]),
            "mrr": float(row["mrr"]),
            "mean_correct_rank": float(row["mean_correct_rank"]),
        }

    protocol = {}
    if protocol_path.is_file():
        with protocol_path.open("r", encoding="utf-8-sig") as file:
            protocol = json.load(file)

    results = [format_result(row) for row in rows]
    candidate = next(
        (row for row in results if row["version"] == "V2_1pct"),
        None,
    )

    return {
        "project": "TraceWise AI",
        "dataset": "RCAEval",
        "evaluation_split": "98 exploratory cases",
        "evaluation_status": "exploratory_not_independent_validation",
        "candidate": candidate,
        "results": results,
        "protocol_status": protocol.get("status", "not_recorded"),
        "interpretation": (
            "These results are exploratory. The 98 cases informed candidate "
            "development, so they are not an independent validation set. "
            "Ranking scores do not establish causal relationships."
        ),
    }
