import { useState, useEffect } from 'react'
import { adminApi } from '../api'
import {
  Loader2, Building2, Users, FileText, MessageSquare,
  Coins, Activity, TrendingUp, Search, ChevronRight,
  Heart, AlertCircle, CheckCircle2, Server
} from 'lucide-react'

// ─── Sub-views ───
type View = 'dashboard' | 'tenants' | 'tenant-detail' | 'users' | 'health'

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Coins; label: string; value: string | number; sub?: string; color: string
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

// ═══ Dashboard Overview ═══
function DashboardView({ onNavigate }: { onNavigate: (v: View, id?: string) => void }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.dashboard().then(setData).catch(() => null).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader />
  if (!data) return <EmptyState text="無法載入儀表板" />

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <button onClick={() => onNavigate('tenants')} className="text-left">
          <StatCard icon={Building2} label="租戶數" value={data.total_tenants} sub={`活躍: ${data.active_tenants}`} color="bg-blue-50 text-blue-600" />
        </button>
        <button onClick={() => onNavigate('users')} className="text-left">
          <StatCard icon={Users} label="總用戶數" value={data.total_users} sub={`活躍: ${data.active_users}`} color="bg-green-50 text-green-600" />
        </button>
        <StatCard icon={FileText} label="文件數" value={data.total_documents} sub={`對話: ${data.total_conversations}`} color="bg-purple-50 text-purple-600" />
        <StatCard icon={Coins} label="總成本" value={`$${data.total_cost.toFixed(4)}`} sub={`呼叫: ${data.total_actions}`} color="bg-amber-50 text-amber-600" />
      </div>

      {/* Daily trend */}
      {data.daily_actions.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> 近 7 天呼叫趨勢
          </h3>
          <div className="flex items-end gap-2 h-32">
            {data.daily_actions.map((d: any) => {
              const maxCount = Math.max(...data.daily_actions.map((x: any) => x.count), 1)
              const pct = (d.count / maxCount) * 100
              return (
                <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-xs text-gray-500">{d.count}</span>
                  <div className="w-full bg-blue-500 rounded-t" style={{ height: `${Math.max(pct, 4)}%` }} />
                  <span className="text-[10px] text-gray-400">{d.date.slice(5)}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Top tenants */}
      {data.top_tenants.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <div className="border-b border-gray-100 px-5 py-3">
            <h3 className="text-sm font-semibold text-gray-700">成本前 5 租戶</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-2">租戶</th>
                <th className="px-5 py-2 text-right">呼叫次數</th>
                <th className="px-5 py-2 text-right">成本 (USD)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.top_tenants.map((t: any) => (
                <tr key={t.name} className="hover:bg-gray-50">
                  <td className="px-5 py-2 text-sm font-medium text-gray-900">{t.name}</td>
                  <td className="px-5 py-2 text-right text-sm text-gray-600">{t.actions}</td>
                  <td className="px-5 py-2 text-right text-sm font-medium text-gray-700">${t.cost.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ═══ Tenant List ═══
function TenantsView({ onNavigate }: { onNavigate: (v: View, id?: string) => void }) {
  const [tenants, setTenants] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    adminApi.tenants(params).then(setTenants).catch(() => []).finally(() => setLoading(false))
  }, [search])

  if (loading) return <Loader />

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜尋租戶名稱..."
            value={search}
            onChange={e => { setSearch(e.target.value); setLoading(true) }}
            className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {tenants.length === 0 ? (
        <EmptyState text="無租戶" />
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">名稱</th>
                <th className="px-5 py-3">方案</th>
                <th className="px-5 py-3">狀態</th>
                <th className="px-5 py-3 text-right">用戶</th>
                <th className="px-5 py-3 text-right">文件</th>
                <th className="px-5 py-3 text-right">API 呼叫</th>
                <th className="px-5 py-3 text-right">成本</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tenants.map((t: any) => (
                <tr key={t.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => onNavigate('tenant-detail', t.id)}>
                  <td className="px-5 py-3">
                    <span className="text-sm font-medium text-gray-900">{t.name}</span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      t.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
                      t.plan === 'pro' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>{t.plan || 'free'}</span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                      t.status === 'active' ? 'text-green-600' : 'text-red-500'
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${t.status === 'active' ? 'bg-green-500' : 'bg-red-400'}`} />
                      {t.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right text-sm text-gray-600">{t.user_count}</td>
                  <td className="px-5 py-3 text-right text-sm text-gray-600">{t.document_count}</td>
                  <td className="px-5 py-3 text-right text-sm text-gray-600">{t.total_actions}</td>
                  <td className="px-5 py-3 text-right text-sm font-medium text-gray-700">${t.total_cost.toFixed(4)}</td>
                  <td className="px-5 py-3"><ChevronRight className="h-4 w-4 text-gray-400" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ═══ Tenant Detail ═══
function TenantDetailView({ tenantId, onBack }: { tenantId: string; onBack: () => void }) {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.tenantStats(tenantId).then(setStats).catch(() => null).finally(() => setLoading(false))
  }, [tenantId])

  if (loading) return <Loader />
  if (!stats) return <EmptyState text="無法載入租戶資料" />

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="text-sm text-blue-600 hover:text-blue-800">&larr; 返回租戶列表</button>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">{stats.tenant_name}</h2>
          <p className="text-sm text-gray-500">方案: {stats.plan} &middot; 狀態: {stats.status}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users} label="用戶數" value={stats.user_count} color="bg-blue-50 text-blue-600" />
        <StatCard icon={FileText} label="文件數" value={stats.document_count} color="bg-green-50 text-green-600" />
        <StatCard icon={MessageSquare} label="對話數" value={stats.conversation_count} color="bg-purple-50 text-purple-600" />
        <StatCard icon={Coins} label="總成本" value={`$${stats.total_cost.toFixed(4)}`} sub={`${stats.total_actions} 次呼叫`} color="bg-amber-50 text-amber-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Token usage */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Token 用量</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">輸入 Tokens</span><span className="font-medium">{stats.total_input_tokens.toLocaleString()}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">輸出 Tokens</span><span className="font-medium">{stats.total_output_tokens.toLocaleString()}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Pinecone 查詢</span><span className="font-medium">{stats.total_pinecone_queries.toLocaleString()}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Embedding 呼叫</span><span className="font-medium">{stats.total_embedding_calls.toLocaleString()}</span></div>
          </div>
        </div>

        {/* Users table */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <div className="border-b border-gray-100 px-5 py-3">
            <h3 className="text-sm font-semibold text-gray-700">用戶列表</h3>
          </div>
          <div className="max-h-48 overflow-y-auto">
            <table className="w-full">
              <tbody className="divide-y divide-gray-100">
                {stats.users.map((u: any) => (
                  <tr key={u.id}>
                    <td className="px-5 py-2 text-sm text-gray-900">{u.email}</td>
                    <td className="px-5 py-2">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{u.role}</span>
                    </td>
                    <td className="px-5 py-2 text-xs text-gray-500">{u.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recent actions */}
      {stats.recent_actions.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <div className="border-b border-gray-100 px-5 py-3">
            <h3 className="text-sm font-semibold text-gray-700">近期操作記錄</h3>
          </div>
          <table className="w-full">
            <tbody className="divide-y divide-gray-100">
              {stats.recent_actions.map((a: any) => (
                <tr key={a.id}>
                  <td className="px-5 py-2 text-sm text-gray-500">{a.created_at ? new Date(a.created_at).toLocaleString('zh-TW') : ''}</td>
                  <td className="px-5 py-2"><span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">{a.action}</span></td>
                  <td className="px-5 py-2 text-xs text-gray-400 font-mono">{a.actor_user_id?.slice(0, 8) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ═══ Users Search ═══
function UsersView() {
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    adminApi.users(params).then(setUsers).catch(() => []).finally(() => setLoading(false))
  }, [search])

  if (loading) return <Loader />

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="搜尋 Email 或姓名..."
          value={search}
          onChange={e => { setSearch(e.target.value); setLoading(true) }}
          className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {users.length === 0 ? (
        <EmptyState text="找不到用戶" />
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">姓名</th>
                <th className="px-5 py-3">角色</th>
                <th className="px-5 py-3">租戶</th>
                <th className="px-5 py-3">部門</th>
                <th className="px-5 py-3">狀態</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u: any) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-sm text-gray-900">{u.email}</td>
                  <td className="px-5 py-3 text-sm text-gray-600">{u.full_name || '—'}</td>
                  <td className="px-5 py-3"><span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{u.role}</span></td>
                  <td className="px-5 py-3 text-sm text-gray-600">{u.tenant_name || '—'}</td>
                  <td className="px-5 py-3 text-sm text-gray-500">{u.department_name || '—'}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${u.status === 'active' ? 'text-green-600' : 'text-red-500'}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${u.status === 'active' ? 'bg-green-500' : 'bg-red-400'}`} />
                      {u.status}
                    </span>
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

// ═══ System Health ═══
function HealthView() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.systemHealth().then(setHealth).catch(() => null).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader />
  if (!health) return <EmptyState text="無法取得系統狀態" />

  const StatusIcon = health.status === 'healthy' ? CheckCircle2 : AlertCircle
  const statusColor = health.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'

  return (
    <div className="space-y-4 max-w-lg">
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-3 mb-6">
          <StatusIcon className={`h-8 w-8 ${statusColor}`} />
          <div>
            <h2 className="text-lg font-bold text-gray-900">系統狀態: {health.status}</h2>
            <p className="text-sm text-gray-500">Python {health.python_version}</p>
          </div>
        </div>

        <div className="space-y-3">
          {[
            { label: '資料庫 (PostgreSQL)', status: health.database, icon: Server },
            { label: 'Redis', status: health.redis, icon: Activity },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
              <div className="flex items-center gap-2">
                <item.icon className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-700">{item.label}</span>
              </div>
              <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                item.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                <span className={`h-2 w-2 rounded-full ${
                  item.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-400'
                }`} />
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Shared components ───
function Loader() {
  return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
}

function EmptyState({ text }: { text: string }) {
  return <div className="flex flex-col items-center py-16 text-gray-400"><AlertCircle className="mb-3 h-10 w-10" /><p className="text-sm">{text}</p></div>
}

// ═══ Main Admin Page ═══
export default function AdminPage() {
  const [view, setView] = useState<View>('dashboard')
  const [selectedTenantId, setSelectedTenantId] = useState<string>('')

  const navigate = (v: View, id?: string) => {
    setView(v)
    if (id) setSelectedTenantId(id)
  }

  const tabs: { key: View; label: string; icon: typeof Building2 }[] = [
    { key: 'dashboard', label: '總覽', icon: Activity },
    { key: 'tenants', label: '租戶管理', icon: Building2 },
    { key: 'users', label: '用戶搜尋', icon: Users },
    { key: 'health', label: '系統健康', icon: Heart },
  ]

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-2">
          <Server className="h-5 w-5 text-red-600" />
          <h1 className="text-lg font-semibold text-gray-900">平台管理後台</h1>
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Superuser</span>
        </div>
        {/* Tabs */}
        <div className="mt-3 flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => navigate(tab.key)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                (view === tab.key || (view === 'tenant-detail' && tab.key === 'tenants'))
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {view === 'dashboard' && <DashboardView onNavigate={navigate} />}
        {view === 'tenants' && <TenantsView onNavigate={navigate} />}
        {view === 'tenant-detail' && <TenantDetailView tenantId={selectedTenantId} onBack={() => setView('tenants')} />}
        {view === 'users' && <UsersView />}
        {view === 'health' && <HealthView />}
      </div>
    </div>
  )
}
