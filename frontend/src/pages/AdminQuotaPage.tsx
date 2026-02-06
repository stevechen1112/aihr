import { useState, useEffect } from 'react'
import { adminApi } from '../api'
import {
  Loader2, AlertCircle, Gauge, Shield, Building2,
  Save, RotateCcw, ChevronRight, ChevronLeft,
  AlertTriangle, CheckCircle2, Bell,
} from 'lucide-react'

type View = 'list' | 'detail'

// ─── Shared ───
function Loader() {
  return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
}
function Empty({ text }: { text: string }) {
  return <div className="flex flex-col items-center py-16 text-gray-400"><AlertCircle className="mb-3 h-10 w-10" /><p className="text-sm">{text}</p></div>
}

function UsageBar({ label, current, limit, ratio }: { label: string; current: number; limit: number | null; ratio: number | null }) {
  const pct = ratio != null ? Math.min(ratio * 100, 100) : 0
  const color = ratio == null ? 'bg-gray-200' : ratio >= 1 ? 'bg-red-500' : ratio >= 0.8 ? 'bg-amber-500' : 'bg-blue-500'
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{current.toLocaleString()} / {limit != null ? limit.toLocaleString() : '∞'}</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${limit != null ? pct : 0}%` }} />
      </div>
    </div>
  )
}

// ═══ Tenant List (with quota summary) ═══
function TenantListView({ onSelect }: { onSelect: (id: string, name: string) => void }) {
  const [tenants, setTenants] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.tenants().then(setTenants).catch(() => []).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader />
  if (tenants.length === 0) return <Empty text="無租戶資料" />

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            <th className="px-5 py-3">租戶</th>
            <th className="px-5 py-3">方案</th>
            <th className="px-5 py-3">狀態</th>
            <th className="px-5 py-3 text-right">用戶</th>
            <th className="px-5 py-3 text-right">文件</th>
            <th className="px-5 py-3 text-right">API 呼叫</th>
            <th className="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {tenants.map((t: any) => (
            <tr key={t.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => onSelect(t.id, t.name)}>
              <td className="px-5 py-3 text-sm font-medium text-gray-900">{t.name}</td>
              <td className="px-5 py-3">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                  t.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
                  t.plan === 'pro' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-700'
                }`}>{t.plan || 'free'}</span>
              </td>
              <td className="px-5 py-3">
                <span className={`inline-flex items-center gap-1 text-xs font-medium ${t.status === 'active' ? 'text-green-600' : 'text-red-500'}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${t.status === 'active' ? 'bg-green-500' : 'bg-red-400'}`} />
                  {t.status}
                </span>
              </td>
              <td className="px-5 py-3 text-right text-sm text-gray-600">{t.user_count}</td>
              <td className="px-5 py-3 text-right text-sm text-gray-600">{t.document_count}</td>
              <td className="px-5 py-3 text-right text-sm text-gray-600">{t.total_actions}</td>
              <td className="px-5 py-3"><ChevronRight className="h-4 w-4 text-gray-400" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ═══ Tenant Detail — Quota + Security ═══
