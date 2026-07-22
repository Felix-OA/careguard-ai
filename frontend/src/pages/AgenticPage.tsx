import { FormEvent, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { AgenticCampaign, AgenticComparison, AgenticObjective, AgenticObjectiveRun, AgenticReport, AgenticStrategy, AgenticTurn, Target } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader, SafeMarkdown } from '../components/UI'

function displaySanitized(value: string) {
  return value
    .replace(/<think>[\s\S]*?<\/think>/gi, '[Hidden reasoning excluded]')
    .replace(/(?:chain[- ]of[- ]thought|private reasoning|hidden reasoning)\s*:\s*[^\n]*/gi, '[Hidden reasoning excluded]')
}

export function AgenticPage() {
  const client = useQueryClient()
  const campaigns = useQuery({ queryKey: ['agentic-campaigns'], queryFn: () => api.get<AgenticCampaign[]>('/agentic/campaigns') })
  const comparisons = useQuery({ queryKey: ['agentic-comparisons'], queryFn: () => api.get<AgenticComparison[]>('/agentic/comparisons') })
  const [baseline, setBaseline] = useState('')
  const [guarded, setGuarded] = useState('')
  const compare = useMutation({ mutationFn: () => api.post<AgenticComparison>('/agentic/compare', { baseline_campaign_id: baseline, guarded_campaign_id: guarded }), onSuccess: () => client.invalidateQueries({ queryKey: ['agentic-comparisons'] }) })
  if (campaigns.isLoading || comparisons.isLoading) return <Loading label="Loading controlled campaigns" />
  if (campaigns.error || comparisons.error) return <ErrorState error={(campaigns.error || comparisons.error)!} />
  const items = campaigns.data!
  return <><PageHeader eyebrow="Controlled multi-turn evaluation" title="Agentic audit" description="Run reproducible, synthetic healthcare-security objectives with approved strategies, hard limits, sanitized trajectories, and human review." action={<Link className="button button-primary" to="/agentic/new">New campaign</Link>} />
    <div className="alert alert-info" role="note"><strong>Bounded by design</strong><span>No shell, filesystem, browser, arbitrary network, real patient data, hidden reasoning, or paid API is required.</span></div>
    <Card className="comparison-create"><div className="card-heading"><div><p className="eyebrow">Matching configurations only</p><h2>Compare baseline and guarded campaigns</h2></div></div><form onSubmit={(event: FormEvent) => { event.preventDefault(); compare.mutate() }}><label>Baseline campaign<select required value={baseline} onChange={e => setBaseline(e.target.value)}><option value="">Select baseline</option>{items.filter(item => item.target_path === 'baseline' && ['COMPLETED','LIMIT_REACHED'].includes(item.status)).map(item => <option value={item.campaign_id} key={item.campaign_id}>{item.label} · seed {item.seed}</option>)}</select></label><label>Guarded campaign<select required value={guarded} onChange={e => setGuarded(e.target.value)}><option value="">Select guarded</option>{items.filter(item => item.target_path === 'guarded' && ['COMPLETED','LIMIT_REACHED'].includes(item.status)).map(item => <option value={item.campaign_id} key={item.campaign_id}>{item.label} · seed {item.seed}</option>)}</select></label><button className="button button-primary" disabled={compare.isPending}>Generate comparison</button></form>{compare.error && <p className="error-text">{compare.error.message}</p>}</Card>
    {comparisons.data!.length > 0 && <Card><h2>Agentic comparisons</h2><div className="stack-list">{comparisons.data!.map(item => <div key={item.comparison_id}><Link to={`/agentic/comparisons/${item.comparison_id}`}>{item.comparison_id}</Link><StatusBadge value={item.identical_scope ? 'PASS' : 'FAIL'} /></div>)}</div></Card>}
    {items.length ? <div className="agentic-campaign-grid">{items.map(item => <Link className="card agentic-campaign-card" to={`/agentic/${item.campaign_id}`} key={item.campaign_id}><div className="review-meta"><StatusBadge value={item.status} /><span>{new Date(item.submitted_at).toLocaleString()}</span></div><h2>{item.label}</h2><p>{item.target_path} · {item.objective_ids.length} objectives · seed {item.seed}</p><div className="tag-list"><span>{item.attacker_type}</span><span>{item.result_summary.turn_count ?? 0} turns</span><span>{item.result_summary.review_count ?? 0} REVIEW</span></div></Link>)}</div> : <EmptyState title="No controlled campaigns yet">Create a deterministic baseline campaign to start the local synthetic workflow.</EmptyState>}
  </>
}

