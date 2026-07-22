import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from '../components/Shell'
import { Loading } from '../components/UI'
import { ErrorBoundary } from '../components/ErrorBoundary'

const DashboardPage = lazy(() => import('../pages/DashboardPage').then(module => ({ default: module.DashboardPage })))
const OnboardingPage = lazy(() => import('../pages/OnboardingPage').then(module => ({ default: module.OnboardingPage })))
const TargetsPage = lazy(() => import('../pages/TargetsPage').then(module => ({ default: module.TargetsPage })))
const TargetDetailPage = lazy(() => import('../pages/TargetsPage').then(module => ({ default: module.TargetDetailPage })))
const AuditsPage = lazy(() => import('../pages/AuditsPage').then(module => ({ default: module.AuditsPage })))
const AuditRunPage = lazy(() => import('../pages/AuditsPage').then(module => ({ default: module.AuditRunPage })))
const AuditDetailPage = lazy(() => import('../pages/AuditsPage').then(module => ({ default: module.AuditDetailPage })))
const ComparisonsPage = lazy(() => import('../pages/ComparisonsPage').then(module => ({ default: module.ComparisonsPage })))
const ComparisonDetailPage = lazy(() => import('../pages/ComparisonsPage').then(module => ({ default: module.ComparisonDetailPage })))
const EventsPage = lazy(() => import('../pages/EventsPage').then(module => ({ default: module.EventsPage })))
const EventDetailPage = lazy(() => import('../pages/EventsPage').then(module => ({ default: module.EventDetailPage })))
const ReviewsPage = lazy(() => import('../pages/ReviewsPage').then(module => ({ default: module.ReviewsPage })))
const PoliciesPage = lazy(() => import('../pages/PoliciesPage').then(module => ({ default: module.PoliciesPage })))
const PolicyDetailPage = lazy(() => import('../pages/PoliciesPage').then(module => ({ default: module.PolicyDetailPage })))
const ReportsPage = lazy(() => import('../pages/ReportsPage').then(module => ({ default: module.ReportsPage })))
const ReportDetailPage = lazy(() => import('../pages/ReportsPage').then(module => ({ default: module.ReportDetailPage })))
const DemoPage = lazy(() => import('../pages/DemoPage').then(module => ({ default: module.DemoPage })))
const SettingsPage = lazy(() => import('../pages/SettingsPage').then(module => ({ default: module.SettingsPage })))

export function App() {
  return <ErrorBoundary><Suspense fallback={<Loading />}><Routes><Route element={<Shell />}>
    <Route index element={<DashboardPage />} />
    <Route path="onboarding" element={<OnboardingPage />} />
    <Route path="targets" element={<TargetsPage />} /><Route path="targets/:targetId" element={<TargetDetailPage />} />
    <Route path="audits" element={<AuditsPage />} /><Route path="audits/new" element={<AuditRunPage />} /><Route path="audits/:runId" element={<AuditDetailPage />} />
    <Route path="comparisons" element={<ComparisonsPage />} /><Route path="comparisons/:comparisonId" element={<ComparisonDetailPage />} />
    <Route path="events" element={<EventsPage />} /><Route path="events/:eventId" element={<EventDetailPage />} />
    <Route path="reviews" element={<ReviewsPage />} />
    <Route path="policies" element={<PoliciesPage />} /><Route path="policies/:policyId" element={<PolicyDetailPage />} />
    <Route path="reports" element={<ReportsPage />} /><Route path="reports/:reportType/:reportId" element={<ReportDetailPage />} />
    <Route path="demo" element={<DemoPage />} /><Route path="settings" element={<SettingsPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route></Routes></Suspense></ErrorBoundary>
}
