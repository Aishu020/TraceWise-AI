# TraceWise AI ? RE2-OB Evaluation Report

## 1. Scope

This report evaluates V1 and V2_1pct on 90 cases from the RCAEval RE2-OB subset. It is a cross-suite evaluation; it does not by itself prove causal identification or universal generalization.

## 2. Methods

Both methods use pre-fault and post-fault metric windows and aggregate metric anomaly scores at service level. V1 uses a 5% relative scale fallback when robust scale is effectively zero. V2_1pct uses a scale floor of 1% of the absolute pre-fault median. Refer to the frozen protocol and methodology documentation for the complete definitions.

## 3. Overall Results

| version | cases | Hit@1 (%) | Hit@3 (%) | MRR | Mean correct rank |
| --- | --- | --- | --- | --- | --- |
| V1 | 90 | 76.67 | 80.0 | 0.8189 | 2.0 |
| V2_1pct | 90 | 75.56 | 91.11 | 0.8317 | 1.8111 |

Hit@1 measures whether the correct root-cause service ranks first. Hit@3 measures whether it appears in the top three. MRR is mean reciprocal rank. Lower mean correct rank is better.

## 4. Paired Case Comparison

- Rank improved with V2: 18/90 (20.00%).
- Rank tied: 69/90 (76.67%).
- Rank worsened: 3/90 (3.33%).
- Mean rank improvement (V1 rank minus V2 rank): 0.1889 positions.

Most cases retained the same rank. Rank improvements were concentrated in delay and loss faults.

## 5. Results by Fault Type

| fault | version | cases | Hit@1 (%) | Hit@3 (%) | MRR | Mean correct rank |
| --- | --- | --- | --- | --- | --- | --- |
| cpu | V1 | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| cpu | V2_1pct | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| delay | V1 | 15 | 20.0 | 26.67 | 0.3657 | 4.8667 |
| delay | V2_1pct | 15 | 13.33 | 53.33 | 0.3494 | 4.6 |
| disk | V1 | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| disk | V2_1pct | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| loss | V1 | 15 | 40.0 | 53.33 | 0.5478 | 3.1333 |
| loss | V2_1pct | 15 | 40.0 | 93.33 | 0.6407 | 2.2667 |
| mem | V1 | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| mem | V2_1pct | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| socket | V1 | 15 | 100.0 | 100.0 | 1.0 | 1.0 |
| socket | V2_1pct | 15 | 100.0 | 100.0 | 1.0 | 1.0 |

## 6. Results by Root-Cause Service

| root_cause_service | version | cases | Hit@1 (%) | Hit@3 (%) | MRR | Mean correct rank |
| --- | --- | --- | --- | --- | --- | --- |
| checkoutservice | V1 | 18 | 66.67 | 66.67 | 0.7407 | 2.2222 |
| checkoutservice | V2_1pct | 18 | 66.67 | 94.44 | 0.7917 | 1.6111 |
| currencyservice | V1 | 18 | 72.22 | 83.33 | 0.8074 | 1.7222 |
| currencyservice | V2_1pct | 18 | 77.78 | 100.0 | 0.8611 | 1.3889 |
| emailservice | V1 | 18 | 77.78 | 77.78 | 0.8131 | 2.3333 |
| emailservice | V2_1pct | 18 | 77.78 | 83.33 | 0.8198 | 2.2222 |
| productcatalogservice | V1 | 18 | 66.67 | 72.22 | 0.7333 | 2.7222 |
| productcatalogservice | V2_1pct | 18 | 66.67 | 83.33 | 0.7631 | 2.3333 |
| recommendationservice | V1 | 18 | 100.0 | 100.0 | 1.0 | 1.0 |
| recommendationservice | V2_1pct | 18 | 88.89 | 94.44 | 0.9228 | 1.5 |

## 7. Interpretation

V2 improves overall Hit@3, MRR, and mean correct-service rank compared with V1, while overall Hit@1 is slightly lower. The effect varies by fault type and service. Delay faults remain challenging, and recommendationservice results decline on some measures.

These metrics assess rankings against dataset-provided labels. They do not independently establish the causal mechanism or production readiness.

## 8. Limitations

1. The evaluation contains 90 cases from one dataset subset.
2. Each fault group contains 15 cases and each service group contains 18 cases.
3. Subgroup estimates are small and should not be generalized without further testing.
4. Confidence intervals and statistical significance tests are not included.
5. Dataset labels and ranking metrics do not prove causality.
6. The independent-validation status must remain as recorded in `experiments/tracewise_protocol.json`. This report does not change it.

## 9. Reproducibility

Inputs:
- `experiments/results/locked_candidate_re2ob_90_case_results.csv`
- `experiments/results/locked_candidate_re2ob_90_paired_comparison.csv`

Companion artifacts include rankings, metric evidence, summary CSVs, the frozen protocol, and evaluation provenance documentation.

## 10. Conclusion

On the evaluated RE2-OB subset, V2 improves top-three ranking performance and reciprocal-rank quality, but not Hit@1. Gains are concentrated in delay and loss cases, with a small number of ranking regressions. Further evaluation on additional held-out subsets and stronger baselines is required before making broader claims.

## Statistical Uncertainty Analysis

A paired percentile bootstrap analysis with 10,000 resamples and random seed 20261020 was conducted on the 90 RE2-OB cases.

| Measure (V2 minus V1, except rank improvement) | Estimate | 95% bootstrap confidence interval |
| --- | ---: | ---: |
| Hit@1 difference | -1.11 percentage points | [-5.56, 2.22] percentage points |
| Hit@3 difference | +11.11 percentage points | [4.44, 18.89] percentage points |
| Mean reciprocal rank difference | +0.0128 | [-0.0172, 0.0380] |
| Mean rank improvement (V1 rank minus V2 rank) | +0.1889 positions | [-0.0667, 0.4000] |

The Hit@3 interval excludes zero, indicating a positive difference under this bootstrap procedure. The intervals for Hit@1, mean reciprocal rank, and mean rank improvement include zero; their observed differences are therefore uncertain under this analysis.

For Hit@1, V2 changed one case from incorrect to correct at rank 1 and changed two cases from correct to incorrect. For Hit@3, V2 brought 11 cases into the top three and moved one case out of the top three.

These intervals quantify sampling uncertainty under resampling of the observed cases. They do not establish causality, eliminate dataset-specific effects, or substitute for a pre-specified inferential analysis. The findings should be interpreted within the scope of this 90-case subset.
