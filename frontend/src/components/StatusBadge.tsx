const statusClass = (value: string) => {
  if (['PASS', 'ALLOW', 'healthy', 'completed', 'CONFIRMED_SAFE'].includes(value)) return 'status-good'
  if (['FAIL', 'BLOCK', 'failed', 'unavailable', 'CONFIRMED_FINDING'].includes(value)) return 'status-bad'
  if (['REVIEW', 'ESCALATE', 'REQUIRE_HUMAN_REVIEW', 'NEEDS_MORE_CONTEXT'].includes(value)) return 'status-review'
  if (['PARTIAL', 'REDACT', 'REQUIRE_CONFIRMATION', 'ALLOW_WITH_WARNING', 'degraded', 'running'].includes(value)) return 'status-warn'
  return 'status-neutral'
}

export function StatusBadge({ value }: { value: string }) {
  return <span className={`status-badge ${statusClass(value)}`} aria-label={`Status: ${value.replaceAll('_', ' ')}`}><span aria-hidden="true" className="status-dot" />{value.replaceAll('_', ' ')}</span>
}
