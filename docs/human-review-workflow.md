# Human-review workflow

The REVIEW queue combines audit scenarios with explicit manual-review reasons and Guard events that require human judgment. It is a demonstration workflow, not formal clinical review.

Each item retains source type/ID, scenario ID when applicable, policy categories, automated evaluator dimensions, sanitized evidence, target, timestamp, original automated result, and a distinct reviewer decision. Supported decisions are `UNREVIEWED`, `CONFIRMED_SAFE`, `CONFIRMED_FINDING`, and `NEEDS_MORE_CONTEXT`, with an optional bounded note and review timestamp.

Saving a decision never changes the evidence record or automated result. In particular, the seven reviewed guarded REVIEW outcomes—authority/access, indirect influence, calibration, medication boundary, emergency handling, source conflict, and consequential record change—remain visible even after a local reviewer decision.

When the same target/scenario is audited again, the newest audit review item remains current and earlier items are marked historical with the superseding run ID. Historical items stay inspectable but do not inflate the dashboard's current unresolved count. Reviewer notes are bounded and secret-shaped values are sanitized. Guard-event review records use the same supersession rule when an audit scenario ID is available.

This store has no reviewer identity, authentication, authorization, signatures, assignment, dual control, escalation SLA, legal hold, or immutable audit history. Production review requires qualified organizational governance and must not be inferred from this local status field.