export function AgenticNewPage() {
  const client = useQueryClient()
  const targets = useQuery({ queryKey: ['targets'], queryFn: () => api.get<Target[]>('/dashboard/targets') })
  const objectives = useQuery({ queryKey: ['agentic-objectives'], queryFn: () => api.get<AgenticObjective[]>('/agentic/objectives') })
  const strategies = useQuery({ queryKey: ['agentic-strategies'], queryFn: () => api.get<AgenticStrategy[]>('/agentic/strategies') })
  const [targetId, setTargetId] = useState('demo')
  const [targetPath, setTargetPath] = useState<'baseline' | 'guarded'>('baseline')
  const [selected, setSelected] = useState<string[]>([])
  const [label, setLabel] = useState('Healthcare-safe controlled campaign')
  const [attacker, setAttacker] = useState<'deterministic' | 'model'>('deterministic')
  const [seed, setSeed] = useState(42)
  const [maxTurns, setMaxTurns] = useState(5)
  const [maxTotal, setMaxTotal] = useState(50)
  const [maxDuration, setMaxDuration] = useState(120)
  const [maxModelCalls, setMaxModelCalls] = useState(0)
  const [cost, setCost] = useState('')
  const [ack, setAck] = useState(false)
  const run = useMutation({ mutationFn: () => {
    return api.post<AgenticCampaign>('/agentic/campaigns', { label, target_id: targetId, target_path: targetPath, objective_ids: selected.length ? selected : objectives.data!.map(item => item.objective_id), attacker_type: attacker, seed, maximum_turns_per_objective: maxTurns, maximum_total_turns: maxTotal, maximum_duration_seconds: maxDuration, maximum_model_calls: attacker === 'deterministic' ? 0 : maxModelCalls, cost_ceiling_usd: cost === '' ? null : Number(cost), synthetic_authorized_acknowledged: ack }, 180_000)
  }, onSuccess: () => client.invalidateQueries({ queryKey: ['agentic-campaigns'] }) })
  if (targets.isLoading || objectives.isLoading || strategies.isLoading) return <Loading />
  if (targets.error || objectives.error || strategies.error) return <ErrorState error={(targets.error || objectives.error || strategies.error)!} />
  const approvedTargets = targets.data!.filter(item => item.configuration.enabled && (
    targetPath === 'guarded' ? item.target.connector_type === 'guard' : item.target.connector_type !== 'guard'
  ))
  const submit = (event: FormEvent) => { event.preventDefault(); run.mutate() }
  return <><PageHeader eyebrow="Safe-by-default campaign" title="New controlled agentic audit" description="Choose an authorized local target, versioned objectives, deterministic seed, and hard resource limits." /><Card className="form-card agentic-wizard"><form onSubmit={submit}><div className="form-grid"><label className="span-2">Campaign label<input required maxLength={120} value={label} onChange={e => setLabel(e.target.value)} /></label><label>Target path<select value={targetPath} onChange={e => { const value = e.target.value as 'baseline' | 'guarded'; setTargetPath(value); const match = targets.data!.find(item => item.configuration.enabled && (value === 'guarded' ? item.target.connector_type === 'guard' : item.target.connector_type !== 'guard')); setTargetId(match?.target.target_id ?? '') }}><option value="baseline">Baseline</option><option value="guarded">CareGuard-protected</option></select></label><label>Approved local target<select required value={targetId} onChange={e => setTargetId(e.target.value)}>{approvedTargets.map(item => <option value={item.target.target_id} key={item.target.target_id}>{item.target.name}</option>)}</select></label><label>Attacker<select value={attacker} onChange={e => { const value = e.target.value as 'deterministic' | 'model'; setAttacker(value); setMaxModelCalls(value === 'model' ? 10 : 0) }}><option value="deterministic">Deterministic local (recommended)</option><option value="model">Configured local model (optional)</option></select></label><label>Seed<input type="number" min={0} max={2147483647} value={seed} onChange={e => setSeed(Number(e.target.value))} /></label><label>Turns per objective<input type="number" min={1} max={10} value={maxTurns} onChange={e => setMaxTurns(Number(e.target.value))} /></label><label>Total-turn limit<input type="number" min={1} max={100} value={maxTotal} onChange={e => setMaxTotal(Number(e.target.value))} /></label><label>Duration limit (seconds)<input type="number" min={5} max={600} value={maxDuration} onChange={e => setMaxDuration(Number(e.target.value))} /></label><label>Model-call limit<input type="number" min={0} max={50} disabled={attacker === 'deterministic'} value={maxModelCalls} onChange={e => setMaxModelCalls(Number(e.target.value))} /></label><label>Optional cost ceiling (USD)<input type="number" min={0} max={10} step="0.001" disabled={attacker === 'deterministic'} value={cost} onChange={e => setCost(e.target.value)} /></label></div>
      <fieldset className="agentic-objectives"><legend>Approved objective pack 1.0</legend><div className="policy-select">{objectives.data!.map(item => <label className="check" key={item.objective_id}><input type="checkbox" checked={selected.length === 0 || selected.includes(item.objective_id)} onChange={e => { const active = selected.length === 0 ? objectives.data!.map(value => value.objective_id) : selected; setSelected(e.target.checked ? [...new Set([...active,item.objective_id])] : active.filter(value => value !== item.objective_id)) }} /><span><strong>{item.objective_id} · {item.title}</strong><small>{item.maximum_turns} turns max · {item.permitted_strategy_ids.join(', ')}</small></span></label>)}</div></fieldset>
      <label className="check agentic-ack"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} /><span>I confirm this is an authorized local synthetic target and I will not enter real patient information.</span></label>
      <button className="button button-primary" disabled={!ack || run.isPending}>{run.isPending ? 'Running bounded campaign…' : 'Start controlled campaign'}</button>
    </form>{run.error && <div className="alert alert-error" role="alert">{run.error.message}</div>}{run.data && <div className="job-complete"><StatusBadge value={run.data.status} /><div><h2>Campaign evidence persisted</h2><p>{run.data.result_summary.turn_count ?? 0} turns across {run.data.result_summary.objective_count ?? 0} objectives.</p></div><Link className="button button-primary" to={`/agentic/${run.data.campaign_id}`}>Open campaign</Link></div>}</Card>
  </>
}

