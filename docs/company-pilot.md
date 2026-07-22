# Company pilot framework

CareGuard AI’s public repository is a local synthetic demonstration. This document describes how its ideas could be evaluated in an authorized company test environment. It is a product implementation framework, not legal, regulatory, clinical, privacy, or compliance advice.

## Suitable organizations

Potential pilot participants include digital-health companies, patient-support platforms, healthcare contact-center vendors, clinical-administration software teams, benefits-navigation products, and AI infrastructure providers that operate a healthcare-oriented test application and can provide security, product, privacy, and domain reviewers.

## Eligible AI use cases

Suitable non-production use cases include patient-support chat, appointment and referral assistance, benefits or coverage navigation, medical-information retrieval, care-navigation support, clinician or operations copilots, and workflow agents with tightly scoped test tools.

The pilot should exclude live clinical decision-making, real patient records, production credentials, emergency-service substitution, and any target without explicit authorization.

## Required integration information

A discovery package normally covers:

- Application and model architecture
- Test endpoints and authentication method
- Retrieval pipeline and document stores
- Source metadata and trust classification
- Identity, role, tenant, and patient-scope derivation
- Available tools and consequential actions
- Confirmation and approval workflow
- Existing policies, logging, escalation, and incident processes
- Expected safe behavior and known utility requirements
- Release process and representative regression environment

Secrets should remain in the company’s approved server-side secret system. They should not be placed in browser forms, reports, screenshots, or repository configuration.

## Proxy-only versus deep integration

| Integration | Visibility | Suitable controls | Important limitation |
|---|---|---|---|
| Proxy-only | Incoming request, final response, and surfaced tool metadata | Request/response policy, redaction, escalation, surfaced tool checks | Cannot prove or filter hidden retrieval/context/tool behavior |
| Deep retrieval | Retrieval candidates before generation plus admitted context | Source classification, context exclusion/refill, grounding evidence | Requires an authenticated, authorized pre-context integration point |
| Tool control | Proposal, authorization, confirmation, and execution boundaries | Role/scope checks, confirmation binding, execution evidence | Requires the target to expose authoritative tool state |

Capability labels are declarations to validate during discovery, not proof that an integration provides the claimed visibility. See the [connector guide](connector-guide.md).

## Discovery process

1. Define the authorized test scope and responsible stakeholders.
2. Map assets, actors, trust boundaries, threats, and non-goals.
3. Document identity, patient scope, source trust, tools, and escalation requirements.
4. Select proxy-only, deep-retrieval, and/or tool-control integration points.
5. Agree on synthetic fixtures, success criteria, review ownership, and data retention.
6. Establish baseline evidence before proposing Guard configuration changes.

## Test-environment requirements

The environment should be isolated from production, contain only fictional or formally approved test data, enforce outbound-network policy, use non-production credentials, provide deterministic fixtures where possible, and support repeatable deployment. Logs and reports should have documented access, retention, and deletion controls.

## Policy and evaluation customization

The pilot maps CareGuard’s internal non-normative policy IDs to the company’s application requirements. Customization may include role and patient scope, source classes, sensitive identifiers, supported medical-language boundaries, emergency wording, tool permissions, confirmation requirements, scenario inputs, agentic objectives, safe indicators, review rules, and utility expectations.

Policy changes should be versioned and reviewed. See [policy configuration](policy-configuration.md), [policy coverage](policy-coverage.md), and [scenario design](scenario-design.md).

## Implementation phases

### Phase A: Scope and baseline

Deliver a threat model, connector plan, synthetic fixture plan, and fixed baseline assessment.

### Phase B: Integration and evidence

Implement the authorized adapter, normalize evidence, verify privacy boundaries, and establish reproducible reports.

### Phase C: Bounded Guard pilot

Configure monitor mode first where appropriate, review observed decisions, then evaluate enforce behavior in the isolated environment. Monitor results must not be described as protection.

### Phase D: Controlled agentic evaluation

Customize a small approved objective/strategy pack, define limits and review ownership, and compare matching baseline/guarded campaigns without converting REVIEW into PASS.

### Phase E: Tuning and handoff

Investigate false positives and false negatives, repeat the fixed release suite, document residual risks, and hand off configuration, reports, tests, and an operating guide.

## Client responsibilities

The participating organization remains responsible for authorization, environment isolation, identity truth, data classification, clinical/domain review, privacy/legal review, secret management, production architecture, incident response, and decisions about deployment. CareGuard evidence should inform—not replace—those processes.

## Data boundaries

- Prefer synthetic data throughout the pilot.
- Do not copy production prompts, patient records, credentials, headers, or unrestricted logs into CareGuard evidence.
- Define which source metadata and tool fields may be retained.
- Keep protected evidence separate from public or portfolio reporting.
- Review every export and screenshot before sharing.

## Example deliverables

- Application-specific threat model and trust-boundary diagram
- Connector and capability assessment
- Versioned policy/scenario/objective packs
- Baseline and guarded evidence summaries
- Sanitized comparison and remediation report
- Human-review rubric and unresolved-review register
- Guard configuration for the authorized test environment
- Regression test plan and operator guide
- Residual-risk and productionization recommendations

## Ongoing regression monitoring

The current public repository does not implement scheduling. A company implementation could run approved fixed suites at release gates, compare only version-matched evidence, alert on regressions or new REVIEW outcomes, retain signed configuration history, and route findings into the organization’s existing engineering and risk workflows. Durable workers, authentication, tenant isolation, tamper-evident storage, and production observability would require separate engineering and validation.

