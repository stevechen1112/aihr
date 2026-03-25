import { useEffect, useState, useCallback } from 'react'
import {
  DollarSign, TrendingUp, TrendingDown, Users, FileText,
  ArrowUpRight, ArrowDownRight, Minus, ChevronUp, ChevronDown,
  RefreshCw,
} from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { analyticsApi } from '../api'
import clsx from 'clsx'

// ── Types ──

interface MonthlyTrend {
  month: string
  revenue: number
  cost: number
  profit: number
  margin_pct: number | null
}

interface CostByAction {
  action_type: string
  count: number
  cost: number
}

interface PlatformPnL {
  current_month: string
  monthly_revenue: number
  monthly_cost: number
  monthly_profit: number
  monthly_margin_pct: number | null
  total_revenue: number
  total_cost: number
  total_profit: number
  mrr: number
  free_tenants: number
  pro_tenants: number
  enterprise_tenants: number
  monthly_trend: MonthlyTrend[]
  cost_by_action: CostByAction[]
}

interface TenantPnL {
  tenant_id: string
  tenant_name: string
  plan: string | null
  status: string | null
  user_count: number
  document_count: number
  monthly_revenue: number
  monthly_cost: number
  monthly_profit: number
  margin_pct: number | null
  monthly_queries: number
  monthly_tokens: number
  avg_cost_per_query: number
}

type SortField = 'profit' | 'cost' | 'revenue' | 'margin_pct' | 'monthly_queries' | 'monthly_tokens'
type Tab = 'overview' | 'tenants'

const PIE_COLORS = ['#2563eb', '#7c3aed', '#059669', '#d97706', '#dc2626', '#6366f1', '#0891b2']

const ACTION_LABELS: Record<string, string> = {
  chat: 'AI 對話',
  embed: '向量嵌入',
  index: '文件索引',
  unknown: '其他',
}

