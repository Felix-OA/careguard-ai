import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import type { DemoResult } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, Disclaimer, PageHeader } from '../components/UI'

const prompts = [
  ['benign','Benign clinic policy'], ['cross_patient','Cross-patient request'], ['fake_authority','Fake authority'],
  ['untrusted','Untrusted source'], ['appointment','Appointment confirmation'], ['emergency','Emergency escalation'],
] as const

function DemoColumn({ path, prompt, custom }: { path: 'baseline' | 'guarded'; prompt: string; custom: string }) {
  const run = useMutation({ mutationFn: () => api.post<DemoResult>('/dashboard/demo/chat', { path, prompt_id: prompt, custom_message: prompt === 'custom' ? custom : null }) })
  return <Card className={`demo-column ${path}`}><div className="demo-title"><div className="target-icon" aria-hidden="true">{path === 'guarded' ? 'CG' : 'AI'}</div><div><p className="eyebrow">{path === 'guarded' ? 'CareGuard protected' : 'Unprotected target'}</p><h2>{path === 'guarded' ? 'Bounded runtime controls' : 'Intentional baseline weaknesses'}</h2></div></div><button className={`button ${path === 'guarded' ? 'button-primary' : ''}`} onClick={() => run.mutate()} disabled={run.isPending}>{run.isPending ? 'Running…' : `Send to ${path}`}</button>{run.error && <div className="alert alert-error">{run.error.message}</div>}{run.data && <div className="demo-result" aria-live="polite"><div className="demo-status"><StatusBadge value={run.data.decision ?? (path === 'baseline' ? 'Uncontrolled' : 'ALLOW')} />{run.data.human_review_required && <StatusBadge value="REVIEW" />}</div><h3>Sanitized response</h3><p className="evidence-quote">{run.data.answer}</p>{(run.data.reason_codes.length > 0 || run.data.triggered_policies.length > 0) && <div className="tag-list" aria-label="Triggered controls">{run.data.reason_codes.map(value => <span key={value}>{value}</span>)}{run.data.triggered_policies.map(value => <span key={value}>{value}</span>)}</div>}<div className="demo-metrics"><span><strong>{run.data.retrieval_counts.raw}</strong> raw sources</span><span><strong>{run.data.retrieval_counts.admitted}</strong> admitted</span><span><strong>{run.data.retrieval_counts.rejected}</strong> rejected</span><span><strong>{run.data.blocked_tools.length}</strong> blocked tools</span><span><strong>{run.data.executed_tools.length}</strong> executed</span><span><strong>{run.data.redaction_count}</strong> redactions</span></div></div>}</Card>
}

export function DemoPage() {
  const [prompt, setPrompt] = useState('benign')
  const [custom, setCustom] = useState('What are the synthetic clinic hours?')
  return <><PageHeader eyebrow="Guided synthetic experience" title="See the defensive boundary" description="Run the same harmless fictional prompt against the intentional baseline and CareGuard-protected path." /><Disclaimer /><Card className="demo-controls"><label>Approved prompt<select value={prompt} onChange={e => setPrompt(e.target.value)}>{prompts.map(([value,label]) => <option value={value} key={value}>{label}</option>)}<option value="custom">Custom synthetic prompt</option></select></label>{prompt === 'custom' && <label>Custom prompt<textarea value={custom} maxLength={1000} onChange={e => setCustom(e.target.value)} /></label>}<div className="alert alert-info"><strong>Synthetic use only</strong><span>Do not enter real patient information, credentials, or protected health data.</span></div></Card><div className="demo-grid"><DemoColumn path="baseline" prompt={prompt} custom={custom} /><DemoColumn path="guarded" prompt={prompt} custom={custom} /></div></>
}
