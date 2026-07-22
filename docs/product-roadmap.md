# Product roadmap

## Stage 1 — Audit foundation

Implemented: deterministic catalogs/evaluators, connectors, synthetic target, JSONL evidence, reports, API, CLI, and containers.

## Stage 2 — Guard

Implemented: separate runtime gateway, monitor/enforce modes, request rules, deep demo context admission/refill, response redaction/withholding, emergency policy response, tool authorization, bounded confirmation, structured events, guarded audits, and before/after comparisons.

## Stage 3 — Dashboard and company onboarding

Implemented: responsive local dashboard, server-persisted company/target onboarding, strict local-target authorization/SSRF checks, declared integration capability, secret-reference status, harmless bounded connection tests, recoverable local audit-job records, evidence-validated audit/comparison views, sanitized Guard events with degradation state, version-bound policy scope, separate reviewer decisions with superseded history, protected-content-free report preview/export, health, and a guided synthetic demo. Backend APIs own summaries, validation, comparisons, review state, and report/event sanitization; the UI contains no security decision logic.

Not implemented: scheduled replay/regression monitoring, production identity/access control, multi-tenancy, formal database migrations, tamper-evident storage, secret-vault integration, signed policy governance, billing, hosting, or formal clinical/compliance review.

The pre-Stage-3 hardening pass establishes trustworthy fixed-suite evidence and a bounded local runtime. It does not make Stages 1–2 production-ready. See [pre-Stage-3 validation](pre-stage-3-validation.md).

## Stage 4 — Controlled multi-turn agentic audit

Implemented: a separate versioned healthcare objective pack, 10 safe strategy categories and templates, deterministic seeded attacker, optional loopback-only model selector and secondary judge, bounded synchronous orchestration, explicit stops/cancellation, target-output injection defenses, sanitized transactional trajectory evidence, agentic reports/API/CLI/dashboard, REVIEW queue integration, and scope-validated baseline-versus-Guard comparisons.

This is a GOAT-inspired high-level architecture, not an official GOAT implementation or research reproduction. It does not add autonomous attack infrastructure, public scanning, arbitrary prompts, tools, shell/filesystem/browser access, production identity, worker isolation, scheduling, hosted execution, or a claim of production readiness.
