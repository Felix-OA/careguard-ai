# Tool control

Guard controls four local simulations: `lookup_patient_record`, `find_appointment`, `request_clinician_escalation`, and `book_appointment`. Generation may propose tools but cannot execute them in enforce mode.

Tool states are deliberately distinct:

| State | Meaning |
|---|---|
| proposed | Raw target intent retained in the protected event. |
| authorized | Role, server-derived scope, tool, and arguments passed policy. |
| confirmation required | An authorized sensitive action is awaiting a bound token. |
| confirmed | The token matched conversation, action, arguments, and patient scope and was consumed. |
| executed | The local simulated tool completed. |
| blocked | An upstream proposal was denied and is not an active public proposal. |
| failed | An authorized execution raised an error; output is withheld and human review is required. |

Patient record and appointment tools require an allowed role and matching verified synthetic patient scope; authorized staff metadata is additionally required for staff access. Emergency escalation is policy-generated and only the approved escalation proposal is exposed. Booking and non-emergency clinician escalation require confirmation.

Confirmation tokens are random, short-lived, process-local, one-time values bound to conversation ID, tool name, canonical arguments, and patient-scope metadata. Missing, expired, replayed, cross-conversation, changed-action, changed-argument, or changed-scope tokens cannot execute. A failed verification consumes suspect state where appropriate. Reload clears all outstanding state. Safe summaries and public tool metadata redact controlled arguments.

The public Guard response exposes only authorized active proposals in enforce mode plus separate blocked and failed lists with redacted arguments. The protected local event retains raw proposal details for audit. Monitor mode preserves raw target proposals/executions and separately records what Guard would authorize or block.

This is a bounded synthetic state-machine demonstration, not production authentication, authorization, transaction integrity, or a durable workflow engine.