export function AgenticDetailPage() {
  const { campaignId = '' } = useParams()
  const client = useQueryClient()
  const campaign = useQuery({ queryKey: ['agentic-campaign', campaignId], queryFn: () => api.get<AgenticCampaign>(`/agentic/campaigns/${campaignId}`) })
  const runs = useQuery({ queryKey: ['agentic-runs', campaignId], queryFn: () => api.get<AgenticObjectiveRun[]>(`/agentic/campaigns/${campaignId}/objectives`) })
  const objectives = useQuery({ queryKey: ['agentic-objectives'], queryFn: () => api.get<AgenticObjective[]>('/agentic/objectives') })
  const cancel = useMutation({ mutationFn: () => api.post<AgenticCampaign>(`/agentic/campaigns/${campaignId}/cancel`, {}), onSuccess: value => { client.setQueryData(['agentic-campaign', campaignId], value); client.invalidateQueries({ queryKey: ['agentic-campaigns'] }) } })
  if (campaign.isLoading || runs.isLoading || objectives.isLoading) return <Loading />
  if (campaign.error || runs.error || objectives.error) return <ErrorState error={(campaign.error || runs.error || objectives.error)!} />
  const data = campaign.data!; const catalog = new Map(objectives.data!.map(item => [item.objective_id,item]))
  const active = ['QUEUED','RUNNING'].includes(data.status)
  return <><PageHeader eyebrow={`${data.target_path} · seed ${data.seed}`} title={data.label} description={`${data.campaign_id} · objective pack ${data.objective_pack_version} · strategy pack ${data.strategy_pack_version} · policy ${data.policy_pack_version} · evaluator ${data.evaluator_version}`} action={<div className="button-row">{active && <button className="button" disabled={cancel.isPending || data.cancellation_requested} onClick={() => cancel.mutate()}>{data.cancellation_requested ? 'Cancellation requested' : cancel.isPending ? 'Requesting cancellation…' : 'Cancel campaign'}</button>}<Link className="button" to={`/agentic/${campaignId}/report`}>Preview sanitized report</Link></div>} /><div className="results-strip">{['PASS','PARTIAL','FAIL','REVIEW','INCONCLUSIVE','LIMIT_REACHED'].map(value => <div key={value}><StatusBadge value={value} /><strong>{data.result_summary.outcomes?.[value] ?? 0}</strong></div>)}</div>{cancel.error && <div className="alert alert-error" role="alert">{cancel.error.message}</div>}<Card><div className="detail-list"><div><dt>Status</dt><dd><StatusBadge value={data.status} /></dd></div><div><dt>Attacker</dt><dd>{data.provider_model_display_name}</dd></div><div><dt>Turns</dt><dd>{data.result_summary.turn_count ?? 0} / {data.maximum_total_turns}</dd></div><div><dt>Duration ceiling</dt><dd>{data.maximum_duration_seconds} seconds</dd></div><div><dt>Model calls</dt><dd>{data.result_summary.model_calls ?? 0} / {data.maximum_model_calls}</dd></div></div></Card>
    <div className="agentic-objective-list">{runs.data!.map(run => { const objective = catalog.get(run.objective_id); return <Card key={run.objective_run_id}><div className="review-meta"><StatusBadge value={run.automated_result} /><span>{run.turn_count} turns</span></div><h2>{run.objective_id} · {objective?.title ?? 'Controlled objective'}</h2><p>{objective?.description}</p><div className="tag-list"><span>{run.stop_reason}</span>{objective?.applicable_policy_ids.map(policy => <span key={policy}>{policy}</span>)}</div>{run.human_review_reason && <div className="alert alert-review"><strong>REVIEW</strong><span>{run.human_review_reason}</span></div>}<Link className="button" to={`/agentic/${campaignId}/objectives/${run.objective_run_id}`}>Inspect sanitized trajectory</Link></Card> })}</div>
  </>
}

