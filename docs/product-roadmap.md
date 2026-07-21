# Product roadmap

## Stage 1 — Audit foundation

Implemented: deterministic catalogs and evaluators, normalized connectors, local synthetic target, evidence, reports, API, CLI, and container workflow.

## Future Audit work

A controlled multi-turn interface is defined in `careguard.audit.agentic`. A future GOAT-inspired runner may combine an attacker-agent adapter, target connector, evaluator, approved scenario objectives, conversation evidence, strict turn/cost limits, and explicit localhost or authorized-target enforcement. Stage 1 does not implement autonomous attack generation or operational jailbreak content.

## Guard module

Planned request/response policy enforcement, retrieval trust filtering, structured authorization, tool confirmation gates, redaction, and human-review routing. Guard decisions should emit evidence compatible with the Audit schema.

## Regression Monitor module

Planned scheduled replay of approved scenarios, baseline comparison, policy drift alerts, severity-aware thresholds, and traceable change review. It should remain opt-in and operate only on authorized targets.

