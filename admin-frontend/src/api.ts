import axios from 'axios'
import type { User } from './types'

const api = axios.create({ baseURL: '/api/v1' })

// ─── Request interceptor: attach JWT ───
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ─── Response interceptor: auto-logout on 401 ───
// Don't redirect if already on login page (prevents interference with login flow)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('admin_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// ─── Auth ───
export const authApi = {
  login: async (email: string, password: string) => {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', password)
    const { data } = await api.post<{ access_token: string }>('/auth/login/access-token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  me: () => api.get<User>('/users/me').then(r => r.data),
}

// ─── Platform Admin ───
export const adminApi = {
  dashboard: () => api.get('/admin/dashboard').then(r => r.data),
  tenants: (params?: Record<string, string>) => api.get('/admin/tenants', { params }).then(r => r.data),
  tenantStats: (id: string) => api.get(`/admin/tenants/${id}/stats`).then(r => r.data),
  updateTenant: (id: string, data: Record<string, unknown>) => api.put(`/admin/tenants/${id}`, data).then(r => r.data),
  users: (params?: Record<string, string>) => api.get('/admin/users', { params }).then(r => r.data),
  systemHealth: () => api.get('/admin/system/health').then(r => r.data),
  // ─ Quota Management ─
  tenantQuota: (id: string) => api.get(`/admin/tenants/${id}/quota`).then(r => r.data),
  updateQuota: (id: string, data: Record<string, unknown>) => api.put(`/admin/tenants/${id}/quota`, data).then(r => r.data),
  applyPlan: (id: string, plan: string) => api.post(`/admin/tenants/${id}/quota/apply-plan?plan=${plan}`).then(r => r.data),
  tenantAlerts: (id: string) => api.get(`/admin/tenants/${id}/alerts`).then(r => r.data),
  checkAlerts: (id: string) => api.post(`/admin/tenants/${id}/alerts/check`).then(r => r.data),
  quotaPlans: () => api.get('/admin/quota/plans').then(r => r.data),
  // ─ Security Config ─
  tenantSecurity: (id: string) => api.get(`/admin/tenants/${id}/security`).then(r => r.data),
  updateSecurity: (id: string, data: Record<string, unknown>) => api.put(`/admin/tenants/${id}/security`, data).then(r => r.data),
}

// ─── Cost Analytics ───
export const analyticsApi = {
  dailyTrend: (params?: Record<string, string>) =>
    api.get('/analytics/trends/daily', { params }).then(r => r.data),
  monthlyByTenant: (params?: Record<string, string>) =>
    api.get('/analytics/trends/monthly-by-tenant', { params }).then(r => r.data),
  anomalies: (params?: Record<string, string>) =>
    api.get('/analytics/anomalies', { params }).then(r => r.data),
  budgetAlerts: () => api.get('/analytics/budget-alerts').then(r => r.data),
}

export default api
