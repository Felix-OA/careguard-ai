# Product roadmap

## Stage 1 — Audit foundation

Implemented: deterministic catalogs/evaluators, connectors, synthetic target, JSONL evidence, reports, API, CLI, and containers.

## Stage 2 — Guard

Implemented: separate runtime gateway, monitor/enforce modes, request rules, deep demo context admission/refill, response redaction/withholding, emergency policy response, tool authorization, bounded confirmation, structured events, guarded audits, and before/after comparisons.

## Stage 3 — Regression Monitor and dashboard

Planned: approved scheduled replay, baseline drift, severity thresholds, traceable review, event/evidence dashboards, and guarded-policy change history. This repository does not yet implement the dashboard or production scheduling.

## Future controlled agentic audit

The interface in `careguard.audit.agentic` remains a non-operational contract for approved objectives, strict turn/cost limits, conversation evidence, and authorized localhost targets. Stage 2 does not add autonomous attack generation.
