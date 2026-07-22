import type { ReactNode } from 'react'

export function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: ReactNode }) {
  return <header className="page-header"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1><p>{description}</p></div>{action && <div className="page-action">{action}</div>}</header>
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`card ${className}`}>{children}</section> }
export function Metric({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) { return <Card className="metric-card"><p>{label}</p><strong>{value}</strong>{hint && <small>{hint}</small>}</Card> }
export function EmptyState({ title, children }: { title: string; children: ReactNode }) { return <div className="empty-state"><span aria-hidden="true">◇</span><h2>{title}</h2><p>{children}</p></div> }
export function Loading({ label = 'Loading CareGuard data' }: { label?: string }) { return <div className="loading" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" />{label}</div> }
export function ErrorState({ error }: { error: Error }) { return <div className="alert alert-error" role="alert"><strong>Unable to load this view.</strong><span>{error.message} Retry the action or check the System page for local service health.</span></div> }
export function Disclaimer() { return <div className="disclaimer" role="note"><strong>Synthetic local evaluation environment.</strong> Not clinical validation, compliance certification, or a production security guarantee.</div> }

export function SafeMarkdown({ content }: { content: string }) {
  return <article className="markdown-preview">{content.split('\n').map((line, index) => {
    if (line.startsWith('### ')) return <h3 key={index}>{line.slice(4)}</h3>
    if (line.startsWith('## ')) return <h2 key={index}>{line.slice(3)}</h2>
    if (line.startsWith('# ')) return <h1 key={index}>{line.slice(2)}</h1>
    if (line.startsWith('- ')) return <p className="markdown-list" key={index}>• {line.slice(2)}</p>
    if (line.startsWith('|')) return <pre key={index}>{line}</pre>
    return line ? <p key={index}>{line}</p> : <br key={index} />
  })}</article>
}
