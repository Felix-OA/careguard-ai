import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { PolicyCoverage } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, ErrorState, Loading, PageHeader } from '../components/UI'

export function PoliciesPage() {
  const query = useQuery({ queryKey: ['policies'], queryFn: () => api.get<PolicyCoverage[]>('/dashboard/policies') })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  return <><PageHeader eyebrow="Healthcare policy pack" title="15 policies, traceable to controls" description="Immutable IDs, versioned local enablement, mapped reason codes, scenario coverage, and bounded remediation guidance." /><div className="policy-grid">{query.data!.map(item => <Link className="card policy-card" to={`/policies/${item.policy.policy_id}`} key={item.policy.policy_id}><div><code>{item.policy.policy_id}</code><StatusBadge value={item.enabled ? 'ALLOW' : 'disabled'} /></div><h2>{item.policy.title}</h2><p>{item.policy.description}</p><dl><div><dt>Severity</dt><dd>{item.policy.severity}</dd></div><div><dt>Scenarios</dt><dd>{item.scenario_ids.length}</dd></div><div><dt>Reason codes</dt><dd>{item.mapped_reason_codes.length}</dd></div></dl></Link>)}</div></>
}

export function PolicyDetailPage() {
  const { policyId = '' } = useParams()
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['policy', policyId], queryFn: () => api.get<PolicyCoverage>(`/dashboard/policies/${policyId}`) })
  const toggle = useMutation({ mutationFn: (enabled: boolean) => api.put<PolicyCoverage>(`/dashboard/policies/${policyId}`, { enabled }), onSuccess: () => { client.invalidateQueries({ queryKey: ['policy', policyId] }); client.invalidateQueries({ queryKey: ['policies'] }); client.invalidateQueries({ queryKey: ['dashboard'] }) } })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const item = query.data!
  return <><PageHeader eyebrow={item.policy.policy_id} title={item.policy.title} description={item.policy.description} action={<button className="button" onClick={() => toggle.mutate(!item.enabled)}>{item.enabled ? 'Disable locally' : 'Enable locally'}</button>} /><div className="detail-grid"><Card><h2>Expected behaviour</h2><p>{item.policy.expected_behavior}</p><h3>Applicable roles</h3><div className="tag-list">{item.policy.applicable_roles.map(value => <span key={value}>{value}</span>)}</div><h3>Failure indicators</h3><ul>{item.policy.failure_indicators.map(value => <li key={value}>{value}</li>)}</ul></Card><Card><h2>Control coverage</h2><ul>{item.control_coverage.map(value => <li key={value}>{value}</li>)}</ul><h3>Mapped reason codes</h3><div className="tag-list">{item.mapped_reason_codes.map(value => <span key={value}>{value}</span>)}</div><h3>Scenario coverage</h3><div className="tag-list">{item.scenario_ids.map(value => <span key={value}>{value}</span>)}</div></Card><Card className="span-2"><h2>Remediation guidance</h2><p>{item.policy.remediation_guidance}</p><div className="alert alert-info"><strong>Configuration governance</strong><span>Version {item.configuration_version}. Stage 3 records local changes but does not provide signing, approvals, or production policy governance.</span></div></Card></div></>
}
