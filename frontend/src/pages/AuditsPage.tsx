import { FormEvent, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { AuditDetail, AuditJob, AuditSummary, PolicyCoverage, Target } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader } from '../components/UI'

export function AuditsPage() {
  const [targetFilter, setTargetFilter] = useState('all')
  const [resultFilter, setResultFilter] = useState('all')
  const [pathFilter, setPathFilter] = useState('all')
  const [dateFilter, setDateFilter] = useState('')
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest')
  const [page, setPage] = useState(1)
  const query = useQuery({ queryKey: ['audits'], queryFn: () => api.get<AuditSummary[]>('/dashboard/audits') })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const filtered = query.data!
    .filter(item => targetFilter === 'all' || item.target_id === targetFilter)
    .filter(item => resultFilter === 'all' || (item.counts[resultFilter as keyof typeof item.counts] ?? 0) > 0)
    .filter(item => pathFilter === 'all' || (pathFilter === 'guarded' ? item.target_id === 'demo-guarded' : item.target_id !== 'demo-guarded'))
    .filter(item => !dateFilter || item.completed_at.slice(0, 10) === dateFilter)
    .sort((a, b) => (sortOrder === 'newest' ? -1 : 1) * a.completed_at.localeCompare(b.completed_at))
  const pageSize = 10
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize))
  const activePage = Math.min(page, pageCount)
  const items = filtered.slice((activePage - 1) * pageSize, activePage * pageSize)
  const resetPage = () => setPage(1)
  return <><PageHeader eyebrow="Fixed synthetic suite" title="Audit history" description="Baseline and guarded runs retain distinct automated PASS, PARTIAL, FAIL, and REVIEW outcomes." action={<Link className="button button-primary" to="/audits/new">Run audit</Link>} />
    <div className="filters"><label>Target<select value={targetFilter} onChange={e => { setTargetFilter(e.target.value); resetPage() }}><option value="all">All targets</option>{[...new Set(query.data!.map(item => item.target_id))].map(id => <option key={id}>{id}</option>)}</select></label><label>Contains result<select value={resultFilter} onChange={e => { setResultFilter(e.target.value); resetPage() }}><option value="all">Any result</option><option>PASS</option><option>PARTIAL</option><option>FAIL</option><option>REVIEW</option></select></label><label>Path<select value={pathFilter} onChange={e => { setPathFilter(e.target.value); resetPage() }}><option value="all">Baseline and guarded</option><option value="baseline">Baseline</option><option value="guarded">Guarded</option></select></label><label>Completion date<input type="date" value={dateFilter} onChange={e => { setDateFilter(e.target.value); resetPage() }} /></label><label>Sort<select value={sortOrder} onChange={e => { setSortOrder(e.target.value as 'newest' | 'oldest'); resetPage() }}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label></div>
    {items.length ? <Card><div className="table-wrap"><table><caption>Completed audits</caption><thead><tr><th>Run</th><th>Target</th><th>Completed</th><th>PASS</th><th>PARTIAL</th><th>FAIL</th><th>REVIEW</th></tr></thead><tbody>{items.map(audit => <tr key={audit.run_id}><td><Link to={`/audits/${audit.run_id}`}>{audit.run_id}</Link></td><td><StatusBadge value={audit.target_id === 'demo-guarded' ? 'Guarded' : 'Baseline'} /></td><td>{new Date(audit.completed_at).toLocaleString()}</td><td>{audit.counts.PASS}</td><td>{audit.counts.PARTIAL}</td><td>{audit.counts.FAIL}</td><td>{audit.counts.REVIEW}</td></tr>)}</tbody></table></div><div className="pagination"><button className="button" disabled={activePage === 1} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {activePage} of {pageCount} · {filtered.length} audits</span><button className="button" disabled={activePage === pageCount} onClick={() => setPage(value => value + 1)}>Next</button></div></Card> : <EmptyState title="No matching audits">Change the filters or start a new run.</EmptyState>}
  </>
}

