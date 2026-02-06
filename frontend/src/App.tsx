import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import UsagePage from './pages/UsagePage'
import AuditLogsPage from './pages/AuditLogsPage'
import DepartmentsPage from './pages/DepartmentsPage'
import AdminPage from './pages/AdminPage'
import AdminQuotaPage from './pages/AdminQuotaPage'
import CompanyPage from './pages/CompanyPage'
import AnalyticsPage from './pages/AnalyticsPage'
import SSOCallbackPage from './pages/SSOCallbackPage'
import SSOSettingsPage from './pages/SSOSettingsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth()
  if (loading) return <div className="flex h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" /></div>
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { token } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={token ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/login/callback" element={<SSOCallbackPage />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<ChatPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="usage" element={<UsagePage />} />
        <Route path="audit" element={<AuditLogsPage />} />
        <Route path="departments" element={<DepartmentsPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="admin/quotas" element={<AdminQuotaPage />} />
        <Route path="company" element={<CompanyPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="sso-settings" element={<SSOSettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
