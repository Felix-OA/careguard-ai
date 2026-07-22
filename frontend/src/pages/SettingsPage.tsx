import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { SystemStatus } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, Disclaimer, ErrorState, Loading, PageHeader } from '../components/UI'

export function SettingsPage() {
  const query = useQuery({ queryKey: ['system-status'], queryFn: () => api.get<SystemStatus>('/dashboard/system-status'), refetchInterval: 30_000 })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const data = query.data!
  return <><PageHeader eyebrow="Local product status" title="System and limitations" description="Safe service health, configuration versions, and the boundary between this demonstration and future productization." /><Disclaimer /><div className="detail-grid"><Card><h2>Service health</h2><div className="service-list">{data.services.map(service => <div key={service.service}><div><strong>{service.service}</strong><span>{service.detail}</span></div><StatusBadge value={service.status} /></div>)}</div></Card><Card><h2>Versioned configuration</h2><dl className="detail-list"><div><dt>Product</dt><dd>{data.product_version}</dd></div><div><dt>Guard mode</dt><dd><StatusBadge value={data.guard_mode ?? 'unavailable'} /></dd></div><div><dt>Policy pack</dt><dd>{data.policy_pack_version}</dd></div><div><dt>Scenario pack</dt><dd>{data.scenario_version}</dd></div></dl></Card><Card className="span-2"><h2>Stage 3 boundaries</h2><div className="limitations-grid"><div><strong>Implemented locally</strong><ul><li>Dashboard aggregation and onboarding</li><li>Fixed-suite audit jobs and comparison</li><li>Sanitized events and reports</li><li>Separate reviewer decisions</li></ul></div><div><strong>Not implemented</strong><ul><li>Production authentication or multi-tenancy</li><li>Real patient-data ingestion</li><li>Cloud hosting, billing, or compliance certification</li><li>Agentic auditing, GOAT, or external scanning</li><li>Signed policy governance or distributed queues</li></ul></div></div></Card></div></>
}
