# TraceWise AI — Evaluation Protocol

**Protocol version:** 1.0  
**Status:** Candidate method recorded; implementation audit required before final release.

## 1. Research objective

Evaluate whether robust changes in service telemetry can rank the known faulty service near the top of a root-cause investigation list.

The ranking is diagnostic evidence. It does not, by itself, establish causality.

## 2. Dataset and evaluation splits

The original manifest contains 125 unique cases. The current manifests contain:

- Tuning set: 25 unique cases.
- Exploratory set: 98 unique cases.
- Overlap between those manifests: zero.
- Cases excluded from both manifests: two, with reasons documented in `results/excluded_case_timestamp_audit.md`.

The 98-case set is described as **exploratory**, not an untouched test set. Its results were inspected during method development.

## 3. Candidate scoring method

For each metric, calculate the pre-fault and post-fault medians.

Robust scale:

`1.4826 × MAD`

Effective scale:

`max(robust scale, 0.01 × abs(pre-fault median), 1e-9)`

Metric anomaly score:

`abs(post-fault median − pre-fault median) / effective scale`

Aggregate available metric scores for each service using their arithmetic mean. Rank services by the resulting score, highest first.

The selected candidate is called **V2 all-metric mean**. The 1% scale floor and aggregation choice were informed by previous experiments. They must not be described as preregistered choices.

## 4. Evaluation metrics

- **Hit@1:** whether the known root-cause service ranks first.
- **Hit@3:** whether it appears among the top three ranked services.
- **MRR:** mean reciprocal rank of the known root-cause service.
- **Mean correct-service rank:** average rank of the known root-cause service; lower is better.

Before final release, verify the evaluator's treatment of ties, missing metrics, and cases where the root-cause service is absent.

## 5. Previously observed exploratory results

For V2 all-metric mean on the 98 exploratory cases:

| Metric | Result |
|---|---:|
| Hit@1 | 64.29% |
| Hit@3 | 78.57% |
| MRR | 0.7374 |
| Mean correct-service rank | 2.4592 |

These are historical exploratory results, not a new run and not independent validation.

## 6. Exclusions and data quality

`re1ob_currencyservice_loss_1` is excluded pending authoritative timestamp verification because its recorded injection time does not fall within the available telemetry interval.

`re1ob_productcatalogservice_cpu_3` is excluded pending source verification because the available telemetry ends 1456 seconds before the recorded injection time.

No source timestamps or telemetry have been altered.

## 7. Fair comparison rules

1. Compare methods on identical cases and identical pre/post windows.
2. Keep the tuning and exploratory manifests separate.
3. Do not select additional parameters based on the exploratory results and then describe those results as independent confirmation.
4. Preserve scripts and result files so reported metrics can be reproduced.
5. Report failures, missing data, and limitations rather than silently dropping cases.
6. Do not interpret anomaly magnitude as proof of causal responsibility.

## 8. Implementation checks still required

- Verify the exact pre/post window definitions in the evaluation scripts.
- Verify tie handling and missing-data behaviour.
- Reproduce the historical results from the saved inputs.
- Confirm that the application displays the same method and metric definitions as the experiment code.

## 9. Validation status

No untouched independent validation set has been established by this protocol. A future independent evaluation must use data not used to choose the scale floor, aggregation method, or other model settings.

## 10. Reproducibility artifacts

- `data/rcaeval_case_manifest.csv`
- `data/rcaeval_25_case_evaluation.csv`
- `data/rcaeval_heldout_98.csv`
- `experiments/results/evaluation_split_audit_summary.csv`
- `experiments/results/excluded_case_timestamp_audit.csv`
- `experiments/results/excluded_case_timestamp_audit.md`
- `experiments/tracewise_protocol.json`
