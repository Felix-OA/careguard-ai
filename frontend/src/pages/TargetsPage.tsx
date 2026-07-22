import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Target } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader } from '../components/UI'

export function TargetsPage() {
  const query = useQuery({ queryKey: ['targets'], queryFn: () => api.get<Target[]>('/dashboard/targets') })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  return <><PageHeader eyebrow="Integration inventory" title="Targets" description="Local, explicitly authorized connectors and their declared inspection capability." action={<Link className="button button-primary" to="/onboarding">Add a target</Link>} />
    {query.data!.length ? <div className="target-grid">{query.data!.map(item => <Link to={`/targets/${item.target.target_id}`} className="card target-card" key={item.target.target_id}><div className="target-icon" aria-hidden="true">{item.target.connector_type === 'guard' ? 'CG' : 'AI'}</div><div><div className="target-title"><h2>{item.target.name}</h2><StatusBadge value={item.configuration.enabled ? 'ALLOW' : 'disabled'} /></div><p>{item.target.connector_type.replace('_', ' ')} · {item.configuration.integration_capability.replaceAll('_', ' ')}</p><dl><div><dt>Credentials</dt><dd>{item.configuration.credential_status}</dd></div><div><dt>Recent audits</dt><dd>{item.recent_audits.length}</dd></div><div><dt>Guard mode</dt><dd>{item.guard_mode ?? 'Not applicable'}</dd></div></dl></div></Link>)}</div> : <EmptyState title="No targets configured">Use onboarding to add an authorized local target.</EmptyState>}
  </>
}

function TargetConfigurationEditor({ data, targetId, onSaved }: { data: Target; targetId: string; onSaved: () => void }) {
  const [name, setName] = useState(data.target.name)
  const [endpoint, setEndpoint] = useState(data.target.endpoint ?? '')
  const [model, setModel] = useState(data.target.model ?? '')
  const [capability, setCapability] = useState(data.configuration.integration_capability)
  const [chatPath, setChatPath] = useState(data.configuration.chat_path)
  const [timeout, setTimeoutValue] = useState(data.configuration.timeout_seconds)
  const [provider, setProvider] = useState(data.configuration.provider_label ?? '')
  const [authorized, setAuthorized] = useState(false)
  const customTarget = !['demo', 'demo-guarded'].includes(targetId)
  const save = useMutation({ mutationFn: () => api.put<Target>(`/dashboard/targets/${targetId}`, {
    name, endpoint: endpoint || null, model: model || null, authorized_target_confirmed: !customTarget || authorized,
    configuration: {
      integration_capability: capability, chat_path: chatPath,
      request_message_field: data.configuration.request_message_field,
      response_answer_field: data.configuration.response_answer_field,
      conversation_field: data.configuration.conversation_field,
      retrieval_metadata_field: data.configuration.retrieval_metadata_field,
      timeout_seconds: timeout, provider_label: provider || null, enabled: data.configuration.enabled,
    },
  }), onSuccess: onSaved })
  return <Card className="span-2"><div className="card-heading"><div><p className="eyebrow">Non-secret configuration</p><h2>Edit connector display and mapping</h2></div><span className="muted">Existing server-side credential reference is preserved</span></div><form onSubmit={event => { event.preventDefault(); save.mutate() }}><div className="form-grid"><label>Target name<input required maxLength={160} value={name} onChange={event => setName(event.target.value)} /></label><label>Integration capability<select value={capability} onChange={event => setCapability(event.target.value as Target['configuration']['integration_capability'])}><option value="proxy_only">Proxy only</option><option value="deep_retrieval">Deep retrieval</option><option value="tool_control">Tool control</option></select></label>{customTarget && <><label className="span-2">Authorized local origin<input placeholder="http://127.0.0.1:8001" value={endpoint} onChange={event => setEndpoint(event.target.value)} /></label><label className="check span-2"><input type="checkbox" checked={authorized} onChange={event => setAuthorized(event.target.checked)} /> I reconfirm that this local synthetic target is owned by or explicitly authorized for my testing.</label></>}<label>Chat path<input required value={chatPath} onChange={event => setChatPath(event.target.value)} /></label><label>Timeout (seconds)<input type="number" min="1" max="60" value={timeout} onChange={event => setTimeoutValue(Number(event.target.value))} /></label><label>Provider label<input maxLength={120} value={provider} onChange={event => setProvider(event.target.value)} /></label><label>Model label<input maxLength={160} value={model} onChange={event => setModel(event.target.value)} /></label></div>{save.error && <div className="alert alert-error" role="alert">{save.error.message}</div>}<button className="button button-primary" disabled={save.isPending || (customTarget && !authorized)}>{save.isPending ? 'Saving…' : 'Save non-secret configuration'}</button></form></Card>
}

