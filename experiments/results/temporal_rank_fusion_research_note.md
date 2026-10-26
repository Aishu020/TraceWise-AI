# TraceWise AI: Temporal Rank-Fusion Experiment

## 1. Objective

Investigate whether combining temporal anomaly-onset signals from CPU and latency metrics improves root-cause service localization for network-loss fault cases in RCAEval.

## 2. Dataset and scope

- Cases evaluated: 19 loss-fault cases.
- Evaluation unit: individual fault-injection case.
- Service universe: common services available across CPU, latency p50, and latency p90 within each case.
- Every compared method used the same service set within a given case.
- The experiment is exploratory and does not establish generalization to other fault types or datasets.

## 3. Method

For each metric family, an anomaly onset was detected using the existing temporal detection procedure. Services were ranked by onset delay, with undetected anomalies placed last. Ranks were normalized by the number of services plus one. For fusion methods, normalized ranks were averaged with equal weights.

The compared methods were CPU, latency p50, latency p90, and their pairwise and three-way combinations.

## 4. Results

| Method | Cases | Hit@1 | Hit@3 | MRR | Mean root rank |
|---|---:|---:|---:|---:|---:|
| CPU + latency p50 + latency p90 | 19 | 21.05% | 89.47% | 0.5307 | 2.368 |
| CPU + latency p50 | 19 | 31.58% | 78.95% | 0.5689 | 2.526 |
| CPU | 19 | 36.84% | 73.68% | 0.5550 | 3.211 |
| Latency p50 | 19 | 26.32% | 73.68% | 0.4987 | 2.947 |
| CPU + latency p90 | 19 | 26.32% | 68.42% | 0.5053 | 2.842 |
| Latency p50 + latency p90 | 19 | 26.32% | 52.63% | 0.4886 | 2.947 |
| Latency p90 | 19 | 21.05% | 52.63% | 0.4452 | 3.263 |

Hit@1 and Hit@3 count tied minimum ranks as hits. MRR uses the minimum rank assigned to the root-cause service.

## 5. Findings

1. CPU + latency p50 had the highest MRR among the compared methods (0.5689).
2. CPU + latency p50 + latency p90 had the highest Hit@3 (89.47%).
3. CPU alone had the highest Hit@1 (36.84%).
4. Combining more signals did not improve every metric. In this sample, the three-signal method traded lower Hit@1 and MRR for higher Hit@3.
5. The differences are based on 19 cases, so individual cases materially affect the reported percentages.

## 6. Interpretation

Temporal onset can provide useful localization evidence, but it does not by itself establish causal direction. An upstream fault, downstream symptom, shared dependency, or measurement artifact can produce similar timing patterns.

CPU + latency p50 is a promising balanced candidate for further validation. The three-signal method is a candidate when top-three coverage is the priority. Neither should be described as the final best method without additional validation.

## 7. Limitations

- Small sample: 19 loss-fault cases.
- Results are specific to the evaluated RCAEval subset and current detection thresholds.
- Ties are counted optimistically in Hit@1 and Hit@3; the MRR calculation also uses minimum rank for ties.
- The analysis is exploratory, and hypotheses were developed after inspecting results from this subset.
- Temporal precedence is not proof of causality.
- No independent dataset has yet been used to validate these findings.

## 8. Reproducibility artifacts

- Input details: `experiments/results/temporal_metric_family_loss_details.csv`
- Case results: `experiments/results/temporal_rank_fusion_common_services_cases.csv`
- Service rankings: `experiments/results/temporal_rank_fusion_common_services_details.csv`
- Summary: `experiments/results/temporal_rank_fusion_common_services_summary.csv`

## 9. Next research step

Freeze these results. Before claiming generalization, evaluate the selected method on a pre-specified set of cases not used to develop the fusion hypothesis, and report tie-aware metrics and results by fault type.
