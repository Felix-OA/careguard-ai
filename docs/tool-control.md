# Tool control

Guard controls four local simulations: `lookup_patient_record`, `find_appointment`, `request_clinician_escalation`, and `book_appointment`. Generation proposes tools but cannot execute them in enforce mode.

Patient record and appointment tools require an allowed role and matching verified synthetic patient scope; staff additionally needs authorized role metadata. Escalation is allowed for configured support cases and is recorded. Booking requires confirmation.

The confirmation workflow stores a process-local token bound to conversation ID and a hash of tool name/arguments. The token expires after the configured TTL and is consumed on success. Missing, expired, cross-conversation, or changed-action tokens cannot execute. A rejected action receives a newly summarized confirmation state where appropriate. Summaries redact controlled synthetic identifiers.

Events distinguish proposed, authorized, blocked, and executed tools plus confirmation status. This is a synthetic workflow demonstration, not production authentication or transaction security.
