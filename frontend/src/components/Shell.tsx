import { NavLink, Outlet, useLocation } from 'react-router-dom'

const navigation = [
  ['/', 'Overview', '⌂'], ['/onboarding', 'Onboarding', '＋'], ['/targets', 'Targets', '◎'],
  ['/audits', 'Audits', '◫'], ['/comparisons', 'Comparisons', '⇄'], ['/events', 'Guard events', '◇'],
  ['/agentic', 'Agentic audit', '◈'], ['/reviews', 'Human review', '◌'], ['/policies', 'Policies', '▦'], ['/reports', 'Reports', '▤'],
  ['/demo', 'Synthetic demo', '▷'], ['/settings', 'System', '⚙'],
]

export function Shell() {
  const location = useLocation()
  const current = navigation.find(([path]) => path === '/' ? location.pathname === '/' : location.pathname.startsWith(path))
  return <div className="app-shell">
    <aside className="sidebar" aria-label="Primary navigation">
      <NavLink to="/" className="brand" aria-label="CareGuard AI dashboard"><span className="brand-mark">CG</span><span><strong>CareGuard</strong><small>AI Security</small></span></NavLink>
      <nav>{navigation.map(([path, label, icon]) => <NavLink key={path} to={path} end={path === '/'}><span aria-hidden="true">{icon}</span>{label}</NavLink>)}</nav>
      <div className="sidebar-foot"><span className="live-dot" aria-hidden="true" /> Local environment<small>Stage 4 · v0.4.0</small></div>
    </aside>
    <div className="app-main">
      <header className="topbar"><div><span>CareGuard</span><span aria-hidden="true">/</span><strong>{current?.[1] ?? 'Detail'}</strong></div><NavLink to="/reviews" className="review-link">Review queue</NavLink></header>
      <main id="main-content" tabIndex={-1}><Outlet /></main>
    </div>
  </div>
}