export function AuditRunPage() {
  const queryClient = useQueryClient()
  const targets = useQuery({ queryKey: ['targets'], queryFn: () => api.get<Target[]>('/dashboard/targets') })
  const policies = useQuery({ queryKey: ['policies'], queryFn: () => api.get<PolicyCoverage[]>('/dashboard/policies') })
  const scenarios = useQuery({ queryKey: ['scenarios'], queryFn: () => api.get<{ scenarios: { scenario_id: string; title: string; enabled: boolean }[] }>('/scenarios') })
  const [targetId, setTargetId] = useState('demo')
  const [scenarioId, setScenarioId] = useState('all')
  const [policyId, setPolicyId] = useState('all')
  const [label, setLabel] = useState('Stage 3 dashboard run')
  const [notes, setNotes] = useState('Synthetic local evaluation only.')
  const run = useMutation({ mutationFn: () => api.post<AuditJob>('/dashboard/audit-jobs', { target_id: targetId, scenario_ids: scenarioId === 'all' ? null : [scenarioId], policy_ids: policyId === 'all' ? null : [policyId], run_label: label, notes }, 60_000), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['audits'] }); queryClient.invalidateQueries({ queryKey: ['dashboard'] }); queryClient.invalidateQueries({ queryKey: ['reviews'] }); queryClient.invalidateQueries({ queryKey: ['reports'] }); queryClient.invalidateQueries({ queryKey: ['targets'] }) } })
  if (targets.isLoading || policies.isLoading || scenarios.isLoading) return <Loading />
  if (targets.error || policies.error || scenarios.error) return <ErrorState error={(targets.error || policies.error || scenarios.error)!} />
  const submit = (event: FormEvent) => { event.preventDefault(); run.mutate() }
  return <><PageHeader eyebrow="New assessment" title="Run the fixed healthcare suite" description="Select an authorized target. Scenario progress is reported only when the local runner completes it." /><Card className="form-card"><form onSubmit={submit}><div className="form-grid"><label>Target<select value={targetId} onChange={e => setTargetId(e.target.value)}>{targets.data!.filter(item => item.configuration.enabled).map(item => <option value={item.target.target_id} key={item.target.target_id}>{item.target.name}</option>)}</select></label><label>Path type<select value={targetId === 'demo-guarded' ? 'guarded' : 'baseline'} onChange={e => setTargetId(e.target.value === 'guarded' ? 'demo-guarded' : 'demo')}><option value="baseline">Baseline</option><option value="guarded">Guarded</option></select></label><label>Scenario set<select value={scenarioId} onChange={e => setScenarioId(e.target.value)}><option value="all">All enabled scenarios</option>{scenarios.data!.scenarios.filter(item => item.enabled).map(item => <option value={item.scenario_id} key={item.scenario_id}>{item.scenario_id} · {item.title}</option>)}</select></label><label>Policy scope<select value={policyId} onChange={e => setPolicyId(e.target.value)}><option value="all">All enabled policies</option>{policies.data!.filter(item => item.enabled).map(item => <option value={item.policy.policy_id} key={item.policy.policy_id}>{item.policy.policy_id} · {item.policy.title}</option>)}</select></label><label className="span-2">Run label<input value={label} maxLength={120} onChange={e => setLabel(e.target.value)} /></label><label className="span-2">Safe notes<textarea value={notes} maxLength={500} onChange={e => setNotes(e.target.value)} /></label></div><div className="alert alert-info"><strong>Scope</strong><span>{scenarioId === 'all' ? 'All enabled versioned scenarios' : scenarioId} with {policyId === 'all' ? 'all enabled policy coverage' : policyId}. No public or paid target calls.</span></div><button className="button button-primary" disabled={run.isPending}>{run.isPending ? 'Running local suite…' : 'Start audit'}</button></form></Card>{run.error && <ErrorState error={run.error} />}{run.data && <Card className="job-complete"><StatusBadge value={run.data.status} /><div><h2>{run.data.progress_count} of {run.data.total_scenarios} scenarios completed</h2><p>{run.data.error ?? 'Evidence and summary were stored server-side.'}</p></div>{run.data.run_id && <Link className="button button-primary" to={`/audits/${run.data.run_id}`}>Open audit</Link>}</Card>}</>
}

function ToolStates({ finding }: { finding: AuditDetail['findings'][number] }) { return <div className="tool-state-grid"><div><strong>{finding.proposed_tools.length}</strong><span>Active proposals</span></div><div><strong>{finding.blocked_tools.length}</strong><span>Blocked upstream</span></div><div><strong>{finding.failed_tools.length}</strong><span>Failed</span></div><div><strong>{finding.executed_tools.length}</strong><span>Executed</span></div></div> }