export function AgenticTrajectoryPage() {
  const { campaignId = '', objectiveRunId = '' } = useParams()
  const turns = useQuery({ queryKey: ['agentic-turns', campaignId, objectiveRunId], queryFn: () => api.get<AgenticTurn[]>(`/agentic/campaigns/${campaignId}/trajectories?objective_run_id=${encodeURIComponent(objectiveRunId)}`) })
  const runs = useQuery({ queryKey: ['agentic-runs', campaignId], queryFn: () => api.get<AgenticObjectiveRun[]>(`/agentic/campaigns/${campaignId}/objectives`) })
  if (turns.isLoading || runs.isLoading) return <Loading />
  if (turns.error || runs.error) return <ErrorState error={(turns.error || runs.error)!} />
  const run = runs.data!.find(item => item.objective_run_id === objectiveRunId)
  return <><PageHeader eyebrow="Sanitized trajectory" title={run?.objective_id ?? 'Controlled objective'} description={`${objectiveRunId} · ${run?.stop_reason ?? 'unknown stop'} · protected response content and hidden reasoning are excluded`} />
    <div className="trajectory-timeline">{turns.data!.map(turn => <Card key={turn.turn_number} className="trajectory-turn"><div className="review-meta"><span>Turn {turn.turn_number}</span><code>{turn.strategy_id}</code><StatusBadge value={turn.response_origin === 'guard' ? 'Guard' : 'Target'} /></div><div className="trajectory-message attacker-message"><strong>Attacker message</strong><p>{displaySanitized(turn.user_test_message)}</p></div><div className="trajectory-message target-message"><strong>{turn.response_origin === 'guard' ? 'Guard-generated response' : 'Target response'}</strong><p>{displaySanitized(turn.sanitized_target_response)}</p></div><div className="trajectory-state"><span>Retrieved {turn.retrieved_sources.length}</span><span>Admitted {turn.admitted_context.length}</span><span>Rejected {turn.rejected_context.length}</span><span>Proposed {turn.proposed_tools.length}</span><span>Blocked {turn.blocked_tools.length}</span><span>Executed {turn.executed_tools.length}</span></div><h3>Evaluator output</h3><div className="signal-list">{turn.evaluator_signals.map((signal,index) => <div key={`${signal.evaluator_id}-${index}`}><StatusBadge value={signal.status} /><span><strong>{signal.dimension}</strong>{signal.detail}</span></div>)}</div>{turn.agent_hijack_indicators.length > 0 && <div className="alert alert-review"><strong>Agent-hijack indicator</strong><span>{turn.agent_hijack_indicators.join(', ')}. The campaign stopped without following target instructions.</span></div>}</Card>)}</div>
    {run && <Card><h2>Final automated result</h2><p><StatusBadge value={run.automated_result} /> · {run.stop_reason}</p>{run.judge_result && <p>Secondary judge: {run.judge_result.outcome}. Disagreement: {run.disagreement ? 'REVIEW required' : 'none'}.</p>}<p className="muted">Reviewer decisions are stored separately and cannot rewrite this evidence.</p></Card>}
  </>
}

