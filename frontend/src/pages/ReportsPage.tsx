import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ReportMetadata, SafeReport } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Card, EmptyState, ErrorState, Loading, PageHeader, SafeMarkdown } from '../components/UI'

export function ReportsPage() {
  const query = useQuery({ queryKey: ['reports'], queryFn: () => api.get<ReportMetadata[]>('/dashboard/reports') })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  return <><PageHeader eyebrow="Sanitized exports" title="Reports" description="Preview backend-generated Markdown or download validated JSON without exposing local file paths." />{query.data!.length ? <div className="report-grid">{query.data!.map(item => <Link className="card report-card" to={`/reports/${item.report_type}/${item.report_id}`} key={`${item.report_type}-${item.report_id}`}><div><span className="report-icon" aria-hidden="true">▤</span><StatusBadge value={item.report_type} /></div><h2>{item.title}</h2><p>{item.report_id}</p><span>{new Date(item.created_at).toLocaleString()}</span></Link>)}</div> : <EmptyState title="No reports available">Complete an audit or comparison to generate a safe preview.</EmptyState>}</>
}

export function ReportDetailPage() {
  const { reportType = '', reportId = '' } = useParams()
  const query = useQuery({ queryKey: ['report', reportType, reportId], queryFn: () => api.get<SafeReport>(`/dashboard/reports/${reportType}/${reportId}`) })
  if (query.isLoading) return <Loading />
  if (query.error) return <ErrorState error={query.error} />
  const report = query.data!
  const download = (type: 'md' | 'json') => { const content = type === 'md' ? report.markdown : JSON.stringify(report.json_content, null, 2); const blob = new Blob([content], { type: type === 'md' ? 'text/markdown' : 'application/json' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${report.metadata.report_id}.${type}`; anchor.click(); URL.revokeObjectURL(url) }
  return <><PageHeader eyebrow={report.metadata.report_type} title={report.metadata.title} description={`${report.metadata.report_id} · ${new Date(report.metadata.created_at).toLocaleString()}`} action={<div className="button-row"><button className="button" onClick={() => navigator.clipboard.writeText(report.markdown)}>Copy safe summary</button><button className="button" onClick={() => download('md')}>Download Markdown</button><button className="button button-primary" onClick={() => download('json')}>Download JSON</button></div>} /><div className="report-boundaries">{report.boundaries.map(item => <span key={item}>{item}</span>)}</div><Card className="report-preview"><SafeMarkdown content={report.markdown} /></Card></>
}
