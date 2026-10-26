# TraceWise AI — Research Evaluation Report

## 1. Project Overview

TraceWise AI investigates whether service-level metric changes can help rank
the likely root-cause service during a software failure.

The current research baseline uses robust statistical comparisons between
pre-injection and post-injection telemetry windows. It is intended as a
lightweight, interpretable baseline for root-cause localization.

## 2. Research Question

Does applying a relative scale floor to robust metric normalization improve
root-cause service ranking compared with the V1 normalization method?

## 3. Dataset and Evaluation Scope

- Dataset: RCAEval telemetry cases
- Cases evaluated: 98
- Original manifest: 125 cases
- Tuning set: 25 cases
- Exploratory evaluation set: 98 cases
- Excluded cases: 2 cases with timestamp inconsistencies
- Evaluation unit: software failure case
- Target: rank the known root-cause service

The 98-case set is disjoint from the 25-case tuning set. However, it has
already been used for exploratory method comparisons and is not an untouched
independent test set.

## 4. Methodology

### 4.1 Time windows

For an injection timestamp t:

- Pre-fault window: t - 300 through t - 60 seconds, inclusive
- Post-fault window: t + 60 through t + 300 seconds, inclusive
- The 60-second interval immediately surrounding injection is excluded.

### 4.2 Robust metric normalization

For each metric, calculate the pre- and post-window medians.

The robust scale is:

    robust_scale = 1.4826 * MAD(pre_fault_metric)

V1 uses the following effective scale:

    max(robust_scale, 0.05 * abs(pre_median), 1e-9)

V2 uses a 1% relative scale floor:

    max(robust_scale, 0.01 * abs(pre_median), 1e-9)

The metric anomaly score is:

    abs(post_median - pre_median) / effective_scale

### 4.3 Service aggregation

Available metric scores are grouped by service. The candidate method
calculates the arithmetic mean of all available metric scores for each
service. Services are ranked in descending score order.

This measures the magnitude of observed changes. It does not establish
that a service caused the failure.

### 4.4 Evaluation metrics

- Hit@1: proportion of cases where the known root-cause service ranks first.
- Hit@3: proportion of cases where it ranks within the top three.
- Mean Reciprocal Rank (MRR): mean reciprocal of the root-cause rank.
- Mean correct-service rank: average rank of the known root-cause service.

Competition ranking is used. Tied services receive the same rank; a root
cause tied at rank 1 counts toward Hit@1.

## 5. Results

The locked-candidate evaluator processed all 98 cases successfully.

| Metric | V1 | V2 (1% floor) |
|---|---:|---:|
| Cases | 98 | 98 |
| Hit@1 | 58.16% | 64.29% |
| Hit@3 | 70.41% | 78.57% |
| MRR | 0.6862 | 0.7374 |
| Mean correct-service rank | 2.8061 | 2.4592 |

V2 improved Hit@1 by 6.12 percentage points and Hit@3 by 8.16 percentage
points relative to V1 on this evaluation set.

These results support further investigation of the normalization choice.
They do not establish statistical significance, generalization to other
datasets, or causal identification.

## 6. Interpretation

The relative scale floor reduces the influence of extremely small baseline
scales, which can otherwise produce disproportionately large normalized
scores. In these experiments, V2 ranked the known root-cause service more
successfully than V1.

Metric magnitude can still prioritize correlated or downstream symptoms
instead of the true initiating service. The ranking should therefore be
treated as diagnostic evidence, not proof of causality.

## 7. Limitations

1. The 98 cases have already informed exploratory comparisons; they are not
   an untouched final test set.
2. The current method relies on aggregate telemetry changes and does not
   model service-call dependencies explicitly.
3. Results may vary by fault type.
4. Ties can affect top-k metrics.
5. Only the current dataset and evaluation scope have been assessed here.
6. No confidence intervals or statistical significance tests are reported.
7. The current results do not demonstrate superiority over established
   state-of-the-art root-cause localization systems.

## 8. Reproducibility Artifacts

The project includes the evaluation protocol and candidate evaluator:

- experiments/tracewise_protocol.json
- experiments/results/tracewise_evaluation_protocol.md
- experiments/evaluate_locked_candidate.py
- experiments/results/locked_candidate_98_case_results.csv
- experiments/results/locked_candidate_98_rankings.csv
- experiments/results/locked_candidate_98_metric_evidence.csv
- experiments/results/locked_candidate_98_summary.csv

Run the evaluator from the project root:

    python experiments/evaluate_locked_candidate.py

The evaluator writes results with the locked_candidate_98 prefix and does
not overwrite the older evaluation files.

## 9. Next Research Steps

1. Audit the implementation and compare its metric-level scores against
   previously saved evidence.
2. Add fault-type-specific error analysis, particularly for delay and loss.
3. Compare against a clearly documented simple baseline.
4. Freeze the method and evaluation protocol before obtaining an independent
   evaluation set.
5. Add uncertainty analysis and document all exclusions.
6. Connect the verified ranking pipeline to the UI only after checking the
   interface contract and testing with real case inputs.

## 10. Conclusion

On 98 exploratory RCAEval cases, V2 with a 1% relative scale floor achieved
64.29% Hit@1, 78.57% Hit@3, and an MRR of 0.7374. These findings are
promising for a lightweight baseline but require independent validation,
additional fault-specific analysis, and comparison with other methods before
strong research claims can be made.
