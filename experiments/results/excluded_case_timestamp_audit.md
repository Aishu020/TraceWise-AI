# RCAEval Excluded-Case Timestamp Audit

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
