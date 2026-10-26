# Experiments

This directory contains the evaluation protocol, benchmark scripts,
diagnostic analyses, and result artifacts for TraceWise AI.

## Current evaluation status

The candidate has been evaluated on 98 exploratory RCAEval cases.
This set has informed development and is not an independent validation set.

The frozen candidate is the V2 all-metric mean method:

- Robust scale: 1.4826 × median absolute deviation (MAD)
- Relative scale floor: 1% of the absolute pre-fault median
- Metric score: absolute post/pre median change divided by effective scale
- Service score: arithmetic mean of all available metric scores
- Ranking: competition ranking; tied scores share a rank
- Pre-fault window: injection time −300 to −60 seconds, inclusive
- Post-fault window: injection time +60 to +300 seconds, inclusive

Two cases remain excluded because their recorded injection timestamps
are incompatible with available telemetry. No timestamps have been
silently corrected. See `results/excluded_case_timestamp_audit.md`.

## Exploratory results

| Version | Hit@1 | Hit@3 | MRR | Mean correct-service rank |
|---|---:|---:|---:|---:|
| V1 | 58.16% | 70.41% | 0.686152 | 2.8061 |
| V2, 1% scale floor | 64.29% | 78.57% | 0.737366 | 2.4592 |

These results are exploratory on a development-informed set. They do not
establish independent validation, generalization to unseen datasets, or
causal root-cause identification.

## Main artifacts

- `tracewise_protocol.json` — evaluation protocol and limitations
- `evaluate_locked_candidate.py` — frozen-candidate evaluator
- `reproduce_locked_candidate_98.py` — reproduction with separate outputs
- `EVALUATION_PROVENANCE.md` — evaluation history and provenance
- `results/locked_candidate_98_summary.csv` — frozen-candidate summary
- `results/reproduction_locked_candidate_98_summary.csv` — reproduced summary
- `results/excluded_case_timestamp_audit.md` — excluded-case audit

Historical scripts and results are retained for traceability. Do not rerun
`evaluate_heldout_99.py` without reviewing its manifest, ranking logic,
printed case count, and output destinations.

## Reproduction

From the project root, activate the backend virtual environment and run:

```powershell
python .\experiments\reproduce_locked_candidate_98.py
```

The script writes outputs using the `reproduction_locked_candidate_98`
prefix so the frozen-candidate outputs remain separate. Matching outputs
verify reproducibility with current inputs and code, not independent validation.

## Remaining research work

1. Review related root-cause analysis literature and refine the research gap.
2. Resolve the excluded cases using authoritative metadata or replacement data.
3. Establish an independent validation set or defensible untouched split.
4. Compare with suitable published baselines where feasible.
5. Evaluate controlled missingness and noise using fixed random seeds.
6. Run ablations and report uncertainty alongside ranking metrics.
7. Keep illustrative UI data separate from benchmark measurements.

Do not claim causal proof from temporal ordering or heuristic rankings.
