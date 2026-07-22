import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { SafeEvent } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader } from '../components/UI'

interface EventPage {
  items: SafeEvent[]
  page: number
  page_size: number
  total: number
  source_status: 'available' | 'unavailable'
  source_detail: string | null
}

export function EventsPage() {
  const [decision, setDecision] = useState('')
  const [review, setReview] = useState('')
  const [reasonCode, setReasonCode] = useState('')
  const [policy, setPolicy] = useState('')
  const [target, setTarget] = useState('')
  const [mode, setMode] = useState('')
  const [date, setDate] = useState('')
  const [page, setPage] = useState(1)
  const resetPage = () => setPage(1)
  const params = new URLSearchParams({ page: String(page), page_size: '25' })
  if (decision) params.set('decision', decision)
  if (review) params.set('human_review', review)
  if (reasonCode) params.set('reason_code', reasonCode)
  if (policy) params.set('policy_id', policy)
  if (target) params.set('target_id', target)
  if (mode) params.set('guard_mode', mode)
  if (date) {
    params.set('date_from', `${date}T00:00:00Z`)
    params.set('date_to', `${date}T23:59:59Z`)
  }
  const query = useQuery({
    queryKey: ['events', decision, review, reasonCode, policy, target, mode, date, page],
    queryFn: () => api.get<EventPage>(`/dashboard/events?${params}`),
  })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  return <>
    <PageHeader eyebrow="Runtime telemetry" title="Guard security events" description="Sanitized request decisions, retrieval states, redactions, and tool states. Protected responses never enter this interface." />
    {data.source_status === 'unavailable' && <div className="alert alert-error" role="alert"><strong>Event source unavailable</strong><span>{data.source_detail} Check System status and retry.</span></div>}
    <div className="filters">
      <label>Decision<select value={decision} onChange={event => { setDecision(event.target.value); resetPage() }}><option value="">All decisions</option>{['ALLOW', 'ALLOW_WITH_WARNING', 'BLOCK', 'REDACT', 'ESCALATE', 'REQUIRE_CONFIRMATION', 'REQUIRE_HUMAN_REVIEW'].map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Human review<select value={review} onChange={event => { setReview(event.target.value); resetPage() }}><option value="">All events</option><option value="true">Required</option><option value="false">Not required</option></select></label>
      <label>Reason code<input value={reasonCode} maxLength={100} placeholder="Exact code" onChange={event => { setReasonCode(event.target.value); resetPage() }} /></label>
      <label>Policy<input value={policy} maxLength={100} placeholder="CG-…" onChange={event => { setPolicy(event.target.value); resetPage() }} /></label>
      <label>Target<input value={target} maxLength={80} placeholder="demo" onChange={event => { setTarget(event.target.value); resetPage() }} /></label>
      <label>Guard mode<select value={mode} onChange={event => { setMode(event.target.value); resetPage() }}><option value="">All modes</option><option value="monitor">Monitor</option><option value="enforce">Enforce</option></select></label>
      <label>Date<input type="date" value={date} onChange={event => { setDate(event.target.value); resetPage() }} /></label>
    </div>
    {data.items.length ? <Card><div className="table-wrap"><table><caption>Sanitized Guard events</caption><thead><tr><th>Timestamp</th><th>Event</th><th>Decision</th><th>Mode</th><th>Reason codes</th><th>Proposed</th><th>Blocked</th><th>Executed</th><th>Review</th></tr></thead><tbody>{data.items.map(event => <tr key={event.event_id}><td>{new Date(event.timestamp).toLocaleString()}</td><td><Link to={`/events/${event.event_id}`}>{event.event_id.slice(0, 18)}…</Link></td><td><StatusBadge value={event.final_decision} /></td><td>{event.guard_mode}</td><td>{event.reason_codes.join(', ') || '—'}</td><td>{event.proposed_tools.length}</td><td>{event.blocked_tools.length}</td><td>{event.executed_tools.length}</td><td>{event.human_review_required ? 'Required' : '—'}</td></tr>)}</tbody></table></div><div className="pagination"><button className="button" disabled={page === 1} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page} · {data.total} events</span><button className="button" disabled={page * 25 >= data.total} onClick={() => setPage(value => value + 1)}>Next</button></div></Card> : <EmptyState title="No Guard events">{data.source_status === 'available' ? 'Run the guarded audit or synthetic demo to produce local security decisions.' : 'Events cannot be counted while the Guard event source is unavailable.'}</EmptyState>}
  </>
}

export function EventDetailPage() {
  const { eventId = '' } = useParams()
  const query = useQuery({ queryKey: ['event', eventId], queryFn: () => api.get<SafeEvent>(`/dashboard/events/${eventId}`) })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const event = query.data!
  return <><PageHeader eyebrow={`${event.guard_mode} · config ${event.guard_config_version}`} title="Sanitized event detail" description={`${event.event_id} · ${new Date(event.timestamp).toLocaleString()}`} /><div className="scope-banner valid"><StatusBadge value={event.final_decision} /><div><strong>Final decision</strong><span>Would enforce: {event.would_enforce_decision}. {event.request_summary}</span></div></div>
    <div className="detail-grid"><Card><h2>Decision timeline</h2><ol className="timeline"><li><strong>Request inspected</strong><span>{event.reason_codes.join(', ') || 'No matched reason codes'}</span></li><li><strong>Context classified</strong><span>{event.raw_retrieval_metadata.length} raw · {event.rejected_retrieval_metadata.length} rejected · {event.admitted_context_metadata.length} admitted</span></li><li><strong>Response controlled</strong><span>{event.redaction_categories.length} redaction categories · confirmation {event.confirmation_status}</span></li><li><strong>Final response</strong><span>{event.final_response}</span></li></ol></Card><Card><h2>Triggered policy</h2><div className="tag-list">{event.triggered_policies.map(value => <span key={value}>{value}</span>)}</div><h3>Tool-state summary</h3><div className="tool-state-grid"><div><strong>{event.proposed_tools.length}</strong><span>Proposed</span></div><div><strong>{event.blocked_tools.length}</strong><span>Blocked</span></div><div><strong>{event.failed_tools.length}</strong><span>Failed</span></div><div><strong>{event.executed_tools.length}</strong><span>Executed</span></div></div>{event.human_review_required && <div className="alert alert-review"><strong>Human review required</strong><span>The automated decision remains unchanged by reviewer workflow.</span></div>}</Card></div>
    <Card><h2>Source trust states</h2><div className="table-wrap"><table><caption>Safe source metadata without excerpts</caption><thead><tr><th>Source</th><th>Title</th><th>Trust</th><th>State</th></tr></thead><tbody>{event.raw_retrieval_metadata.map(source => <tr key={`${source.source_id}-raw`}><td>{source.source_id}</td><td>{source.title}</td><td>{source.trust_level}</td><td>{source.admitted_to_context ? 'Admitted' : 'Rejected'}</td></tr>)}</tbody></table></div></Card>
  </>
}
