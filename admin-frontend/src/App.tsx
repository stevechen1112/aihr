import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import AdminQuotaPage from './pages/AdminQuotaPage'
import AnalyticsPage from './pages/AnalyticsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading, user } = useAuth()
  if (loading) return <div className="flex h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-red-600 border-t-transparent" /></div>
  if (!token || !user?.is_superuser) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { token, user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={token && user?.is_superuser ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<AdminPage />} />
        <Route path="quotas" element={<AdminQuotaPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
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
