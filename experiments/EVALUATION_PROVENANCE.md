# TraceWise AI — Evaluation Provenance

## Historical evaluator

`experiments/evaluate_heldout_99.py` reads
`data/rcaeval_heldout_98.csv`, despite its filename and its printed
"99 cases" label.

It writes files using the `heldout_98_*` prefix. Do not rerun this
script without first changing its output destinations and reviewing
its ranking implementation.

The historical summary reports:

- V1 Hit@1: 59.18%
- V1 Hit@3: 70.41%
- V2 Hit@1: 63.27%
- V2 Hit@3: 77.55%

These figures are historical and should not be substituted for the
frozen candidate results.

## Frozen candidate

`experiments/evaluate_locked_candidate.py` implements the protocol
in `experiments/tracewise_protocol.json`.

- Dataset: RCAEval
- Evaluated cases: 98 exploratory cases
- V2 scale floor: 1% of the absolute pre-fault median
- Metric score: absolute pre/post median change divided by effective scale
- Service aggregation: arithmetic mean across all available metric scores
- Ranking: competition ranking, with ties sharing the same rank
- Windows: injection minus 300 to minus 60 seconds, and injection
  plus 60 to plus 300 seconds, inclusive

Frozen candidate summary:

- V1 Hit@1: 58.16%
- V1 Hit@3: 70.41%
- V1 MRR: 0.686152
- V1 mean correct-service rank: 2.8061
- V2 Hit@1: 64.29%
- V2 Hit@3: 78.57%
- V2 MRR: 0.737366
- V2 mean correct-service rank: 2.4592

## Reproduction check

`experiments/reproduce_locked_candidate_98.py` was run using a
separate output prefix.

The reproduced case-results, service-rankings, and metric-evidence
CSV rows matched the corresponding frozen candidate files exactly.
The reproduced summary also matched.

This verifies reproducibility of the saved outputs from the current
implementation and inputs. It does not establish independent
validation, generalization to unseen datasets, or causal root-cause
identification.

## Data-quality exclusions

Two cases remain excluded pending authoritative timestamp verification
or suitable replacement data:

- `re1ob_currencyservice_loss_1`
- `re1ob_productcatalogservice_cpu_3`

Their timestamps have not been silently corrected.

## Research limitations

The 98-case set is exploratory and has informed development.
Independent validation is not yet available. Claims should be limited
to the evaluated RCAEval cases and the documented protocol.
