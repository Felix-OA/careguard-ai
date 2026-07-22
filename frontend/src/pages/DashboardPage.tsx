import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { DashboardSummary } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, Disclaimer, EmptyState, ErrorState, Loading, Metric, PageHeader } from '../components/UI'

const countKeys = ['PASS', 'PARTIAL', 'FAIL', 'REVIEW'] as const

export function DashboardPage() {
  const query = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get<DashboardSummary>('/dashboard/summary'), refetchInterval: 30_000 })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  const chartData = Object.entries(data.finding_categories).map(([name, value]) => ({ name: name.replaceAll('_', ' '), value }))
  return <>
    <PageHeader eyebrow="Security posture" title="Healthcare AI security, without the guesswork" description="Live signals from the fixed synthetic audit suite and CareGuard runtime controls." action={<Link className="button button-primary" to="/audits/new">Run an audit</Link>} />
    <Disclaimer />
    <div className="metrics-grid top-metrics">
      <Metric label="Active targets" value={data.active_target_count} hint="Local and explicitly authorized" />
      <Metric label="Guard mode" value={<StatusBadge value={data.guard_mode ?? 'unavailable'} />} hint="Current runtime configuration" />
      <Metric label="Human review" value={data.unresolved_review_count} hint="Unreviewed decisions preserved" />
      <Metric label="Latest suite" value={data.latest_guarded_audit ? 'Guarded' : data.latest_baseline_audit ? 'Baseline' : 'Not run'} hint={data.latest_guarded_audit?.run_id ?? data.latest_baseline_audit?.run_id ?? 'Start from Audits'} />
    </div>
    <div className="results-strip" aria-label="Latest audit result counts">{countKeys.map(status => <div key={status}><StatusBadge value={status} /><strong>{data.result_counts[status] ?? 0}</strong></div>)}</div>
    <div className="dashboard-grid">
      <Card className="span-2"><div className="card-heading"><div><p className="eyebrow">Latest guarded assessment</p><h2>Bounded control outcomes</h2></div>{data.latest_guarded_audit && <Link to={`/audits/${data.latest_guarded_audit.run_id}`}>View audit →</Link>}</div>
        {data.latest_guarded_audit ? <div className="comparison-snapshot">
          <div><small>Answer disclosure</small><strong>{data.retrieval_metrics.answer_disclosure ?? 0}</strong><span>guarded findings</span></div>
          <div><small>Raw confidential retrieval</small><strong>{data.retrieval_metrics.retrieval_exposure ?? 0}</strong><span>not context admission</span></div>
          <div><small>Confidential admitted</small><strong>{data.retrieval_metrics.confidential_context_admitted ?? 0}</strong><span>authorized context records</span></div>
          <div><small>Blocked upstream tools</small><strong>{data.tool_metrics.blocked_upstream_tool_proposals ?? 0}</strong><span>not executions</span></div>
        </div> : <EmptyState title="No guarded audit yet">Run the guarded suite to populate validated control metrics.</EmptyState>}
      </Card>
      <Card><div className="card-heading"><div><p className="eyebrow">Service health</p><h2>Local system</h2></div><Link to="/settings">Details →</Link></div><div className="stack-list">{data.services.map(service => <div key={service.service}><span>{service.service.replace('-', ' ')}</span><StatusBadge value={service.status} /></div>)}</div></Card>
      <Card className="span-2"><div className="card-heading"><div><p className="eyebrow">Finding distribution</p><h2>Risk categories</h2></div><span className="muted">Latest completed audit</span></div>
        {chartData.length ? <><div className="chart" role="img" aria-label="Bar chart of findings by risk category"><ResponsiveContainer width="100%" height={240}><BarChart data={chartData} layout="vertical" margin={{ left: 20 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="value" fill="var(--teal-500)" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div><table className="sr-table"><caption>Finding distribution values</caption><tbody>{chartData.map(item => <tr key={item.name}><th>{item.name}</th><td>{item.value}</td></tr>)}</tbody></table></> : <EmptyState title="No finding distribution">Complete an audit to view category signals.</EmptyState>}
      </Card>
      <Card><div className="card-heading"><div><p className="eyebrow">Runtime decisions</p><h2>Guard events</h2></div><Link to="/events">Explore →</Link></div><div className="decision-list">{Object.entries(data.event_decisions).slice(0, 6).map(([status, count]) => <div key={status}><StatusBadge value={status} /><strong>{count}</strong></div>)}{!Object.keys(data.event_decisions).length && <p className="muted">No runtime events recorded.</p>}</div></Card>
      <Card className="span-3"><div className="card-heading"><div><p className="eyebrow">Recent activity</p><h2>Audit history</h2></div><Link to="/audits">All audits →</Link></div>{data.recent_audits.length ? <div className="table-wrap"><table><caption>Recent audit activity</caption><thead><tr><th>Run</th><th>Target</th><th>Completed</th><th>PASS</th><th>FAIL</th><th>REVIEW</th></tr></thead><tbody>{data.recent_audits.map(audit => <tr key={audit.run_id}><td><Link to={`/audits/${audit.run_id}`}>{audit.run_id}</Link></td><td>{audit.target_id}</td><td>{new Date(audit.completed_at).toLocaleString()}</td><td>{audit.counts.PASS}</td><td>{audit.counts.FAIL}</td><td>{audit.counts.REVIEW}</td></tr>)}</tbody></table></div> : <EmptyState title="No audits yet">Start the fixed synthetic suite from the audit workflow.</EmptyState>}</Card>
    </div>
  </>
}
