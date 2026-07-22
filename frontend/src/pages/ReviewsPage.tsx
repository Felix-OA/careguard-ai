import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ReviewItem, ReviewStatus } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader } from '../components/UI'

export function ReviewsPage() {
  const [filter, setFilter] = useState<ReviewStatus | 'ALL'>('UNREVIEWED')
  const [editing, setEditing] = useState<ReviewItem | null>(null)
  const [status, setStatus] = useState<ReviewStatus>('UNREVIEWED')
  const [note, setNote] = useState('')
  const dialogRef = useRef<HTMLElement>(null)
  const reviewTriggerRef = useRef<HTMLButtonElement>(null)
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['reviews'], queryFn: () => api.get<ReviewItem[]>('/dashboard/reviews') })
  const save = useMutation({ mutationFn: () => api.put(`/dashboard/reviews/${encodeURIComponent(editing!.review_id)}`, { status, note: note || null }), onSuccess: () => { setEditing(null); client.invalidateQueries({ queryKey: ['reviews'] }); client.invalidateQueries({ queryKey: ['dashboard'] }) } })
  useEffect(() => {
    if (!editing) return
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setEditing(null); return }
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), select:not([disabled]), textarea:not([disabled])')]
      if (!focusable.length) return
      const first = focusable[0]; const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', handleKey)
    return () => { document.removeEventListener('keydown', handleKey); reviewTriggerRef.current?.focus() }
  }, [editing])
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const currentItems = query.data!.filter(item => !item.is_stale)
  const items = query.data!.filter(item => filter === 'ALL' ? true : !item.is_stale && item.decision.status === filter)
  return <><PageHeader eyebrow="Human judgment" title="Review queue" description="Automated results remain immutable. Reviewer decisions and notes are stored as a separate local demonstration workflow." /><div className="review-summary">{(['UNREVIEWED','CONFIRMED_SAFE','CONFIRMED_FINDING','NEEDS_MORE_CONTEXT'] as ReviewStatus[]).map(value => <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}><StatusBadge value={value} /><strong>{currentItems.filter(item => item.decision.status === value).length}</strong></button>)}</div>
    <div className="button-row review-history-toggle"><button className="button" onClick={() => setFilter(filter === 'ALL' ? 'UNREVIEWED' : 'ALL')}>{filter === 'ALL' ? 'Show current unresolved' : `Show history (${query.data!.length - currentItems.length} superseded)`}</button></div>
    {items.length ? <div className="review-list">{items.map(item => <Card key={item.review_id} className="review-card"><div className="review-meta"><span>{item.source_type.replace('_',' ')}</span><span>{new Date(item.timestamp).toLocaleString()}</span><StatusBadge value={item.automated_result} />{item.is_stale && <StatusBadge value="historical" />}</div><h2>{item.scenario_id ?? item.source_id}</h2>{item.is_stale && <p className="field-help">Superseded by run {item.superseded_by}; excluded from the current unresolved count.</p>}<p className="review-reason">{item.review_reason}</p><p className="evidence-quote">{item.evidence_summary}</p><div className="tag-list">{item.policy_categories.map(value => <span key={value}>{value}</span>)}</div><div className="review-footer"><StatusBadge value={item.decision.status} /><button className="button" onClick={event => { reviewTriggerRef.current = event.currentTarget; setEditing(item); setStatus(item.decision.status); setNote(item.decision.note ?? '') }}>Record review</button></div></Card>)}</div> : <EmptyState title="No review items in this state">Change the status filter or run the guarded suite.</EmptyState>}
    {editing && <div className="modal-backdrop" role="presentation" onMouseDown={e => e.target === e.currentTarget && setEditing(null)}><section ref={dialogRef} className="modal" role="dialog" aria-modal="true" aria-labelledby="review-dialog-title"><div className="card-heading"><h2 id="review-dialog-title">Review {editing.scenario_id ?? editing.source_id}</h2><button className="icon-button" aria-label="Close review dialog" onClick={() => setEditing(null)}>×</button></div><div className="alert alert-review"><strong>Automated result: {editing.automated_result}</strong><span>This decision will not overwrite the automated evidence.</span></div><label>Reviewer decision<select autoFocus value={status} onChange={e => setStatus(e.target.value as ReviewStatus)}><option>UNREVIEWED</option><option>CONFIRMED_SAFE</option><option>CONFIRMED_FINDING</option><option>NEEDS_MORE_CONTEXT</option></select></label><label>Concise reviewer note<textarea maxLength={500} value={note} onChange={e => setNote(e.target.value)} /></label>{save.error && <div className="alert alert-error" role="alert">{save.error.message}</div>}<div className="button-row"><button className="button" onClick={() => setEditing(null)}>Cancel</button><button className="button button-primary" onClick={() => save.mutate()} disabled={save.isPending}>Save review</button></div></section></div>}
  </>
}
