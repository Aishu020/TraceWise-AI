# TraceWise AI
### Explainable Root-Cause Analysis for Software Failures

TraceWise AI is a research-oriented project that investigates how metric-based anomaly analysis can help identify the services most likely to be responsible for failures in distributed software systems.

The project compares a baseline method with a modified anomaly-scoring approach using the RCAEval dataset. It presents previously computed service rankings and metric-level evidence to help users inspect and understand the results.

**Project status:** Research prototype  
**Developed in:** 2026  
**Primary focus:** Artificial Intelligence, anomaly detection, explainable root-cause analysis, and software reliability

---

## 1. The Problem

Modern software applications often consist of multiple interconnected services. When one service experiences a failure, its effects can spread to other services, making the original source difficult to identify.

For example, a CPU spike in one service may cause increased latency in another service. A monitoring system may detect both symptoms, but identifying which service is the likely root cause requires further investigation.

Traditional monitoring tools help detect abnormal behaviour, but detecting an anomaly does not automatically explain its cause.

TraceWise AI explores the following question:

**Can metric-based anomaly scoring help rank potentially responsible services more effectively, while providing evidence that supports the ranking?**

---

## 2. Project Objectives

The main objectives of TraceWise AI are to:

- Investigate metric-based approaches for identifying potential root-cause services.
- Compare a baseline anomaly-scoring method with a modified scoring method.
- Evaluate service-ranking performance using established ranking metrics.
- Provide metric-level evidence that helps explain why services receive higher anomaly scores.
- Make benchmark results inspectable through a working application.
- Establish a reproducible foundation for future research in explainable root-cause analysis.

---

## 3. How It Works

TraceWise AI follows a research pipeline that converts telemetry measurements into ranked service hypotheses.

1. **Dataset:** Use RCAEval cases containing telemetry associated with software failures.
2. **Time windows:** Select pre-fault and post-fault metric windows around the recorded fault-injection time.
3. **Metric analysis:** Compare metric behaviour between the selected windows.
4. **Anomaly scoring:** Calculate the deviation of each metric using a robust statistical scale.
5. **Service aggregation:** Aggregate metric scores into service-level scores.
6. **Ranking:** Rank services according to their aggregated anomaly scores.
7. **Evaluation:** Compare the rankings against the known root-cause labels using ranking metrics.
8. **Inspection:** Display previously computed rankings and metric-level evidence in the TraceWise AI application.

The current case explorer displays saved evaluation results. It should not be interpreted as performing a new live diagnosis whenever a case is selected.

---

## 4. Research Method

### Baseline V1

The baseline method uses metric deviations to calculate anomaly scores and aggregate them into service-level rankings.

### Candidate V2 — Robust Scale with a 1% Relative Scale Floor

The candidate method uses the median absolute deviation (MAD) to estimate a robust scale for each metric.

The effective scale is defined as:

`effective_scale = max(1.4826 × MAD, 0.01 × abs(pre_fault_median), 1e-9)`

The metric anomaly score is:

`score = abs(post_fault_median - pre_fault_median) / effective_scale`

The metric scores are aggregated using the arithmetic mean to obtain service-level scores. Services are then ranked in descending order of their scores.

The relative scale floor is intended to reduce excessive scores when a metric's estimated variation is very small. However, a high anomaly score alone does not prove that a service caused the failure.

### Evaluation windows

The current protocol uses the following inclusive time windows:

- **Pre-fault:** `[injection time − 300 seconds, injection time − 60 seconds]`
- **Post-fault:** `[injection time + 60 seconds, injection time + 300 seconds]`

The frozen benchmark protocol and its evaluation artifacts define the results reported below.

---

## 5. Dataset and Evaluation

TraceWise AI uses the RCAEval dataset for research into root-cause analysis in distributed systems.

The frozen primary comparison evaluates 90 cases from the **RE2-OB evaluation split**.

The methods are evaluated using:

- **Hit@1:** Whether the correct root-cause service is ranked first.
- **Hit@3:** Whether the correct service appears within the top three ranks.
- **Mean Reciprocal Rank (MRR):** The average reciprocal of the correct service's rank.
- **Mean correct rank:** The average rank position of the correct root-cause service. Lower is better.

### Frozen benchmark results

| Metric | Baseline V1 | Candidate V2 |
|---|---:|---:|
| Hit@1 | 76.67% | 75.56% |
| Hit@3 | 80.00% | 91.11% |
| MRR | 0.8189 | 0.8317 |
| Mean correct rank | 2.0000 | 1.8111 |

### Interpretation

In the frozen 90-case evaluation, Candidate V2:

