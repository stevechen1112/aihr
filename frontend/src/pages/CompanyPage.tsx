import { useState, useEffect, useCallback } from 'react'
import { companyApi } from '../api'
import {
  Loader2, AlertCircle, Building2, Users, FileText,
  MessageSquare, Gauge, UserPlus, MoreVertical,
  BarChart3, ChevronDown, CheckCircle2, AlertTriangle,
  Mail, Eye, EyeOff,
} from 'lucide-react'

type Tab = 'dashboard' | 'users' | 'quota' | 'usage'

// ─── Shared ───
function Loader() {
  return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
}
function Empty({ text }: { text: string }) {
  return <div className="flex flex-col items-center py-16 text-gray-400"><AlertCircle className="mb-3 h-10 w-10" /><p className="text-sm">{text}</p></div>
}
function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Users; label: string; value: string | number; sub?: string; color: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500">{label}</p>
          <p className="text-xl font-bold text-gray-900">{value}</p>
          {sub && <p className="text-xs text-gray-400">{sub}</p>}
        </div>
      </div>
    </div>
  )
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

// ═══ Dashboard Tab ═══
function DashboardTab() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    companyApi.dashboard().then(setData).catch(() => null).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader />
  if (!data) return <Empty text="無法載入儀表板" />

  const qs = data.quota_status

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users} label="員工人數" value={data.user_count} color="bg-blue-50 text-blue-600" />
        <StatCard icon={FileText} label="文件數" value={data.document_count} color="bg-green-50 text-green-600" />
        <StatCard icon={MessageSquare} label="對話數" value={data.conversation_count} color="bg-purple-50 text-purple-600" />
        <StatCard icon={BarChart3} label="本月查詢" value={data.monthly_queries} sub={`費用: $${(data.monthly_cost || 0).toFixed(4)}`} color="bg-amber-50 text-amber-600" />
      </div>

      {/* Quota overview */}
      {qs && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Gauge className="h-4 w-4" /> 配額使用狀況
            </h3>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
              qs.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
              qs.plan === 'pro' ? 'bg-blue-100 text-blue-700' :
              'bg-gray-100 text-gray-700'
            }`}>{qs.plan || 'free'} 方案</span>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <UsageBar label="使用者" current={qs.current_users} limit={qs.max_users} ratio={qs.users_usage_ratio} />
            <UsageBar label="文件" current={qs.current_documents} limit={qs.max_documents} ratio={qs.documents_usage_ratio} />
            <UsageBar label="月查詢" current={qs.current_monthly_queries} limit={qs.monthly_query_limit} ratio={qs.queries_usage_ratio} />
            <UsageBar label="月 Token" current={qs.current_monthly_tokens} limit={qs.monthly_token_limit} ratio={qs.tokens_usage_ratio} />
          </div>
          {qs.is_over_quota && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>{qs.quota_warnings?.map((w: string, i: number) => <p key={i}>{w}</p>)}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ═══ Users Tab ═══
function UsersTab() {
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showInvite, setShowInvite] = useState(false)
  const [inviteForm, setInviteForm] = useState({ email: '', full_name: '', role: 'employee', password: '' })
  const [showPw, setShowPw] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editRole, setEditRole] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    companyApi.users().then(setUsers).catch(() => []).finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setMsg('')
    try {
      await companyApi.inviteUser(inviteForm)
      setInviteForm({ email: '', full_name: '', role: 'employee', password: '' })
      setShowInvite(false)
      setMsg('已邀請使用者')
      load()
    } catch (err: any) {
      setMsg(err.response?.data?.detail || '邀請失敗')
    }
    finally { setSubmitting(false) }
  }

  const handleUpdateRole = async (userId: string) => {
    try {
      await companyApi.updateUser(userId, { role: editRole })
      setEditingId(null)
      load()
    } catch { /* noop */ }
  }

  const handleDeactivate = async (userId: string) => {
    if (!confirm('確定要停用此使用者？')) return
    try {
      await companyApi.deactivateUser(userId)
      load()
    } catch { /* noop */ }
  }

  if (loading) return <Loader />

  const roles = ['owner', 'admin', 'hr', 'employee', 'viewer']

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">成員管理 ({users.length})</h3>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <UserPlus className="h-4 w-4" /> 邀請成員
        </button>
      </div>

      {msg && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-700 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" /> {msg}
        </div>
      )}

      {/* Invite modal */}
      {showInvite && (
        <form onSubmit={handleInvite} className="rounded-xl border border-blue-200 bg-blue-50/50 p-5 space-y-3">
          <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2"><Mail className="h-4 w-4" /> 邀請新成員</h4>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              type="email" required placeholder="Email *"
              value={inviteForm.email}
              onChange={e => setInviteForm(p => ({ ...p, email: e.target.value }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <input
              type="text" placeholder="姓名"
              value={inviteForm.full_name}
              onChange={e => setInviteForm(p => ({ ...p, full_name: e.target.value }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <select
              value={inviteForm.role}
              onChange={e => setInviteForm(p => ({ ...p, role: e.target.value }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {roles.filter(r => r !== 'owner').map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'} required placeholder="初始密碼 *"
                value={inviteForm.password}
                onChange={e => setInviteForm(p => ({ ...p, password: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 pr-9 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {submitting ? '邀請中...' : '送出邀請'}
            </button>
            <button type="button" onClick={() => setShowInvite(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              取消
            </button>
          </div>
        </form>
      )}

      {/* User table */}
      {users.length === 0 ? <Empty text="尚無成員" /> : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">姓名</th>
                <th className="px-5 py-3">角色</th>
                <th className="px-5 py-3">狀態</th>
                <th className="px-5 py-3">加入時間</th>
                <th className="px-5 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u: any) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-sm text-gray-900">{u.email}</td>
                  <td className="px-5 py-3 text-sm text-gray-600">{u.full_name || '—'}</td>
                  <td className="px-5 py-3">
                    {editingId === u.id ? (
                      <div className="flex items-center gap-1">
                        <select
                          value={editRole}
                          onChange={e => setEditRole(e.target.value)}
                          className="rounded border border-gray-300 px-2 py-1 text-xs"
                        >
                          {roles.map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                        <button onClick={() => handleUpdateRole(u.id)} className="text-xs text-blue-600 hover:underline">確定</button>
                        <button onClick={() => setEditingId(null)} className="text-xs text-gray-400 hover:underline">取消</button>
                      </div>
                    ) : (
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{u.role}</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${u.status === 'active' ? 'text-green-600' : 'text-red-500'}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${u.status === 'active' ? 'bg-green-500' : 'bg-red-400'}`} />
                      {u.status || 'active'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-500">{u.created_at ? new Date(u.created_at).toLocaleDateString('zh-TW') : '—'}</td>
                  <td className="px-5 py-3 text-right">
                    <div className="relative inline-block">
                      <DropdownMenu
                        onEdit={() => { setEditingId(u.id); setEditRole(u.role || 'employee') }}
                        onDeactivate={() => handleDeactivate(u.id)}
                        disabled={u.role === 'owner'}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function DropdownMenu({ onEdit, onDeactivate, disabled }: { onEdit: () => void; onDeactivate: () => void; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  if (disabled) return <span className="text-xs text-gray-300">—</span>
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="rounded p-1 hover:bg-gray-100">
        <MoreVertical className="h-4 w-4 text-gray-400" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-32 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            <button onClick={() => { onEdit(); setOpen(false) }} className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">變更角色</button>
            <button onClick={() => { onDeactivate(); setOpen(false) }} className="block w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50">停用帳號</button>
          </div>
        </>
      )}
    </div>
  )
}

