# Dashboard guide

The Stage 3 dashboard is a local React 19/TypeScript/Vite application served at `http://127.0.0.1:3000`. React Router owns page navigation, TanStack Query owns remote state, Recharts renders the category view with a table alternative, and one central API client applies timeouts and sanitized error handling. nginx proxies `/api/` to the Audit API; the browser never calls Guard or the demo agent directly.

## Routes

| Route | Purpose |
|---|---|
| `/` | Validated security summary, counts, review load, events, metrics, activity, and health |
| `/onboarding` | Eight-step local company and target setup |
| `/targets`, `/targets/:id` | Target inventory, capability, credential status, test, enable/disable, and delete |
| `/audits`, `/audits/new`, `/audits/:id` | Filtered history, scoped run, evidence, evaluators, retrieval/context, and tool states |
| `/comparisons`, `/comparisons/:id` | Backend-validated baseline/guarded comparison and scenario table |
| `/events`, `/events/:id` | Bounded sanitized Guard event list/detail |
| `/reviews` | Demonstration human-review decisions kept separate from automation |
| `/policies`, `/policies/:id` | Existing policy catalogue, mappings, coverage, and local enablement |
| `/reports`, `/reports/:type/:id` | Safe Markdown preview and Markdown/JSON export |
| `/demo` | Approved baseline-versus-guarded fictional prompts |
| `/settings` | Service health, versions, and explicit non-goals |

## Typical workflow

Start Compose, complete onboarding, test the synthetic target, run `demo` baseline and `demo-guarded` audits, create a comparison from equivalent runs, inspect REVIEW items, then inspect event and report views. Counts and claims come from evidence-validated backend summaries. Current guarded metrics use a comparison only when it matches the latest baseline and guarded run exactly; stale comparisons and incomplete/corrupt audit records cannot become current posture. A blocked proposal is never counted as executed, raw retrieval is displayed separately from admitted context, and redaction is not counted as user-visible disclosure.

The event view distinguishes a genuinely empty event store from an unavailable Guard event source. The review view excludes superseded items from current counts while retaining them as labelled history. Safe report previews/exports are summaries, not protected evidence downloads.

All pages include semantic headings and labels, visible focus, keyboard navigation, status text as well as color, reduced-motion handling, responsive layouts, safe error/empty/loading states, table captions, and a table alternative for the chart. This is not an accessibility certification; verify with the target assistive-technology matrix before productization.

The dashboard is a single-operator local demonstration. It has no authentication, multi-tenancy, scheduling, formal review authority, production policy governance, or clinical/compliance status. Stage 4 agentic auditing is not present.