- Improves Hit@3 by **11.11 percentage points**.
- Improves MRR from 0.8189 to 0.8317.
- Improves mean correct rank from 2.0000 to 1.8111.
- Decreases Hit@1 by **1.11 percentage points** compared with the baseline.

The results suggest a trade-off: Candidate V2 identifies the correct service within the top three more frequently, but it does not improve top-one accuracy in this evaluation.

### Paired ranking analysis

Across the 90 paired cases, the correct service's rank:

- Improved in 18 cases.
- Remained unchanged in 69 cases.
- Worsened in 3 cases.

The mean rank improvement was 0.1889 positions.

The frozen bootstrap analysis used 10,000 resamples with seed `20261020`. The reported confidence interval for the Hit@3 difference was 4.44 to 18.89 percentage points. The intervals for Hit@1, MRR, and mean rank improvement included zero.

These findings should be interpreted in the context of the evaluated cases and the limitations of the experimental design.

> **Research note:** The evaluation is a comparison on the RE2-OB split, not proof of causality or independent validation across all distributed-system environments.

---

## 6. Explainability and Evidence

TraceWise AI exposes saved metric-level evidence alongside service rankings.

This helps an investigator examine:

- Which services received the highest scores.
- The relative position of a service in each method's ranking.
- Which metrics contributed to the observed deviations.
- Whether the two methods produced different rankings for a case.
- How the ranking relates to the known evaluation outcome.

The evidence is intended to support inspection and interpretation. It does not establish that a highly ranked service caused the incident, nor does it replace independent debugging and verification.

---

## 7. Application Features

The current application includes:

- **Overview:** A dashboard for exploring the research prototype.
- **Incidents:** An interface for examining incident examples.
- **Service Map:** A visual representation of service relationships.
- **Evidence Explorer:** An area for inspecting available evidence.
- **Research Lab:** Access to research evaluation summaries and saved RCAEval results.
- **Case Explorer:** Search and select previously evaluated cases to inspect V1 and V2 rankings and metric evidence.
- **Log Explorer:** An interface for examining log examples.
- **Settings:** Application preferences, including theme selection.

The dashboard includes illustrative sample information. It should not be interpreted as a live production monitoring system unless connected to a real telemetry source.

The Research Lab and RCAEval Case Explorer are the primary research-focused components of the project.

---

## 8. Technology Stack

The project uses a web-based architecture with a separate frontend and backend.

| Component | Technology |
|---|---|
| Frontend | React, JavaScript, Vite |
| Backend | Python, FastAPI |
| API communication | HTTP/REST |
| Research computation | Python, statistical anomaly scoring |
| Dataset | RCAEval |
| Research artifacts | CSV evaluation results, protocol and Markdown reports |

The project is designed to use a local development environment without requiring paid AI APIs for its current metric-based research pipeline.

---

## 9. Running the Project Locally

### Prerequisites

Install the following:

- Python and the dependencies specified by the backend.
- Node.js and npm.
- Git (optional for local execution, required for repository workflows).

Use the Python version and package versions supported by the project's existing dependency files.

### Step 1 — Start the backend

Open a terminal in the project root and run:

```bash
cd backend
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend should be available at:

`http://127.0.0.1:8000`

If API documentation is enabled, visit:

`http://127.0.0.1:8000/docs`

### Step 2 — Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite, usually:

`http://localhost:5173`

### Step 3 — Verify the application

1. Confirm the frontend loads.
2. Confirm the backend connection indicator reports a successful connection.
3. Open the Research Lab.
4. Search for and select a saved RCAEval case.
5. Inspect the saved V1 and V2 rankings and metric-level evidence.
6. Switch between themes and check the other application sections.

If your local configuration uses a different API base URL, ensure it points to the running backend.

---

## 10. Research Artifacts

The `experiments/` directory contains research reports and saved evaluation artifacts.

Important artifacts include:

- `experiments/RE2_OB_EVALUATION_REPORT.md` — primary evaluation report.
- `experiments/EVALUATION_PROVENANCE.md` — evaluation provenance and supporting context.
- `experiments/tracewise_protocol.json` — frozen experimental protocol.
- `experiments/results/locked_candidate_re2ob_90_case_results.csv` — primary case-level results.
- `experiments/results/locked_candidate_re2ob_90_rankings.csv` — primary service-ranking results.
- `experiments/results/locked_candidate_re2ob_90_metric_evidence.csv` — primary metric-level evidence.
- `experiments/results/locked_candidate_98_summary.csv` — a separate exploratory evaluation summary.

The exact filenames in the repository should be checked before relying on these paths in scripts or documentation.

