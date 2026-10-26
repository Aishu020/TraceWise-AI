# Phase 2 — Dataset inspection

## Goal

Move from synthetic demo incidents toward a reproducible evaluation using RCAEval, an open benchmark for microservice root-cause analysis. This first step reads the benchmark's case index only. It does not download all telemetry.

## Why start with RE1-OB?

RE1-OB is the metrics-only subset for Online Boutique. Starting with one subset keeps the first data-processing task small and lets us validate a baseline before adding logs and traces.

## Setup (Windows PowerShell)

Run from the `TraceWise-AI` project root. Activate the same backend virtual environment used by the API, then install the research-only dependencies:

```powershell
pip install -r experiments/requirements-research.txt
```

If you have not activated the backend environment yet:

```powershell
cd backend
.venv\Scripts\Activate.ps1
cd ..
pip install -r experiments/requirements-research.txt
```

Inspect the case index:

```powershell
python experiments/phase2_inspect_rcaeval.py --suite RE1-OB
```

The script reports the available subset names and writes a filtered manifest to `data/rcaeval_case_manifest.csv`. It reads `cases.parquet` through the Hugging Face dataset endpoint and does not download the full telemetry archives.

## Data integrity and research hygiene

- Keep the dataset's published labels for evaluation only; do not use the ground-truth root cause as an input feature.
- Keep a record of the dataset version, selected cases, preprocessing, and random seeds.
- Do not commit downloaded raw telemetry or large data files to GitHub. Commit the manifest only if its source terms permit it; otherwise regenerate it using the script.
- Check the benchmark license and citation requirements before redistribution or publication.
- Do not claim research performance until the selected cases have been run through the pipeline and compared against a documented baseline.

## Next step after inspection

Review the CSV and confirm the available columns and number of RE1-OB cases. Then implement a small telemetry loader and a first evaluation baseline. We should not connect dataset labels directly to the UI as if they were AI predictions.