export function AgenticComparisonPage() {
  const { comparisonId = '' } = useParams()
  const query = useQuery({ queryKey: ['agentic-comparison', comparisonId], queryFn: () => api.get<AgenticComparison>(`/agentic/comparisons/${comparisonId}`) })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  return <><PageHeader eyebrow="Matching synthetic configuration" title="Agentic baseline versus guarded" description={`${data.comparison_id} · same objectives, versions, seed, attacker, and limits`} action={<Link className="button" to={`/agentic/comparisons/${comparisonId}/report`}>Preview report</Link>} /><div className="scope-banner valid"><StatusBadge value="PASS" /><div><strong>Identical scope verified</strong><span>Observed changes apply only to this fixed local synthetic setup.</span></div></div><Card><div className="table-wrap"><table><caption>Agentic objective comparison</caption><thead><tr><th>Objective</th><th>Baseline</th><th>Guarded</th><th>Turns</th><th>Observed dimensions</th><th>Security</th><th>Utility</th><th>Stop reasons</th><th>Review</th></tr></thead><tbody>{data.objective_results.map(row => <tr key={row.objective_id}><td>{row.objective_id}</td><td><StatusBadge value={row.baseline_result} /></td><td><StatusBadge value={row.guarded_result} /></td><td>{row.baseline_turns} → {row.guarded_turns}</td><td><small>disclosure {row.baseline_metrics.answer_disclosures ?? 0} → {row.guarded_metrics.answer_disclosures ?? 0}<br />context {row.baseline_metrics.untrusted_context_admissions ?? 0} → {row.guarded_metrics.untrusted_context_admissions ?? 0}<br />tools {row.baseline_metrics.tool_executions ?? 0} → {row.guarded_metrics.tool_executions ?? 0}<br />escalation {row.baseline_metrics.safe_escalations ?? 0} → {row.guarded_metrics.safe_escalations ?? 0}<br />hijack {row.baseline_metrics.hijack_indicators ?? 0} → {row.guarded_metrics.hijack_indicators ?? 0}</small></td><td>{row.security_change}</td><td>{row.utility_change}</td><td>{row.baseline_stop_reason} → {row.guarded_stop_reason}</td><td>{row.review_reason ?? row.human_review_change}</td></tr>)}</tbody></table></div></Card><div className="detail-grid"><Card><h2>Observed changes</h2><ul>{data.observed_changes.map(item => <li key={item}>{item}</li>)}</ul>{!data.observed_changes.length && <p>No directional change was established.</p>}</Card><Card><h2>Regressions and review</h2><ul>{[...data.regressions,...data.review_notes].map(item => <li key={item}>{item}</li>)}</ul></Card></div></>
}

export function AgenticReportPage() {
  const { campaignId, comparisonId } = useParams()
  const path = comparisonId ? `/agentic/comparisons/${comparisonId}/report` : `/agentic/campaigns/${campaignId}/report`
  const query = useQuery({ queryKey: ['agentic-report', path], queryFn: () => api.get<AgenticReport>(path) })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  return <><PageHeader eyebrow="Sanitized agentic report" title={query.data!.title} description="Backend-generated summary without raw conversations, protected values, tool arguments, or hidden reasoning." /><div className="report-boundaries">{query.data!.boundaries.map(item => <span key={item}>{item}</span>)}</div><Card className="report-preview"><SafeMarkdown content={query.data!.markdown} /></Card></>
}
