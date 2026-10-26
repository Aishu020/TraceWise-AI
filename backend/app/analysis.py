"""Interpretable evidence-based root-cause ranking baseline.

This is deliberately a transparent heuristic baseline, not a trained causal model.
Scores are relative ranking scores and must not be interpreted as probabilities.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def analyze_incident(incident: dict[str, Any]) -> dict[str, Any]:
    signals = incident.get("signals", [])
    by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in signals:
        by_service[signal.get("service", "unknown")].append(signal)

    candidates: list[dict[str, Any]] = []
    all_text = " ".join(
        f"{s.get('service', '')} {s.get('message', '')}" for s in signals
    ).lower()

    # Transparent rule features: temporal order and service-local signal keywords.
    pool_signals = [s for s in signals if _contains_any(
        f"{s.get('service', '')} {s.get('message', '')}", ("pool", "connection", "database")
    )]
    timeout_signals = [s for s in signals if _contains_any(
        f"{s.get('service', '')} {s.get('message', '')}", ("timeout", "timed out", "latency")
    )]
    retry_signals = [s for s in signals if _contains_any(
        f"{s.get('service', '')} {s.get('message', '')}", ("retry", "retries", "retrying")
    )]

    if pool_signals:
        candidates.append({
            "cause": "Database connection pool pressure",
            "raw_score": 0.42 + 0.12 * min(len(pool_signals), 2) + (0.10 if timeout_signals else 0),
            "evidence": [f"{s.get('time', 'Unknown time')}: {s.get('message', 'Database signal')} ({s.get('service', 'unknown')})" for s in pool_signals],
            "counter_evidence": ["The example does not include query-level evidence proving that the database is the initiating cause."],
            "next_check": "Inspect active connections, pool wait time, query duration, and configured connection limits.",
        })
    if retry_signals:
        candidates.append({
            "cause": "Retry amplification across dependent services",
            "raw_score": 0.35 + 0.12 * min(len(retry_signals), 2) + (0.05 if timeout_signals else 0),
            "evidence": [f"{s.get('time', 'Unknown time')}: {s.get('message', 'Retry signal')} ({s.get('service', 'unknown')})" for s in retry_signals],
            "counter_evidence": ["Retry events may be a response to an earlier failure rather than its original cause."],
            "next_check": "Compare retry counts and request rates before and after the first observed failure.",
        })
    if timeout_signals:
        candidates.append({
            "cause": "Slow or unavailable upstream dependency",
            "raw_score": 0.32 + 0.10 * min(len(timeout_signals), 3),
            "evidence": [f"{s.get('time', 'Unknown time')}: {s.get('message', 'Latency signal')} ({s.get('service', 'unknown')})" for s in timeout_signals],
            "counter_evidence": ["Latency is a symptom as well as a possible cause; the available sample is too small to establish direction."],
            "next_check": "Inspect distributed traces for the first slow span and compare dependency latency with its baseline.",
        })
    if not candidates:
        candidates.append({
            "cause": "Insufficient diagnostic evidence",
            "raw_score": 0.20,
            "evidence": ["No recognized database, timeout, latency, or retry signal was found."],
            "counter_evidence": ["The current rules cover only a small set of common signal patterns."],
            "next_check": "Collect timestamped logs, service metrics, and traces from the incident window.",
        })

    # Small, explicit heuristic for early signals: do not call this causal proof.
    if pool_signals and timeout_signals:
        first_pool = min(s.get("time", "99:99:99") for s in pool_signals)
        first_timeout = min(s.get("time", "99:99:99") for s in timeout_signals)
        if first_pool < first_timeout:
            for candidate in candidates:
                if candidate["cause"] == "Database connection pool pressure":
                    candidate["raw_score"] += 0.08
                    candidate["evidence"].append(
                        "The first pool-related signal precedes the first timeout signal in the supplied timestamps."
                    )

    candidates.sort(key=lambda item: item["raw_score"], reverse=True)
    max_score = max(item["raw_score"] for item in candidates) or 1.0
    hypotheses = []
    for rank, candidate in enumerate(candidates, start=1):
        relative_score = round(min(candidate["raw_score"] / max_score, 1.0), 3)
        hypotheses.append({
            "rank": rank,
            "cause": candidate["cause"],
            "score": relative_score,
            "confidence": "Moderate" if relative_score >= 0.85 and len(candidate["evidence"]) >= 2 else "Low–moderate" if relative_score >= 0.60 else "Low",
            "evidence": candidate["evidence"],
            "counter_evidence": candidate["counter_evidence"],
            "next_check": candidate["next_check"],
        })

    return {
        "incident_id": incident["id"],
        "method": "Interpretable heuristic baseline v0.1",
        "disclaimer": "Relative heuristic scores are not calibrated probabilities or proof of causation. The example telemetry is synthetic; verify every hypothesis against real traces and metrics.",
        "hypotheses": hypotheses,
        "signals_used": len(signals),
        "services_observed": len(by_service),
    }
