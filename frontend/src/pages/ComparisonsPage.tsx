import { FormEvent, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { AuditSummary, Comparison } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader } from '../components/UI'

export function ComparisonsPage() {
  const client = useQueryClient()
  const comparisons = useQuery({ queryKey: ['comparisons'], queryFn: () => api.get<Comparison[]>('/dashboard/comparisons') })
  const audits = useQuery({ queryKey: ['audits'], queryFn: () => api.get<AuditSummary[]>('/dashboard/audits') })
  const [baseline, setBaseline] = useState('')
  const [guarded, setGuarded] = useState('')
  const create = useMutation({ mutationFn: () => api.post<Comparison>('/dashboard/comparisons', { baseline_run_id: baseline, guarded_run_id: guarded }), onSuccess: () => { client.invalidateQueries({ queryKey: ['comparisons'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); client.invalidateQueries({ queryKey: ['reports'] }) } })
  if (comparisons.isLoading || audits.isLoading) return <Loading />
  if (comparisons.error || audits.error) return <ErrorState error={(comparisons.error || audits.error)!} />
  const submit = (event: FormEvent) => { event.preventDefault(); create.mutate() }
  return <><PageHeader eyebrow="Validated scope" title="Baseline versus guarded" description="Compare equivalent fixed-suite evidence without hiding security regressions, utility changes, or human review." /><Card className="comparison-create"><form onSubmit={submit}><label>Baseline run<select required value={baseline} onChange={e => setBaseline(e.target.value)}><option value="">Select baseline</option>{audits.data!.filter(item => item.target_id === 'demo').map(item => <option value={item.run_id} key={item.run_id}>{item.run_id}</option>)}</select></label><label>Guarded run<select required value={guarded} onChange={e => setGuarded(e.target.value)}><option value="">Select guarded</option>{audits.data!.filter(item => item.target_id === 'demo-guarded').map(item => <option value={item.run_id} key={item.run_id}>{item.run_id}</option>)}</select></label><button className="button button-primary" disabled={create.isPending}>Generate comparison</button></form>{create.error && <p className="error-text">{create.error.message}</p>}</Card>
    {comparisons.data!.length ? <div className="comparison-list">{comparisons.data!.map(item => <Link to={`/comparisons/${item.comparison_id}`} className="card comparison-card" key={item.comparison_id}><div><StatusBadge value={item.identical_scope ? 'PASS' : 'FAIL'} /><span>{new Date(item.created_at).toLocaleString()}</span></div><h2>Baseline → Guarded</h2><div className="comparison-counts"><span>{item.baseline_metrics.counts.FAIL} FAIL</span><strong>→</strong><span>{item.guarded_metrics.counts.FAIL} FAIL</span><span>{item.guarded_metrics.counts.REVIEW} REVIEW</span></div><p>{item.security_improvements.length} observed reductions · {item.regressions.length} regression signals</p></Link>)}</div> : <EmptyState title="No comparisons yet">Run equivalent baseline and guarded audits, then generate a comparison.</EmptyState>}
  </>
}

const metricLabels: Record<string, string> = { answer_disclosure: 'Answer disclosure', retrieval_exposure: 'Raw confidential retrieval', confidential_context_admitted: 'Confidential context admitted', untrusted_context_admitted: 'Untrusted context admitted', unauthorized_tool_proposals: 'Unauthorized active proposals', blocked_upstream_tool_proposals: 'Blocked upstream proposals', unauthorized_tool_executions: 'Unauthorized executions', confirmation_failures: 'Confirmation failures', grounding_issues: 'Grounding issues', refusal_correctness_issues: 'Refusal correctness issues', utility_issues: 'Utility issues' }

export function ComparisonDetailPage() {
  const { comparisonId = '' } = useParams()
  const query = useQuery({ queryKey: ['comparison', comparisonId], queryFn: () => api.get<Comparison>(`/dashboard/comparisons/${comparisonId}`) })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  return <><PageHeader eyebrow="Fixed synthetic suite" title="Security change, with scope intact" description={`${data.comparison_id} · ${data.scenario_ids.length} scenarios · scenario ${String(data.scope_validation.scenario_version)} · policy ${String(data.scope_validation.policy_pack_version)} · Guard ${String(data.policy_configuration.version ?? 'unknown')} (${String(data.policy_configuration.mode ?? 'unknown')})`} action={<Link className="button" to={`/reports/comparison/${comparisonId}`}>Preview report</Link>} /><div className={`scope-banner ${data.identical_scope ? 'valid' : 'invalid'}`}><StatusBadge value={data.identical_scope ? 'PASS' : 'FAIL'} /><div><strong>{data.identical_scope ? 'Identical scope verified' : 'Scope mismatch'}</strong><span>Baseline {data.baseline_target_id} and guarded {data.guarded_target_id}: counts, scenario order, versions, expected behavior, and evaluator definitions are backend-validated.</span></div></div>
    <div className="count-comparison"><div><p>Baseline</p>{(['PASS','PARTIAL','FAIL','REVIEW'] as const).map(key => <span key={key}><StatusBadge value={key} /><strong>{data.baseline_metrics.counts[key]}</strong></span>)}</div><div className="comparison-arrow" aria-hidden="true">→</div><div><p>Guarded</p>{(['PASS','PARTIAL','FAIL','REVIEW'] as const).map(key => <span key={key}><StatusBadge value={key} /><strong>{data.guarded_metrics.counts[key]}</strong></span>)}</div></div>
    <Card><div className="card-heading"><div><p className="eyebrow">Observed metrics</p><h2>Security and utility comparison</h2></div><span className="muted">Not universal product claims</span></div><div className="metric-comparison">{Object.entries(metricLabels).map(([key,label]) => <div key={key}><span>{label}</span><strong>{Number(data.baseline_metrics[key] ?? 0)}</strong><span aria-label="changed to">→</span><strong>{Number(data.guarded_metrics[key] ?? 0)}</strong></div>)}</div></Card>
    <Card><div className="card-heading"><div><p className="eyebrow">Scenario-level validation</p><h2>Every outcome remains visible</h2></div></div><div className="table-wrap"><table><caption>Baseline versus guarded scenario outcomes</caption><thead><tr><th>Scenario</th><th>Baseline</th><th>Guarded</th><th>Security change</th><th>Utility change</th><th>Review reason</th></tr></thead><tbody>{data.scenario_results.map(item => <tr key={item.scenario_id}><td>{item.scenario_id}</td><td><StatusBadge value={item.baseline_result} /></td><td><StatusBadge value={item.guarded_result} /></td><td>{item.security_change}</td><td>{item.utility_change}</td><td>{item.manual_review_reason ?? '—'}</td></tr>)}</tbody></table></div></Card>
    <div className="detail-grid"><Card><h2>Observed improvements</h2><ul>{data.security_improvements.map(item => <li key={item}>{item}</li>)}</ul></Card><Card><h2>Regression and utility notes</h2>{data.regressions.length || data.utility_tradeoffs.length ? <ul>{[...data.regressions,...data.utility_tradeoffs].map(item => <li key={item}>{item}</li>)}</ul> : <p>No fixed-suite regressions or utility tradeoffs were reported.</p>}</Card></div>
  </>
}