export function TargetDetailPage() {
  const { targetId = '' } = useParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const query = useQuery({ queryKey: ['target', targetId], queryFn: () => api.get<Target>(`/dashboard/targets/${targetId}`) })
  const test = useMutation({ mutationFn: () => api.post<{ status: string; detail: string; latency_ms: number | null }>(`/dashboard/targets/${targetId}/test`) })
  const toggle = useMutation({ mutationFn: (enabled: boolean) => {
    const data = query.data!
    const configuration = {
      integration_capability: data.configuration.integration_capability,
      chat_path: data.configuration.chat_path,
      request_message_field: data.configuration.request_message_field,
      response_answer_field: data.configuration.response_answer_field,
      conversation_field: data.configuration.conversation_field,
      retrieval_metadata_field: data.configuration.retrieval_metadata_field,
      timeout_seconds: data.configuration.timeout_seconds,
      provider_label: data.configuration.provider_label,
      enabled,
    }
    return api.put<Target>(`/dashboard/targets/${targetId}`, { name: data.target.name, endpoint: data.target.endpoint, model: data.target.model, authorized_target_confirmed: true, configuration })
  }, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['target', targetId] }); queryClient.invalidateQueries({ queryKey: ['targets'] }); queryClient.invalidateQueries({ queryKey: ['dashboard'] }) } })
  const remove = useMutation({ mutationFn: () => api.delete(`/dashboard/targets/${targetId}`), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['targets'] }); queryClient.invalidateQueries({ queryKey: ['dashboard'] }); navigate('/targets') } })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  return <><PageHeader eyebrow="Target detail" title={data.target.name} description={`${data.target.connector_type.replace('_', ' ')} connector · created ${new Date(data.target.created_at).toLocaleDateString()}`} action={<button className="button button-primary" onClick={() => test.mutate()} disabled={test.isPending}>Test connection</button>} />
    {test.data && <div className="alert alert-info"><StatusBadge value={test.data.status} /><span>{test.data.detail} {test.data.latency_ms ? `(${test.data.latency_ms.toFixed(0)} ms)` : ''}</span></div>}
    <div className="detail-grid"><Card><p className="eyebrow">Connector</p><h2>Connection profile</h2><dl className="detail-list"><div><dt>Target ID</dt><dd>{data.target.target_id}</dd></div><div><dt>Endpoint</dt><dd>{data.target.endpoint ?? 'In-process local target'}</dd></div><div><dt>Chat path</dt><dd>{data.configuration.chat_path}</dd></div><div><dt>Provider</dt><dd>{data.configuration.provider_label ?? 'Not specified'}</dd></div><div><dt>Credentials</dt><dd>{data.configuration.credential_status}</dd></div></dl></Card>
      <Card><p className="eyebrow">Capability</p><h2>{data.configuration.integration_capability.replaceAll('_', ' ')}</h2><p>{data.configuration.integration_capability === 'proxy_only' ? 'CareGuard can inspect requests and surfaced output, but cannot control hidden retrieval context.' : data.configuration.integration_capability === 'deep_retrieval' ? 'Authorized retrieval and generation hooks expose candidates before context assembly.' : 'CareGuard can authorize and confirm surfaced tool actions before execution.'}</p><div className="button-row"><button className="button" onClick={() => toggle.mutate(!data.configuration.enabled)}>{data.configuration.enabled ? 'Disable target' : 'Enable target'}</button>{!['demo','demo-guarded'].includes(targetId) && <button className="button button-danger" onClick={() => window.confirm('Delete this local target? This cannot be undone.') && remove.mutate()}>Delete target</button>}</div></Card>
      <TargetConfigurationEditor key={data.configuration.updated_at} data={data} targetId={targetId} onSaved={() => { queryClient.invalidateQueries({ queryKey: ['target', targetId] }); queryClient.invalidateQueries({ queryKey: ['targets'] }); queryClient.invalidateQueries({ queryKey: ['dashboard'] }) }} />
      <Card className="span-2"><div className="card-heading"><h2>Recent audits</h2><Link to="/audits/new">Run audit →</Link></div>{data.recent_audits.length ? <div className="table-wrap"><table><caption>Recent target audits</caption><thead><tr><th>Run</th><th>Completed</th><th>PASS</th><th>FAIL</th><th>REVIEW</th></tr></thead><tbody>{data.recent_audits.map(audit => <tr key={audit.run_id}><td><Link to={`/audits/${audit.run_id}`}>{audit.run_id}</Link></td><td>{new Date(audit.completed_at).toLocaleString()}</td><td>{audit.counts.PASS}</td><td>{audit.counts.FAIL}</td><td>{audit.counts.REVIEW}</td></tr>)}</tbody></table></div> : <EmptyState title="No audits for this target">Run the fixed synthetic suite to populate evidence.</EmptyState>}</Card>
    </div>
  </>
}
