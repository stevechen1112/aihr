import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import { BrandingProvider } from './contexts/BrandingContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import UsagePage from './pages/UsagePage'
import AuditLogsPage from './pages/AuditLogsPage'
import DepartmentsPage from './pages/DepartmentsPage'
import CompanyPage from './pages/CompanyPage'
import SSOCallbackPage from './pages/SSOCallbackPage'
import SSOSettingsPage from './pages/SSOSettingsPage'
import BrandingPage from './pages/BrandingPage'
import SubscriptionPage from './pages/SubscriptionPage'
import CustomDomainsPage from './pages/CustomDomainsPage'
import RegionsPage from './pages/RegionsPage'
import MyUsagePage from './pages/MyUsagePage'
import RAGDashboardPage from './pages/RAGDashboardPage'
import QualityDashboardPage from './pages/QualityDashboardPage'
import PrivacyPage from './pages/PrivacyPage'
import TermsPage from './pages/TermsPage'
import AcceptInvitePage from './pages/AcceptInvitePage'
import LandingPage from './pages/LandingPage'
import PricingPage from './pages/PricingPage'
import SignupPage from './pages/SignupPage'
import VerifyEmailPage from './pages/VerifyEmailPage'

const legacyAppRoutes = [
  'documents',
  'my-usage',
  'usage',
  'audit',
  'departments',
  'company',
  'sso-settings',
  'branding',
  'subscription',
  'custom-domains',
  'rag-dashboard',
  'quality-dashboard',
  'regions',
] as const

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth()
  if (loading) return <div className="flex h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" /></div>
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RoleGuard({ children, roles }: { children: React.ReactNode; roles: string[] }) {
  const { user } = useAuth()
  if (!user || !roles.includes(user.role)) return <Navigate to="/app" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { token } = useAuth()
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/welcome" element={<Navigate to="/" replace />} />
      <Route path="/pricing" element={<PricingPage />} />
      <Route path="/signup" element={token ? <Navigate to="/app" replace /> : <SignupPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/login" element={token ? <Navigate to="/app" replace /> : <LoginPage />} />
      <Route path="/login/callback" element={<SSOCallbackPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />
      {legacyAppRoutes.map((path) => (
        <Route
          key={path}
          path={`/${path}`}
          element={<Navigate to={`/app/${path}`} replace />}
        />
      ))}
      <Route path="/app" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<ChatPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="my-usage" element={<MyUsagePage />} />
        <Route path="usage" element={<RoleGuard roles={['owner', 'admin']}><UsagePage /></RoleGuard>} />
        <Route path="audit" element={<RoleGuard roles={['owner', 'admin']}><AuditLogsPage /></RoleGuard>} />
        <Route path="departments" element={<RoleGuard roles={['owner', 'admin', 'hr']}><DepartmentsPage /></RoleGuard>} />
        <Route path="company" element={<RoleGuard roles={['owner', 'admin']}><CompanyPage /></RoleGuard>} />
        <Route path="sso-settings" element={<RoleGuard roles={['owner', 'admin']}><SSOSettingsPage /></RoleGuard>} />
        <Route path="branding" element={<RoleGuard roles={['owner', 'admin']}><BrandingPage /></RoleGuard>} />
        <Route path="subscription" element={<RoleGuard roles={['owner', 'admin']}><SubscriptionPage /></RoleGuard>} />
        <Route path="custom-domains" element={<RoleGuard roles={['owner', 'admin']}><CustomDomainsPage /></RoleGuard>} />
        <Route path="rag-dashboard" element={<RoleGuard roles={['owner', 'admin', 'hr']}><RAGDashboardPage /></RoleGuard>} />
        <Route path="quality-dashboard" element={<RoleGuard roles={['owner', 'admin']}><QualityDashboardPage /></RoleGuard>} />
        <Route path="regions" element={<RoleGuard roles={['owner', 'admin']}><RegionsPage /></RoleGuard>} />
      </Route>
      <Route path="*" element={token ? <Navigate to="/app" replace /> : <Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrandingProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrandingProvider>
  )
}