The 98-case exploratory evaluation is separate from the frozen 90-case RE2-OB comparison. Its results must not be substituted for the primary benchmark.

**Reproducibility principle:** Preserve the frozen evaluation outputs and protocol. New experiments should use separate output files and document their configuration, dataset split, and methodology.

---

## 11. Limitations

The current project has several limitations.

1. **Ranking is not causality.** A large metric deviation does not prove that a service caused an incident.
2. **Limited evaluation scope.** The primary frozen comparison covers 90 cases from RE2-OB and does not establish general performance across all systems.
3. **Top-one performance trade-off.** Candidate V2 improves Hit@3 but has lower Hit@1 than the baseline.
4. **Telemetry dependence.** Missing, noisy, or poorly sampled metrics can affect the reliability of the rankings.
5. **Limited evidence modalities.** The current scoring approach is metric-based and does not yet perform unified causal reasoning over metrics, logs, traces, and service dependencies.
6. **Saved results versus live inference.** The RCAEval Case Explorer presents previously computed results rather than executing a fresh diagnosis for every selection.
7. **Prototype scope.** The application is a research prototype, not a production-ready incident-management platform.

These limitations define areas for further experimentation and validation.

---

## 12. Future Enhancements

The following are proposed technical and research directions. They are **not claims about functionality already implemented**.

### 12.1 Multimodal telemetry analysis

Combine metrics, logs, distributed traces, and service dependency information to investigate whether multiple evidence sources improve root-cause ranking.

### 12.2 Causal root-cause analysis

Investigate methods that distinguish correlated symptoms from plausible causes. Compare ranking results with causal evidence where suitable ground truth or controlled fault-injection experiments are available.

### 12.3 Temporal anomaly detection

Replace or complement simple pre-fault and post-fault median comparisons with time-series approaches that capture trends, seasonality, delayed effects, and transient anomalies.

### 12.4 Learned service-ranking models

Compare the current statistical approach with supervised or weakly supervised ranking methods. Evaluate whether learned approaches generalize to unseen fault types and services.

### 12.5 Cross-dataset generalization

Evaluate the methods on additional suitable public datasets and fault scenarios. Keep training, validation, and test data separated to reduce data leakage and overfitting.

### 12.6 Ablation studies

Systematically compare alternative robust scales, scale-floor settings, service aggregation methods, and time-window choices. Record each experiment separately rather than overwriting the frozen benchmark.

### 12.7 Statistical reliability

Increase evaluation coverage where data permits, perform paired statistical analyses, report uncertainty, and investigate cases where a method improves or worsens the correct service's rank.

### 12.8 Missing and noisy telemetry

Study how missing metrics, irregular sampling, noisy observations, and incomplete service information affect ranking accuracy and evidence reliability.

---

## 13. Research Ethics and Responsible Interpretation

TraceWise AI is intended to support software debugging and research into root-cause analysis.

Its rankings should be treated as hypotheses for further investigation, not as definitive findings. Evaluation metrics describe performance on the tested cases and should not be generalized beyond the available evidence.

Future evaluations should document dataset provenance, experimental settings, limitations, and potential sources of bias.

---

## 14. Project Goal

TraceWise AI provides a foundation for investigating how robust statistical anomaly scoring and metric-level evidence can support root-cause analysis in distributed software systems.

The central research goal is not simply to produce a ranked list of services, but to understand **when the rankings are useful, why they change, where they fail, and whether additional evidence can make them more reliable**.

---

## Acknowledgements and References

- **Dataset:** RCAEval. Add the official dataset paper, repository, and applicable license or usage terms before public release.
- **Experimental details:** See the evaluation report, provenance document, frozen protocol, and saved CSV artifacts in the `experiments/` directory.

  ---

## ScreenShots

  <img width="944" height="440" alt="image" src="https://github.com/user-attachments/assets/9ec3509c-0fa6-4180-a1b1-3834ff513ad2" />

<img width="957" height="437" alt="image" src="https://github.com/user-attachments/assets/218720a0-8902-4e29-b3b3-908ec4060dd5" />

<img width="944" height="434" alt="image" src="https://github.com/user-attachments/assets/a0116ad0-e43f-4979-ac9d-324c50d012cb" />

<img width="947" height="437" alt="image" src="https://github.com/user-attachments/assets/7109aaab-4a06-4c4c-96a4-bcdcf4226994" />

<img width="946" height="435" alt="image" src="https://github.com/user-attachments/assets/77df25f5-efa2-4d28-b689-e7a206ac7f41" />

<img width="944" height="436" alt="image" src="https://github.com/user-attachments/assets/a2c5291a-1bf2-49d9-b36b-8cc92be3a574" />
