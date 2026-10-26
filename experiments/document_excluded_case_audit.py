from pathlib import Path
import pandas as pd

results = Path("experiments/results")
results.mkdir(parents=True, exist_ok=True)

rows = [
    {
        "case": "re1ob_currencyservice_loss_1",
        "root_cause_service": "currencyservice",
        "fault": "loss",
        "recorded_injection_time": 16933142,
        "telemetry_start": 1693313863,
        "telemetry_end": 1693314583,
        "telemetry_rows": 721,
        "injection_within_telemetry": False,
        "reason": (
            "Injection timestamp in the manifest and source text file "
            "does not fall within the telemetry interval. The intended "
            "timestamp cannot be verified from these files alone."
        ),
        "decision": "Exclude pending source verification",
    },
    {
        "case": "re1ob_productcatalogservice_cpu_3",
        "root_cause_service": "productcatalogservice",
        "fault": "cpu",
        "recorded_injection_time": 1685373255,
        "telemetry_start": 1685371737,
        "telemetry_end": 1685371799,
        "telemetry_rows": 63,
        "injection_within_telemetry": False,
        "reason": (
            "Telemetry ends 1456 seconds before the recorded injection. "
            "No post-injection observations are available in the current file."
        ),
        "decision": "Exclude pending source verification",
    },
]

df = pd.DataFrame(rows)
csv_path = results / "excluded_case_timestamp_audit.csv"
df.to_csv(csv_path, index=False)

note = """# RCAEval Excluded-Case Timestamp Audit

## Purpose
Document why two cases in the original 125-case manifest are not
included in the current tuning or exploratory evaluation manifests.

## Findings

### re1ob_currencyservice_loss_1
The injection-time text file and manifest both contain `16933142`.
The available telemetry spans `1693313863` to `1693314583` (721 rows).
The injection timestamp does not fall within this interval. The intended
timestamp cannot be established from the inspected files alone.

### re1ob_productcatalogservice_cpu_3
The injection-time text file and manifest both contain `1685373255`.
The available telemetry spans `1685371737` to `1685371799` (63 rows).
The telemetry ends 1456 seconds before the recorded injection, leaving
no post-injection observations in the available file.

## Decision
Both cases remain excluded pending verification against authoritative
source metadata or a verified replacement download. No timestamps or
source telemetry were modified.

## Limitations
This audit establishes incompatibility between the recorded injection
times and the available telemetry intervals. It does not establish the
original intended timestamp or the underlying reason for either mismatch.
"""
md_path = results / "excluded_case_timestamp_audit.md"
md_path.write_text(note, encoding="utf-8")

print("Saved:", csv_path.resolve())
print("Saved:", md_path.resolve())
print("\nAudit summary:")
print(df[["case", "telemetry_rows", "injection_within_telemetry", "decision"]].to_string(index=False))