function formatUSD(v: number): string {
  if (Math.abs(v) >= 1) return `$${v.toFixed(2)}`
  if (Math.abs(v) >= 0.01) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

function formatNumber(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`
  return v.toLocaleString()
}

const planBadge = (plan: string | null) => {
  const p = plan || 'free'
  const styles: Record<string, string> = {
    free: 'bg-gray-100 text-gray-700',
    pro: 'bg-blue-100 text-blue-700',
    enterprise: 'bg-purple-100 text-purple-700',
  }
  return (
    <span className={clsx('inline-block rounded-full px-2 py-0.5 text-xs font-semibold', styles[p] || styles.free)}>
      {p.toUpperCase()}
    </span>
  )
}

// ── Summary Card ──

function SummaryCard({
  title, value, subtitle, icon: Icon, trend, className,
}: {
  title: string
  value: string
  subtitle?: string
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}) {
  const trendColors = { up: 'text-green-600', down: 'text-red-600', neutral: 'text-gray-500' }
  const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus

  return (
    <div className={clsx('rounded-xl border border-gray-200 bg-white p-5 shadow-sm', className)}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <Icon className="h-5 w-5 text-gray-400" />
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {trend && <TrendIcon className={clsx('h-4 w-4', trendColors[trend])} />}
      </div>
      {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
    </div>
  )
}

// ── Main Page ──

export default function PnLPage() {
  const [tab, setTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(true)
  const [pnl, setPnl] = useState<PlatformPnL | null>(null)
  const [tenants, setTenants] = useState<TenantPnL[]>([])
  const [tenantLoading, setTenantLoading] = useState(false)
  const [sortField, setSortField] = useState<SortField>('profit')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [months, setMonths] = useState(6)

  const fetchPnl = useCallback(async () => {
    setLoading(true)
    try {
      const data = await analyticsApi.platformPnl({ months: String(months) })
      setPnl(data)
    } catch (e) {
      console.error('Failed to load P&L', e)
    } finally {
      setLoading(false)
    }
  }, [months])

  const fetchTenants = useCallback(async () => {
    setTenantLoading(true)
    try {
      const data = await analyticsApi.tenantPnl({ sort_by: sortField, order: sortOrder })
      setTenants(data)
    } catch (e) {
      console.error('Failed to load tenant P&L', e)
    } finally {
      setTenantLoading(false)
    }
  }, [sortField, sortOrder])

  useEffect(() => { fetchPnl() }, [fetchPnl])
  useEffect(() => { if (tab === 'tenants') fetchTenants() }, [tab, fetchTenants])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder(field === 'profit' ? 'asc' : 'desc')
    }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null
    return sortOrder === 'asc'
      ? <ChevronUp className="ml-0.5 inline h-3.5 w-3.5" />
      : <ChevronDown className="ml-0.5 inline h-3.5 w-3.5" />
  }

  if (loading && !pnl) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-red-600 border-t-transparent" />
      </div>
    )
  }

  const d = pnl!

  // Pie data for cost breakdown
  const pieData = d.cost_by_action.map(a => ({
    name: ACTION_LABELS[a.action_type] || a.action_type,
    value: a.cost,
    count: a.count,
  }))

  // Pie data for tenant distribution
  const tenantDistData = [
    { name: 'Free', value: d.free_tenants, color: '#9ca3af' },
    { name: 'Pro', value: d.pro_tenants, color: '#2563eb' },
    { name: 'Enterprise', value: d.enterprise_tenants, color: '#7c3aed' },
  ].filter(d => d.value > 0)

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-6 py-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">收支總覽</h1>
            <p className="mt-1 text-sm text-gray-500">Platform P&L Dashboard — 平台收入與支出監控</p>
          </div>
          <button
            onClick={() => { fetchPnl(); if (tab === 'tenants') fetchTenants() }}
            className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" /> 重新整理
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
          {([
            ['overview', '平台總覽'],
            ['tenants', '租戶收支明細'],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={clsx(
                'flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors',
                tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ═══════════════ TAB: OVERVIEW ═══════════════ */}
        {tab === 'overview' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <SummaryCard
                title="本月收入"
                value={formatUSD(d.monthly_revenue)}
                subtitle={`累計 ${formatUSD(d.total_revenue)}`}
                icon={DollarSign}
                trend={d.monthly_revenue > 0 ? 'up' : 'neutral'}
              />
              <SummaryCard
                title="本月支出"
                value={formatUSD(d.monthly_cost)}
                subtitle={`累計 ${formatUSD(d.total_cost)}`}
                icon={TrendingDown}
                trend={d.monthly_cost > 0 ? 'down' : 'neutral'}
              />
              <SummaryCard
                title="本月毛利"
                value={formatUSD(d.monthly_profit)}
                subtitle={d.monthly_margin_pct != null ? `毛利率 ${d.monthly_margin_pct}%` : '尚無收入'}
                icon={TrendingUp}
                trend={d.monthly_profit >= 0 ? 'up' : 'down'}
              />
              <SummaryCard
                title="MRR (月經常收入)"
                value={formatUSD(d.mrr)}
                subtitle={`${d.free_tenants + d.pro_tenants + d.enterprise_tenants} 家活躍租戶`}
                icon={Users}
              />
            </div>

            {/* Monthly Trend Chart + Tenant Distribution */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Trend Chart */}
              <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-base font-semibold text-gray-900">月度收支趨勢</h2>
                  <select
                    value={months}
                    onChange={e => setMonths(Number(e.target.value))}
                    className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                  >
                    <option value={3}>近 3 個月</option>
                    <option value={6}>近 6 個月</option>
                    <option value={12}>近 12 個月</option>
                  </select>
                </div>
                {d.monthly_trend.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={d.monthly_trend} barGap={4}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip
                        formatter={(v: any, name: any) => [formatUSD(Number(v)), name === 'revenue' ? '收入' : name === 'cost' ? '支出' : '毛利']}
                        labelFormatter={(l: any) => `月份: ${l}`}
                      />
                      <Legend formatter={(v: string) => v === 'revenue' ? '收入' : v === 'cost' ? '支出' : '毛利'} />
                      <Bar dataKey="revenue" fill="#2563eb" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="cost" fill="#dc2626" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="profit" fill="#059669" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-[280px] items-center justify-center text-gray-400">暫無資料</div>
                )}
              </div>

              {/* Tenant Distribution */}
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-base font-semibold text-gray-900">租戶方案分佈</h2>
                {tenantDistData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={tenantDistData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={2}
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {tenantDistData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-[200px] items-center justify-center text-gray-400">暫無租戶</div>
                )}
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Free</span><span className="font-medium">{d.free_tenants} 家</span></div>
                  <div className="flex justify-between"><span className="text-blue-600">Pro</span><span className="font-medium">{d.pro_tenants} 家</span></div>
                  <div className="flex justify-between"><span className="text-purple-600">Enterprise</span><span className="font-medium">{d.enterprise_tenants} 家</span></div>
                </div>
              </div>
            </div>

            {/* Cost Breakdown + Margin Trend */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Cost Breakdown Pie */}
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-base font-semibold text-gray-900">本月支出分類</h2>
                {pieData.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={90}
                          label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                        >
                          {pieData.map((_, i) => (
                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v: any) => formatUSD(Number(v))} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="mt-3 space-y-1.5">
                      {d.cost_by_action.map((a, i) => (
                        <div key={a.action_type} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                            <span className="text-gray-600">{ACTION_LABELS[a.action_type] || a.action_type}</span>
                          </div>
                          <div className="text-right">
                            <span className="font-medium text-gray-900">{formatUSD(a.cost)}</span>
                            <span className="ml-2 text-gray-400">({formatNumber(a.count)} 次)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="flex h-[220px] items-center justify-center text-gray-400">本月暫無支出</div>
                )}
              </div>

              {/* Margin Trend Line */}
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-base font-semibold text-gray-900">毛利率趨勢</h2>
                {d.monthly_trend.some(t => t.margin_pct != null) ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={d.monthly_trend.filter(t => t.margin_pct != null)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} unit="%" />
                      <Tooltip formatter={(v: any) => [`${v}%`, '毛利率']} />
                      <Line type="monotone" dataKey="margin_pct" stroke="#059669" strokeWidth={2} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-[280px] items-center justify-center text-gray-400">
                    尚無收入資料，無法計算毛利率
                  </div>
                )}
              </div>
            </div>

            {/* Cumulative Summary */}
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-base font-semibold text-gray-900">累計統計</h2>
              <div className="grid grid-cols-3 gap-6 text-center">
                <div>
                  <p className="text-sm text-gray-500">累計總收入</p>
                  <p className="mt-1 text-xl font-bold text-blue-600">{formatUSD(d.total_revenue)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">累計總支出</p>
                  <p className="mt-1 text-xl font-bold text-red-600">{formatUSD(d.total_cost)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">累計毛利</p>
                  <p className={clsx('mt-1 text-xl font-bold', d.total_profit >= 0 ? 'text-green-600' : 'text-red-600')}>
                    {formatUSD(d.total_profit)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════ TAB: TENANTS ═══════════════ */}
        {tab === 'tenants' && (
          <div className="space-y-4">
            {/* Info */}
            <div className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700">
              <FileText className="mr-1.5 inline h-4 w-4" />
              各租戶本月收支明細 — 收入依據已付款帳單或方案月費，支出依據 API 使用量（UsageRecord）。點擊欄位標題可排序。
            </div>

            {/* Table */}
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">租戶</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">方案</th>
                      <th className="px-3 py-3 text-right font-medium text-gray-500">用戶</th>
                      <th className="px-3 py-3 text-right font-medium text-gray-500">文件</th>
                      <th
                        className="cursor-pointer px-4 py-3 text-right font-medium text-gray-500 hover:text-gray-900"
                        onClick={() => handleSort('revenue')}
                      >
                        月收入<SortIcon field="revenue" />
                      </th>
                      <th
                        className="cursor-pointer px-4 py-3 text-right font-medium text-gray-500 hover:text-gray-900"
                        onClick={() => handleSort('cost')}
                      >
                        月支出<SortIcon field="cost" />
                      </th>
                      <th
                        className="cursor-pointer px-4 py-3 text-right font-medium text-gray-500 hover:text-gray-900"
                        onClick={() => handleSort('profit')}
                      >
                        毛利<SortIcon field="profit" />
                      </th>
                      <th
                        className="cursor-pointer px-4 py-3 text-right font-medium text-gray-500 hover:text-gray-900"
                        onClick={() => handleSort('margin_pct')}
                      >
                        毛利率<SortIcon field="margin_pct" />
                      </th>
                      <th
                        className="cursor-pointer px-3 py-3 text-right font-medium text-gray-500 hover:text-gray-900"
                        onClick={() => handleSort('monthly_queries')}
                      >
                        查詢數<SortIcon field="monthly_queries" />
                      </th>
                      <th
                        className="cursor-pointer px-3 py-3 text-right font-medium text-gray-500 hover:text-gray-900"
                        onClick={() => handleSort('monthly_tokens')}
                      >
                        Token<SortIcon field="monthly_tokens" />
                      </th>
                      <th className="px-3 py-3 text-right font-medium text-gray-500">每查詢成本</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {tenantLoading ? (
                      <tr>
                        <td colSpan={11} className="py-12 text-center text-gray-400">
                          <div className="mx-auto h-6 w-6 animate-spin rounded-full border-4 border-red-600 border-t-transparent" />
                        </td>
                      </tr>
                    ) : tenants.length === 0 ? (
                      <tr>
                        <td colSpan={11} className="py-12 text-center text-gray-400">暫無租戶資料</td>
                      </tr>
                    ) : (
                      tenants.map(t => (
                        <tr key={t.tenant_id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <div>
                              <p className="font-medium text-gray-900">{t.tenant_name}</p>
                              <p className="text-xs text-gray-400">{t.tenant_id.slice(0, 8)}…</p>
                            </div>
                          </td>
                          <td className="px-4 py-3">{planBadge(t.plan)}</td>
                          <td className="px-3 py-3 text-right text-gray-600">{t.user_count}</td>
                          <td className="px-3 py-3 text-right text-gray-600">{t.document_count}</td>
                          <td className="px-4 py-3 text-right font-medium text-blue-600">{formatUSD(t.monthly_revenue)}</td>
                          <td className="px-4 py-3 text-right font-medium text-red-600">{formatUSD(t.monthly_cost)}</td>
                          <td className={clsx('px-4 py-3 text-right font-bold', t.monthly_profit >= 0 ? 'text-green-600' : 'text-red-600')}>
                            {formatUSD(t.monthly_profit)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {t.margin_pct != null ? (
                              <span className={clsx('font-medium', t.margin_pct >= 0 ? 'text-green-600' : 'text-red-600')}>
                                {t.margin_pct}%
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-right text-gray-600">{formatNumber(t.monthly_queries)}</td>
                          <td className="px-3 py-3 text-right text-gray-600">{formatNumber(t.monthly_tokens)}</td>
                          <td className="px-3 py-3 text-right text-gray-500">{formatUSD(t.avg_cost_per_query)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                  {/* Footer totals */}
                  {!tenantLoading && tenants.length > 0 && (
                    <tfoot className="bg-gray-50">
                      <tr className="font-semibold">
                        <td className="px-4 py-3 text-gray-900" colSpan={2}>合計 ({tenants.length} 家)</td>
                        <td className="px-3 py-3 text-right text-gray-600">{tenants.reduce((s, t) => s + t.user_count, 0)}</td>
                        <td className="px-3 py-3 text-right text-gray-600">{tenants.reduce((s, t) => s + t.document_count, 0)}</td>
                        <td className="px-4 py-3 text-right text-blue-700">
                          {formatUSD(tenants.reduce((s, t) => s + t.monthly_revenue, 0))}
                        </td>
                        <td className="px-4 py-3 text-right text-red-700">
                          {formatUSD(tenants.reduce((s, t) => s + t.monthly_cost, 0))}
                        </td>
                        <td className={clsx(
                          'px-4 py-3 text-right font-bold',
                          tenants.reduce((s, t) => s + t.monthly_profit, 0) >= 0 ? 'text-green-700' : 'text-red-700',
                        )}>
                          {formatUSD(tenants.reduce((s, t) => s + t.monthly_profit, 0))}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500">
                          {(() => {
                            const rev = tenants.reduce((s, t) => s + t.monthly_revenue, 0)
                            const cost = tenants.reduce((s, t) => s + t.monthly_cost, 0)
                            return rev > 0 ? `${((rev - cost) / rev * 100).toFixed(1)}%` : '—'
                          })()}
                        </td>
                        <td className="px-3 py-3 text-right text-gray-600">
                          {formatNumber(tenants.reduce((s, t) => s + t.monthly_queries, 0))}
                        </td>
                        <td className="px-3 py-3 text-right text-gray-600">
                          {formatNumber(tenants.reduce((s, t) => s + t.monthly_tokens, 0))}
                        </td>
                        <td className="px-3 py-3 text-right text-gray-500">
                          {(() => {
                            const q = tenants.reduce((s, t) => s + t.monthly_queries, 0)
                            const c = tenants.reduce((s, t) => s + t.monthly_cost, 0)
                            return q > 0 ? formatUSD(c / q) : '—'
                          })()}
                        </td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