// ═══ Quota Tab ═══
function QuotaTab() {
  const [quota, setQuota] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    companyApi.quota().then(setQuota).catch(() => null).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader />
  if (!quota) return <Empty text="無法載入配額" />

  return (
    <div className="max-w-lg space-y-5">
      <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">方案配額</h3>
          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
            quota.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
            quota.plan === 'pro' ? 'bg-blue-100 text-blue-700' :
            'bg-gray-100 text-gray-700'
          }`}>{quota.plan || 'free'}</span>
        </div>
        <UsageBar label="使用者" current={quota.current_users} limit={quota.max_users} ratio={quota.users_usage_ratio} />
        <UsageBar label="文件" current={quota.current_documents} limit={quota.max_documents} ratio={quota.documents_usage_ratio} />
        <UsageBar label="儲存空間 (MB)" current={quota.current_storage_mb} limit={quota.max_storage_mb} ratio={quota.storage_usage_ratio} />
        <UsageBar label="月查詢" current={quota.current_monthly_queries} limit={quota.monthly_query_limit} ratio={quota.queries_usage_ratio} />
        <UsageBar label="月 Token" current={quota.current_monthly_tokens} limit={quota.monthly_token_limit} ratio={quota.tokens_usage_ratio} />

        {quota.is_over_quota && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>{quota.quota_warnings?.map((w: string, i: number) => <p key={i}>{w}</p>)}</div>
          </div>
        )}

        {!quota.is_over_quota && (
          <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" /> 配額使用正常
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 text-center">如需調整配額，請聯繫平台管理員</p>
    </div>
  )
}

// ═══ Usage Tab ═══
function UsageTab() {
  const [summary, setSummary] = useState<any>(null)
  const [byUser, setByUser] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showByUser, setShowByUser] = useState(false)

  useEffect(() => {
    Promise.all([companyApi.usageSummary(), companyApi.usageByUser()])
      .then(([s, u]) => { setSummary(s); setByUser(u) })
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader />
  if (!summary) return <Empty text="無法載入用量資料" />

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={BarChart3} label="總操作數" value={summary.total_actions} color="bg-blue-50 text-blue-600" />
        <StatCard icon={MessageSquare} label="總 Token" value={(summary.total_input_tokens + summary.total_output_tokens).toLocaleString()} color="bg-green-50 text-green-600" />
        <StatCard icon={Gauge} label="Pinecone 查詢" value={summary.total_pinecone_queries} color="bg-purple-50 text-purple-600" />
        <StatCard icon={BarChart3} label="估計成本" value={`$${summary.total_cost?.toFixed(4) || '0'}`} color="bg-amber-50 text-amber-600" />
      </div>

      {/* By user toggle */}
      <div>
        <button
          onClick={() => setShowByUser(!showByUser)}
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          <ChevronDown className={`h-4 w-4 transition-transform ${showByUser ? 'rotate-180' : ''}`} />
          按成員查看用量
        </button>
      </div>

      {showByUser && byUser.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">成員</th>
                <th className="px-5 py-3 text-right">查詢次數</th>
                <th className="px-5 py-3 text-right">Token</th>
                <th className="px-5 py-3 text-right">成本</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {byUser.map((u: any, i: number) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-5 py-2">
                    <p className="text-sm font-medium text-gray-900">{u.full_name || u.email}</p>
                    {u.full_name && <p className="text-xs text-gray-400">{u.email}</p>}
                  </td>
                  <td className="px-5 py-2 text-right text-sm text-gray-600">{u.monthly_queries}</td>
                  <td className="px-5 py-2 text-right text-sm text-gray-600">{(u.monthly_tokens || 0).toLocaleString()}</td>
                  <td className="px-5 py-2 text-right text-sm font-medium text-gray-700">${(u.monthly_cost || 0).toFixed(4)}</td>
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
export default function CompanyPage() {
  const [tab, setTab] = useState<Tab>('dashboard')

  const tabs: { key: Tab; label: string; icon: typeof Building2 }[] = [
    { key: 'dashboard', label: '總覽', icon: Building2 },
    { key: 'users', label: '成員管理', icon: Users },
    { key: 'quota', label: '配額', icon: Gauge },
    { key: 'usage', label: '用量', icon: BarChart3 },
  ]

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-blue-600" />
          <h1 className="text-lg font-semibold text-gray-900">公司管理</h1>
        </div>
        <div className="mt-3 flex gap-1">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.key ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <t.icon className="h-4 w-4" /> {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'dashboard' && <DashboardTab />}
        {tab === 'users' && <UsersTab />}
        {tab === 'quota' && <QuotaTab />}
        {tab === 'usage' && <UsageTab />}
      </div>
    </div>
  )
}