export function AuditDetailPage() {
  const { runId = '' } = useParams()
  const query = useQuery({ queryKey: ['audit-detail', runId], queryFn: () => api.get<AuditDetail>(`/dashboard/audits/${runId}`) })
  const [expanded, setExpanded] = useState<string | null>(null)
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  return <><PageHeader eyebrow={`${data.summary.target_id} · ${data.guard_mode ?? 'baseline'}`} title="Audit detail" description={`${data.summary.run_id} · scenario ${data.scenario_version} · policy ${data.policy_pack_version}`} action={<Link className="button" to={`/reports/audit/${runId}`}>Preview report</Link>} /><div className="results-strip">{(['PASS','PARTIAL','FAIL','REVIEW'] as const).map(status => <div key={status}><StatusBadge value={status} /><strong>{data.summary.counts[status]}</strong></div>)}</div>
    <div className="metrics-grid"><Card><p className="eyebrow">Raw retrieval</p><strong className="big-number">{data.retrieval_metrics.retrieval_exposure}</strong><p>Confidential sources retrieved before admission.</p></Card><Card><p className="eyebrow">Context admission</p><strong className="big-number">{data.retrieval_metrics.confidential_context_admitted}</strong><p>Confidential sources admitted after authorization.</p></Card><Card><p className="eyebrow">Answer disclosure</p><strong className="big-number">{data.retrieval_metrics.answer_disclosure}</strong><p>Evaluator disclosure findings.</p></Card><Card><p className="eyebrow">Blocked tools</p><strong className="big-number">{data.tool_metrics.blocked_upstream_tool_proposals}</strong><p>Denied proposals, not executions.</p></Card></div>
    <Card><div className="card-heading"><div><p className="eyebrow">Scenario evidence</p><h2>All scenario results</h2></div><span className="muted">Select a row for sanitized detail</span></div><div className="table-wrap"><table><caption>Scenario results and review requirements</caption><thead><tr><th>Scenario</th><th>Category</th><th>Result</th><th>Severity</th><th>Policies</th><th>Review reason</th></tr></thead><tbody>{data.findings.map(finding => <tr key={finding.scenario_id} className="clickable-row" onClick={() => setExpanded(expanded === finding.scenario_id ? null : finding.scenario_id)}><td><button className="text-button" aria-expanded={expanded === finding.scenario_id}>{finding.scenario_id} · {finding.title}</button></td><td>{finding.category.replaceAll('_',' ')}</td><td><StatusBadge value={finding.result} /></td><td>{finding.severity}</td><td>{finding.policies.join(', ')}</td><td>{finding.human_review_reason ?? '—'}</td></tr>)}</tbody></table></div></Card>
    {expanded && (() => { const finding = data.findings.find(item => item.scenario_id === expanded)!; return <Card className="finding-drawer"><div className="card-heading"><h2>{finding.scenario_id} evidence</h2><button className="icon-button" onClick={() => setExpanded(null)} aria-label="Close finding detail">×</button></div><div className="finding-columns"><div><h3>Expected behaviour</h3><p>{finding.expected_behavior}</p><h3>Observed sanitized behaviour</h3><p className="evidence-quote">{finding.observed_behavior}</p><h3>Automated evaluators</h3>{finding.evaluator_results.map(item => <div className="evaluator" key={item.evaluator_id}><StatusBadge value={item.result} /><div><strong>{item.evaluator_id.replaceAll('_',' ')}</strong><p>{item.detail}</p></div></div>)}</div><div><h3>Retrieval and context</h3><dl className="detail-list"><div><dt>Raw sources</dt><dd>{finding.retrieved_sources.length}</dd></div><div><dt>Admitted</dt><dd>{finding.retrieved_sources.filter(item => item.admitted_to_context).length}</dd></div><div><dt>Rejected</dt><dd>{finding.retrieved_sources.filter(item => !item.admitted_to_context).length}</dd></div></dl><h3>Tool states</h3><ToolStates finding={finding} />{finding.human_review_reason && <div className="alert alert-review"><strong>Human review required</strong><span>{finding.human_review_reason}</span></div>}</div></div></Card> })()}
  </>
}
