import { Component, type ReactNode } from 'react'

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() { return { failed: true } }

  componentDidCatch() {
    // Intentionally do not log rendered data or stack traces in the browser.
  }

  render() {
    if (this.state.failed) return <main className="fatal-error"><h1>CareGuard could not render this view</h1><p>No protected details were displayed. Reload the local dashboard or check service status.</p><button className="button button-primary" onClick={() => window.location.assign('/')}>Return to dashboard</button></main>
    return this.props.children
  }
}