function TenantDetailView({ tenantId, tenantName, onBack }: { tenantId: string; tenantName: string; onBack: () => void }) {
  const [tab, setTab] = useState<'quota' | 'security' | 'alerts'>('quota')
  return (
    <div className="space-y-4">
      <button onClick={onBack} className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
        <ChevronLeft className="h-4 w-4" /> 返回租戶列表
      </button>
      <div className="flex items-center gap-3">
        <Building2 className="h-5 w-5 text-gray-400" />
        <h2 className="text-lg font-bold text-gray-900">{tenantName}</h2>
      </div>
      <div className="flex gap-1 border-b border-gray-200 pb-px">
        {([
          { key: 'quota' as const, label: '配額管理', icon: Gauge },
          { key: 'security' as const, label: '安全設定', icon: Shield },
          { key: 'alerts' as const, label: '告警記錄', icon: Bell },
        ]).map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>
      {tab === 'quota' && <QuotaTab tenantId={tenantId} />}
      {tab === 'security' && <SecurityTab tenantId={tenantId} />}
      {tab === 'alerts' && <AlertsTab tenantId={tenantId} />}
    </div>
  )
}

// ─── Quota Tab ───
function QuotaTab({ tenantId }: { tenantId: string }) {
  const [quota, setQuota] = useState<any>(null)
  const [plans, setPlans] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([adminApi.tenantQuota(tenantId), adminApi.quotaPlans()])
      .then(([q, p]) => { setQuota(q); setPlans(p); setForm({
        max_users: String(q.max_users ?? ''),
        max_documents: String(q.max_documents ?? ''),
        max_storage_mb: String(q.max_storage_mb ?? ''),
        monthly_query_limit: String(q.monthly_query_limit ?? ''),
        monthly_token_limit: String(q.monthly_token_limit ?? ''),
        quota_alert_threshold: String(q.quota_alert_threshold ?? '0.8'),
      }) })
      .catch(() => null)
      .finally(() => setLoading(false))
  }

  useEffect(load, [tenantId])

  const handleSave = async () => {
    setSaving(true)
    setMsg('')
    try {
      const body: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(form)) {
        if (v === '') body[k] = null
        else if (k === 'quota_alert_threshold') body[k] = parseFloat(v)
        else body[k] = parseInt(v, 10)
      }
      const updated = await adminApi.updateQuota(tenantId, body)
      setQuota(updated)
      setMsg('配額已更新')
    } catch { setMsg('更新失敗') }
    finally { setSaving(false) }
  }

  const handleApplyPlan = async (plan: string) => {
    setSaving(true)
    setMsg('')
    try {
      await adminApi.applyPlan(tenantId, plan)
      load()
      setMsg(`已套用 ${plan} 方案`)
    } catch { setMsg('套用失敗') }
    finally { setSaving(false) }
  }

  if (loading) return <Loader />
  if (!quota) return <Empty text="無法載入配額" />

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Current usage */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700">目前使用狀況</h3>
        <UsageBar label="使用者" current={quota.current_users} limit={quota.max_users} ratio={quota.users_usage_ratio} />
        <UsageBar label="文件" current={quota.current_documents} limit={quota.max_documents} ratio={quota.documents_usage_ratio} />
        <UsageBar label="儲存空間 (MB)" current={quota.current_storage_mb} limit={quota.max_storage_mb} ratio={quota.storage_usage_ratio} />
        <UsageBar label="月查詢" current={quota.current_monthly_queries} limit={quota.monthly_query_limit} ratio={quota.queries_usage_ratio} />
        <UsageBar label="月 Token" current={quota.current_monthly_tokens} limit={quota.monthly_token_limit} ratio={quota.tokens_usage_ratio} />
        {quota.is_over_quota && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>{quota.quota_warnings.map((w: string, i: number) => <p key={i}>{w}</p>)}</div>
          </div>
        )}
      </div>

      {/* Edit form */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">配額設定</h3>
          {plans && (
            <div className="flex gap-1">
              {Object.keys(plans).map((p: string) => (
                <button
                  key={p}
                  onClick={() => handleApplyPlan(p)}
                  disabled={saving}
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                    quota.plan === p ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>

        {([
          { key: 'max_users', label: '使用者上限' },
          { key: 'max_documents', label: '文件上限' },
          { key: 'max_storage_mb', label: '儲存空間 (MB)' },
          { key: 'monthly_query_limit', label: '月查詢上限' },
          { key: 'monthly_token_limit', label: '月 Token 上限' },
          { key: 'quota_alert_threshold', label: '告警閾值 (0~1)' },
        ]).map(f => (
          <div key={f.key}>
            <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
            <input
              type="number"
              placeholder="不限制"
              value={form[f.key] ?? ''}
              onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        ))}

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> 儲存
          </button>
          <button
            onClick={load}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RotateCcw className="h-4 w-4" /> 重設
          </button>
          {msg && <span className="text-sm text-green-600">{msg}</span>}
        </div>
      </div>
    </div>
  )
}

// ─── Security Tab ───
function SecurityTab({ tenantId }: { tenantId: string }) {
  const [, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    isolation_level: 'standard',
    require_mfa: false,
    ip_whitelist: '',
    data_retention_days: '',
    encryption_key_id: '',
  })
  const [msg, setMsg] = useState('')

  useEffect(() => {
    adminApi.tenantSecurity(tenantId)
      .then(c => {
        setConfig(c)
        setForm({
          isolation_level: c.isolation_level || 'standard',
          require_mfa: c.require_mfa || false,
          ip_whitelist: c.ip_whitelist || '',
          data_retention_days: c.data_retention_days != null ? String(c.data_retention_days) : '',
          encryption_key_id: c.encryption_key_id || '',
        })
      })
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [tenantId])

  const handleSave = async () => {
    setSaving(true)
    setMsg('')
    try {
      const body: Record<string, unknown> = {
        isolation_level: form.isolation_level,
        require_mfa: form.require_mfa,
        ip_whitelist: form.ip_whitelist || null,
        data_retention_days: form.data_retention_days ? parseInt(form.data_retention_days, 10) : null,
        encryption_key_id: form.encryption_key_id || null,
      }
      const updated = await adminApi.updateSecurity(tenantId, body)
      setConfig(updated)
      setMsg('安全設定已更新')
    } catch { setMsg('更新失敗') }
    finally { setSaving(false) }
  }

  if (loading) return <Loader />

  const levels = ['standard', 'enhanced', 'dedicated']

  return (
    <div className="max-w-lg rounded-xl border border-gray-200 bg-white p-5 space-y-5">
      <h3 className="text-sm font-semibold text-gray-700">安全隔離設定</h3>

      {/* Isolation level */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-2">隔離等級</label>
        <div className="flex gap-2">
          {levels.map(l => (
            <button
              key={l}
              onClick={() => setForm(prev => ({ ...prev, isolation_level: l }))}
              className={`flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
                form.isolation_level === l
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {l === 'standard' && '🔵 標準'}
              {l === 'enhanced' && '🟡 加強'}
              {l === 'dedicated' && '🔴 專屬'}
            </button>
          ))}
        </div>
      </div>

      {/* MFA */}
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={form.require_mfa}
          onChange={e => setForm(p => ({ ...p, require_mfa: e.target.checked }))}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <span className="text-sm text-gray-700">要求多因子驗證 (MFA)</span>
      </label>

      {/* IP whitelist */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">IP 白名單（逗號分隔）</label>
        <input
          type="text"
          placeholder="例: 192.168.1.0/24, 10.0.0.0/8"
          value={form.ip_whitelist}
          onChange={e => setForm(p => ({ ...p, ip_whitelist: e.target.value }))}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Retention */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">資料保留天數</label>
        <input
          type="number"
          placeholder="不限"
          value={form.data_retention_days}
          onChange={e => setForm(p => ({ ...p, data_retention_days: e.target.value }))}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Encryption key */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">加密金鑰 ID</label>
        <input
          type="text"
          placeholder="（選填）"
          value={form.encryption_key_id}
          onChange={e => setForm(p => ({ ...p, encryption_key_id: e.target.value }))}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <Save className="h-4 w-4" /> 儲存設定
        </button>
        {msg && <span className="text-sm text-green-600">{msg}</span>}
      </div>
    </div>
  )
}

// ─── Alerts Tab ───
function AlertsTab({ tenantId }: { tenantId: string }) {
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)

  const load = () => {
    setLoading(true)
    adminApi.tenantAlerts(tenantId).then(setAlerts).catch(() => []).finally(() => setLoading(false))
  }

  useEffect(load, [tenantId])

  const handleCheck = async () => {
    setChecking(true)
    try {
      await adminApi.checkAlerts(tenantId)
      load()
    } catch { /* noop */ }
    finally { setChecking(false) }
  }

  if (loading) return <Loader />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">配額告警記錄</h3>
        <button
          onClick={handleCheck}
          disabled={checking}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <Bell className="h-3.5 w-3.5" /> {checking ? '檢查中...' : '立即檢查'}
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-green-400 mb-3" />
          <p className="text-sm text-gray-500">目前無告警記錄</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">時間</th>
                <th className="px-5 py-3">類型</th>
                <th className="px-5 py-3">資源</th>
                <th className="px-5 py-3">訊息</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {alerts.map((a: any, i: number) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-5 py-2 text-xs text-gray-500 whitespace-nowrap">{a.created_at ? new Date(a.created_at).toLocaleString('zh-TW') : '—'}</td>
                  <td className="px-5 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      a.alert_type === 'exceeded' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                    }`}>{a.alert_type === 'exceeded' ? '超額' : '預警'}</span>
                  </td>
                  <td className="px-5 py-2 text-sm text-gray-700">{a.resource || '—'}</td>
                  <td className="px-5 py-2 text-sm text-gray-600">{a.message || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ═══ Main Page ═══
export default function AdminQuotaPage() {
  const [view, setView] = useState<View>('list')
  const [selectedId, setSelectedId] = useState('')
  const [selectedName, setSelectedName] = useState('')

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-2">
          <Gauge className="h-5 w-5 text-orange-600" />
          <h1 className="text-lg font-semibold text-gray-900">配額與安全管理</h1>
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Superuser</span>
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {view === 'list' && (
          <TenantListView onSelect={(id, name) => { setSelectedId(id); setSelectedName(name); setView('detail') }} />
        )}
        {view === 'detail' && (
          <TenantDetailView tenantId={selectedId} tenantName={selectedName} onBack={() => setView('list')} />
        )}
      </div>
    </div>
  )
}
