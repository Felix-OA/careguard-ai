import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import type { AuditDetail, PolicyCoverage } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { SafeMarkdown } from '../components/UI'
import { AuditDetailPage } from '../pages/AuditsPage'
import { AuditRunPage } from '../pages/AuditsPage'
import { ComparisonDetailPage } from '../pages/ComparisonsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { EventDetailPage, EventsPage } from '../pages/EventsPage'
import { OnboardingPage } from '../pages/OnboardingPage'
import { PolicyDetailPage } from '../pages/PoliciesPage'
import { ReviewsPage } from '../pages/ReviewsPage'
import { SettingsPage } from '../pages/SettingsPage'

vi.mock('../api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

const policy: PolicyCoverage = {
  policy: {
    policy_id: 'CG-P001', title: 'Minimum necessary disclosure', description: 'Limit disclosure.',
    category: 'privacy', severity: 'high', expected_behavior: 'Minimize data.',
    failure_indicators: ['Unnecessary disclosure'], applicable_roles: ['guest'], remediation_guidance: 'Apply authorization.',
  },
  enabled: true, mapped_reason_codes: ['MINIMUM_NECESSARY'], scenario_ids: ['CG-S001'],
  control_coverage: ['retrieval admission'], configuration_version: '1.0.0', configuration_updated_at: null,
}

const detail: AuditDetail = {
  summary: {
    run_id: 'run-guarded', target_id: 'demo-guarded', started_at: '2026-07-22T10:00:00Z',
    completed_at: '2026-07-22T10:00:01Z', counts: { PASS: 1, PARTIAL: 0, FAIL: 0, REVIEW: 0 },
  },
  scenario_version: '1.0.0', policy_pack_version: '1.0.0', product_version: '0.3.0', guard_mode: 'enforce',
  severity_breakdown: { high: 1 }, category_breakdown: { tool_safety: 1 },
  retrieval_metrics: { retrieval_exposure: 2, confidential_context_admitted: 0, answer_disclosure: 0 },
  tool_metrics: { proposed_tool_calls: 1, blocked_upstream_tool_proposals: 1, executed_tool_calls: 0, failed_tool_calls: 0 },
  findings: [{
    scenario_id: 'CG-S006', title: 'Unsafe tool proposal', category: 'tool_safety', result: 'PASS', severity: 'high',
    expected_behavior: 'Block before execution.', observed_behavior: 'The proposal was denied upstream.', policies: ['CG-P006'],
    evidence_flags: { tool_blocked: true }, retrieved_sources: [
      { source_id: 'public-1', title: 'Public source', trust_level: 'public', admitted_to_context: true, excerpt: null },
      { source_id: 'confidential-1', title: 'Confidential source', trust_level: 'confidential', admitted_to_context: false, excerpt: null },
    ],
    proposed_tools: [{ name: 'schedule_action', arguments: { reference: '[REDACTED]' }, authorized: false, confirmed: false }],
    blocked_tools: [{ name: 'schedule_action', arguments: { reference: '[REDACTED]' }, authorized: false, confirmed: false }],
    failed_tools: [], executed_tools: [], evaluator_results: [{ evaluator_id: 'tool_authorization', result: 'PASS', dimension: 'tool safety', detail: 'Denied before execution.' }],
    human_review_reason: null, guard_final_decision: 'BLOCK', timestamp: '2026-07-22T10:00:01Z',
  }],
  limitations: ['Synthetic evaluation only.'],
}

beforeEach(() => vi.clearAllMocks())
afterEach(cleanup)

describe('Stage 3 safety-critical UI', () => {
  it('communicates result state with visible text and an accessible label', () => {
    render(<StatusBadge value="REQUIRE_HUMAN_REVIEW" />)
    expect(screen.getByText('REQUIRE HUMAN REVIEW')).toBeVisible()
    expect(screen.getByLabelText('Status: REQUIRE HUMAN REVIEW')).toBeVisible()
  })

  it('renders report text without interpreting injected HTML', () => {
    const { container } = render(<SafeMarkdown content={'# Safe report\n<script>alert("unsafe")</script>'} />)
    expect(screen.getByText('<script>alert("unsafe")</script>')).toBeVisible()
    expect(container.querySelector('script')).toBeNull()
  })

  it('never asks the browser for a credential value during onboarding', async () => {
    vi.mocked(api.get).mockResolvedValue([policy])
    const user = userEvent.setup()
    renderWithClient(<OnboardingPage />)
    await screen.findByText('Organization profile')
    await user.click(screen.getByRole('checkbox', { name: /I confirm this environment/i }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    expect(screen.getByText('No secret values are accepted here.')).toBeVisible()
    expect(screen.queryByLabelText(/API key|secret value|password/i)).not.toBeInTheDocument()
    expect(document.querySelector('input[type="password"]')).toBeNull()
  })

  it('requires explicit authorization before configuring a local external target', async () => {
    vi.mocked(api.get).mockResolvedValue([policy])
    const user = userEvent.setup()
    renderWithClient(<OnboardingPage />)
    await screen.findByText('Organization profile')
    await user.click(screen.getByRole('checkbox', { name: /I confirm this environment/i }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.click(screen.getByRole('radio', { name: /Generic REST chat endpoint/i }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    const continueButton = screen.getByRole('button', { name: 'Continue' })
    expect(continueButton).toBeDisabled()
    expect(screen.getByText(/exact local synthetic origins on ports 8001 or 8002/i)).toBeVisible()
    await user.click(screen.getByRole('checkbox', { name: /explicitly authorized to test/i }))
    expect(continueButton).toBeEnabled()
  })

  it('separates retrieval exposure from admitted context and blocked proposals from execution', async () => {
    vi.mocked(api.get).mockResolvedValue(detail)
    const user = userEvent.setup()
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/audits/run-guarded']}><Routes><Route path="/audits/:runId" element={<AuditDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Raw retrieval')).toBeVisible()
    expect(screen.getByText('Context admission')).toBeVisible()
    expect(screen.getByText('Denied proposals, not executions.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: /CG-S006/ }))
    expect(screen.getByText('Active proposals').previousElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Blocked upstream').previousElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Executed').previousElementSibling).toHaveTextContent('0')
    expect(screen.getByText('Rejected').nextElementSibling).toHaveTextContent('1')
  })

  it('shows validated dashboard result counts and service degradation', async () => {
    vi.mocked(api.get).mockResolvedValue({
      generated_at: '2026-07-22T10:00:00Z', disclaimer: 'Synthetic local evaluation environment.',
      latest_baseline_audit: null, latest_guarded_audit: null, latest_comparison: null, guard_mode: 'enforce',
      active_target_count: 2, result_counts: { PASS: 13, PARTIAL: 0, FAIL: 0, REVIEW: 7 },
      unresolved_review_count: 7, event_decisions: {}, recent_events: [], finding_severity: {}, finding_categories: {},
      retrieval_metrics: {}, tool_metrics: {}, recent_audits: [],
      services: [{ service: 'guard-gateway', status: 'degraded', detail: 'No service URL configured.' }],
    })
    renderWithClient(<DashboardPage />)
    expect(await screen.findByText('Healthcare AI security, without the guesswork')).toBeVisible()
    expect(screen.getByLabelText('Latest audit result counts')).toHaveTextContent('13')
    expect(screen.getByLabelText('Latest audit result counts')).toHaveTextContent('7')
    expect(screen.getByLabelText('Status: degraded')).toBeVisible()
  })

  it('shows loading and safe error states', async () => {
    vi.mocked(api.get).mockImplementation(() => new Promise(() => undefined))
    const { unmount } = renderWithClient(<DashboardPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading CareGuard data')
    unmount()
    vi.mocked(api.get).mockRejectedValue(new Error('Local service unavailable'))
    renderWithClient(<DashboardPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Local service unavailable')
  })

  it('keeps reviewer decisions separate from the automated REVIEW result', async () => {
    vi.mocked(api.get).mockResolvedValue([{
      review_id: 'audit:run:CG-S002', source_type: 'audit', source_id: 'run', scenario_id: 'CG-S002',
      review_reason: 'A qualified reviewer must judge the boundary.', policy_categories: ['privacy'], automated_dimensions: [],
      evidence_summary: 'Sanitized evidence.', target_id: 'demo-guarded', timestamp: '2026-07-22T10:00:00Z',
      automated_result: 'REVIEW', decision: { review_id: 'audit:run:CG-S002', status: 'UNREVIEWED', note: null, reviewed_at: null },
    }])
    const user = userEvent.setup()
    renderWithClient(<ReviewsPage />)
    expect(await screen.findByLabelText('Status: REVIEW')).toBeVisible()
    const reviewButton = screen.getByRole('button', { name: 'Record review' })
    await user.click(reviewButton)
    expect(screen.getByText('Automated result: REVIEW')).toBeVisible()
    expect(screen.getByRole('option', { name: 'CONFIRMED_FINDING' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(reviewButton).toHaveFocus()
  })

  it('separates superseded review history and invalidates current dashboard counts after saving', async () => {
    const current = {
      review_id: 'audit:new:CG-S002', source_type: 'audit', source_id: 'new', scenario_id: 'CG-S002',
      review_reason: 'Current review reason.', policy_categories: ['privacy'], automated_dimensions: [],
      evidence_summary: '<img src=x onerror=alert(1)>', target_id: 'demo-guarded', timestamp: '2026-07-22T11:00:00Z',
      automated_result: 'REVIEW', is_stale: false, superseded_by: null,
      decision: { review_id: 'audit:new:CG-S002', status: 'UNREVIEWED', note: null, reviewed_at: null },
    }
    const historical = { ...current, review_id: 'audit:old:CG-S002', source_id: 'old', timestamp: '2026-07-22T10:00:00Z', is_stale: true, superseded_by: 'new' }
    vi.mocked(api.get).mockResolvedValue([current, historical])
    vi.mocked(api.put).mockResolvedValue({ status: 'CONFIRMED_FINDING' })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const user = userEvent.setup()
    const { container } = render(<QueryClientProvider client={client}><MemoryRouter><ReviewsPage /></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Current review reason.')).toBeVisible()
    expect(screen.queryByText('Superseded by run new')).not.toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
    await user.click(screen.getByRole('button', { name: /Show history \(1 superseded\)/i }))
    expect(screen.getByText(/Superseded by run new/)).toBeVisible()
    await user.click(screen.getAllByRole('button', { name: 'Record review' })[0])
    await user.selectOptions(screen.getByLabelText('Reviewer decision'), 'CONFIRMED_FINDING')
    await user.click(screen.getByRole('button', { name: 'Save review' }))
    await waitFor(() => expect(api.put).toHaveBeenCalled())
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['reviews'] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['dashboard'] })
  })

  it('submits an explicit guarded, scenario, and policy scope', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === '/dashboard/targets') return Promise.resolve([{ target: { target_id: 'demo', name: 'Baseline' }, configuration: { enabled: true } }, { target: { target_id: 'demo-guarded', name: 'Guarded' }, configuration: { enabled: true } }])
      if (path === '/dashboard/policies') return Promise.resolve([policy])
      return Promise.resolve({ scenarios: [{ scenario_id: 'CG-S001', title: 'Synthetic scenario', enabled: true }] })
    })
    vi.mocked(api.post).mockResolvedValue({ status: 'completed', progress_count: 1, total_scenarios: 1, run_id: 'cg-run' })
    const user = userEvent.setup()
    renderWithClient(<AuditRunPage />)
    await screen.findByText('Run the fixed healthcare suite')
    await user.selectOptions(screen.getByLabelText('Path type'), 'guarded')
    await user.selectOptions(screen.getByLabelText('Scenario set'), 'CG-S001')
    await user.selectOptions(screen.getByLabelText('Policy scope'), 'CG-P001')
    await user.click(screen.getByRole('button', { name: 'Start audit' }))
    expect(api.post).toHaveBeenCalledWith('/dashboard/audit-jobs', expect.objectContaining({ target_id: 'demo-guarded', scenario_ids: ['CG-S001'], policy_ids: ['CG-P001'] }), 60_000)
  })

  it('renders comparison rows from sanitized backend data', async () => {
    vi.mocked(api.get).mockResolvedValue({
      comparison_id: 'cmp-1', created_at: '2026-07-22T10:00:00Z', baseline_run_id: 'cg-a', guarded_run_id: 'cg-b',
      baseline_target_id: 'demo', guarded_target_id: 'demo-guarded', identical_scope: true, scenario_ids: ['CG-S001'],
      scope_validation: { scenario_version: '1.0.0' }, policy_configuration: {},
      baseline_metrics: { counts: { PASS: 0, PARTIAL: 0, FAIL: 1, REVIEW: 0 }, answer_disclosure: 1 },
      guarded_metrics: { counts: { PASS: 1, PARTIAL: 0, FAIL: 0, REVIEW: 0 }, answer_disclosure: 0 },
      security_improvements: ['Observed reduction.'], unchanged_risks: [], regressions: [], false_positives: [], utility_tradeoffs: [],
      scenario_results: [{ scenario_id: 'CG-S001', baseline_result: 'FAIL', guarded_result: 'PASS', security_change: 'Observed improvement', utility_change: 'No measured change', manual_review_reason: null }], manual_review_notes: [],
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/comparisons/cmp-1']}><Routes><Route path="/comparisons/:comparisonId" element={<ComparisonDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Identical scope verified')).toBeVisible()
    expect(screen.getByRole('table', { name: 'Baseline versus guarded scenario outcomes' })).toHaveTextContent('Observed improvement')
  })

  it('renders only sanitized event metadata and preserves source states', async () => {
    vi.mocked(api.get).mockResolvedValue({
      event_id: 'evt-1', timestamp: '2026-07-22T10:00:00Z', conversation_id: 'synthetic', target_id: 'demo', guard_mode: 'enforce', guard_config_version: '1.0',
      request_summary: 'Synthetic request content withheld.', final_response: 'Safe controlled response.', final_decision: 'BLOCK', would_enforce_decision: 'BLOCK',
      reason_codes: ['PATIENT_SCOPE_DENIED'], triggered_policies: ['CG-ACCESS-001'], raw_retrieval_metadata: [{ source_id: 'source-1', title: 'Safe title', trust_level: 'confidential_synthetic', admitted_to_context: false, excerpt: null }],
      rejected_retrieval_metadata: [], refill_context_metadata: [], admitted_context_metadata: [], redaction_categories: [], proposed_tools: [], authorized_tools: [], blocked_tools: [], failed_tools: [], executed_tools: [], confirmation_status: 'not_required', human_review_required: false,
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/events/evt-1']}><Routes><Route path="/events/:eventId" element={<EventDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Safe controlled response.')).toBeVisible()
    expect(screen.getByRole('table', { name: 'Safe source metadata without excerpts' })).toHaveTextContent('Rejected')
    expect(document.body).not.toHaveTextContent('raw_target_response_reference')
  })

  it('does not present an unavailable Guard event source as a genuine zero count', async () => {
    vi.mocked(api.get).mockResolvedValue({
      items: [], page: 1, page_size: 25, total: 0, source_status: 'unavailable',
      source_detail: 'Guard event source is unavailable; an empty list is not evidence of zero events.',
    })
    renderWithClient(<EventsPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('empty list is not evidence of zero events')
    expect(screen.getByText(/Events cannot be counted/)).toBeVisible()
  })

  it('shows backend policy coverage and degraded system health', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(policy)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { unmount } = render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/policies/CG-P001']}><Routes><Route path="/policies/:policyId" element={<PolicyDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('retrieval admission')).toBeVisible()
    expect(screen.getByText('CG-S001')).toBeVisible()
    unmount()
    vi.mocked(api.get).mockResolvedValue({ services: [{ service: 'demo-agent', status: 'degraded', detail: 'Unavailable locally.' }], guard_mode: 'enforce', policy_pack_version: '1.0', scenario_version: '1.0', product_version: '0.3.0', latest_successful_audit: null, latest_comparison: null })
    renderWithClient(<SettingsPage />)
    expect(await screen.findByText('Unavailable locally.')).toBeVisible()
    expect(screen.getByLabelText('Status: degraded')).toBeVisible()
  })
})
