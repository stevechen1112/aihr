import axios from 'axios'
import type {
  User, Document, ChatRequest, ChatResponse,
  Conversation, Message, UsageSummary, UsageByAction,
  UsageRecord, AuditLog,
} from './types'

const api = axios.create({ baseURL: '/api/v1' })

// ─── Request interceptor: attach JWT ───
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ─── Response interceptor: auto-logout on 401 ───
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
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

// ─── Documents ───
export const docApi = {
  list: () => api.get<Document[]>('/documents/').then(r => r.data),
  get: (id: string) => api.get<Document>(`/documents/${id}`).then(r => r.data),
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<Document>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    }).then(r => r.data)
  },
  delete: (id: string) => api.delete(`/documents/${id}`).then(r => r.data),
}

// ─── Chat ───
export const chatApi = {
  send: (req: ChatRequest) => api.post<ChatResponse>('/chat/chat', req).then(r => r.data),
  conversations: () => api.get<Conversation[]>('/chat/conversations').then(r => r.data),
  messages: (convId: string) => api.get<Message[]>(`/chat/conversations/${convId}/messages`).then(r => r.data),
  deleteConversation: (convId: string) => api.delete(`/chat/conversations/${convId}`).then(r => r.data),
}

// ─── Audit ───
export const auditApi = {
  logs: (params?: Record<string, string>) => api.get<AuditLog[]>('/audit/logs', { params }).then(r => r.data),
  usageSummary: (params?: Record<string, string>) => api.get<UsageSummary>('/audit/usage/summary', { params }).then(r => r.data),
  usageByAction: (params?: Record<string, string>) => api.get<UsageByAction[]>('/audit/usage/by-action', { params }).then(r => r.data),
  usageRecords: (params?: Record<string, string>) => api.get<UsageRecord[]>('/audit/usage/records', { params }).then(r => r.data),
  exportLogs: (format: 'csv' | 'pdf', params?: Record<string, string>) =>
    api.get('/audit/logs/export', { params: { format, ...params }, responseType: 'blob' }).then(r => r.data),
  exportUsage: (format: 'csv' | 'pdf', params?: Record<string, string>) =>
    api.get('/audit/usage/export', { params: { format, ...params }, responseType: 'blob' }).then(r => r.data),
}

// ─── Platform Admin ───
export const adminApi = {
  dashboard: () => api.get('/admin/dashboard').then(r => r.data),
  tenants: (params?: Record<string, string>) => api.get('/admin/tenants', { params }).then(r => r.data),
  tenantStats: (id: string) => api.get(`/admin/tenants/${id}/stats`).then(r => r.data),
  updateTenant: (id: string, data: Record<string, unknown>) => api.put(`/admin/tenants/${id}`, data).then(r => r.data),
  users: (params?: Record<string, string>) => api.get('/admin/users', { params }).then(r => r.data),
  systemHealth: () => api.get('/admin/system/health').then(r => r.data),
  // ─ Quota Management (T3-1) ─
  tenantQuota: (id: string) => api.get(`/admin/tenants/${id}/quota`).then(r => r.data),
  updateQuota: (id: string, data: Record<string, unknown>) => api.put(`/admin/tenants/${id}/quota`, data).then(r => r.data),
  applyPlan: (id: string, plan: string) => api.post(`/admin/tenants/${id}/quota/apply-plan?plan=${plan}`).then(r => r.data),
  tenantAlerts: (id: string) => api.get(`/admin/tenants/${id}/alerts`).then(r => r.data),
  checkAlerts: (id: string) => api.post(`/admin/tenants/${id}/alerts/check`).then(r => r.data),
  quotaPlans: () => api.get('/admin/quota/plans').then(r => r.data),
  // ─ Security Config (T3-3) ─
  tenantSecurity: (id: string) => api.get(`/admin/tenants/${id}/security`).then(r => r.data),
  updateSecurity: (id: string, data: Record<string, unknown>) => api.put(`/admin/tenants/${id}/security`, data).then(r => r.data),
}

// ─── Company Self-Service (T3-2) ───
export const companyApi = {
  dashboard: () => api.get('/company/dashboard').then(r => r.data),
  profile: () => api.get('/company/profile').then(r => r.data),
  quota: () => api.get('/company/quota').then(r => r.data),
  users: () => api.get('/company/users').then(r => r.data),
  inviteUser: (data: { email: string; full_name?: string; role: string; password: string }) =>
    api.post('/company/users/invite', data).then(r => r.data),
  updateUser: (id: string, data: Record<string, unknown>) =>
    api.put(`/company/users/${id}`, data).then(r => r.data),
  deactivateUser: (id: string) => api.delete(`/company/users/${id}`).then(r => r.data),
  usageSummary: () => api.get('/company/usage/summary').then(r => r.data),
  usageByUser: () => api.get('/company/usage/by-user').then(r => r.data),
}

// ─── Cost Analytics (T3-5) ───
export const analyticsApi = {
  dailyTrend: (params?: Record<string, string>) =>
    api.get('/analytics/trends/daily', { params }).then(r => r.data),
  monthlyByTenant: (params?: Record<string, string>) =>
    api.get('/analytics/trends/monthly-by-tenant', { params }).then(r => r.data),
  anomalies: (params?: Record<string, string>) =>
    api.get('/analytics/anomalies', { params }).then(r => r.data),
  budgetAlerts: () => api.get('/analytics/budget-alerts').then(r => r.data),
}

// ─── SSO ───
export const ssoApi = {
  /** Public: get enabled providers for a tenant (no auth required) */
  providers: (tenantId: string) =>
    api.get<{ provider: string; enabled: boolean }[]>(`/auth/sso/providers/${tenantId}`).then(r => r.data),
  /** Public: create signed OAuth state */
  state: (body: { tenant_id: string; provider: string }) =>
    api.post<{ state: string }>('/auth/sso/state', body).then(r => r.data),
  /** Exchange OAuth code for JWT */
  callback: (body: { code: string; redirect_uri: string; tenant_id: string; provider: string; state: string; code_verifier: string }) =>
    api.post<{ access_token: string; token_type: string }>('/auth/sso/callback', body).then(r => r.data),
  /** Admin: list SSO configs (requires auth) */
  listConfigs: () => api.get('/auth/sso/config').then(r => r.data),
  /** Admin: create / upsert SSO config */
  createConfig: (body: Record<string, unknown>) => api.post('/auth/sso/config', body).then(r => r.data),
  /** Admin: update SSO config */
  updateConfig: (provider: string, body: Record<string, unknown>) => api.put(`/auth/sso/config/${provider}`, body).then(r => r.data),
  /** Admin: delete SSO config */
  deleteConfig: (provider: string) => api.delete(`/auth/sso/config/${provider}`).then(r => r.data),
}

export default api
