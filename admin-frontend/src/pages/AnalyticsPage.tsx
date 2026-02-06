import { useState, useEffect, useCallback } from 'react'
import { analyticsApi } from '../api'
import {
  Loader2, AlertCircle, TrendingUp, TrendingDown,
  AlertTriangle, DollarSign, Zap, Activity, Calendar,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

type Tab = 'trend' | 'tenants' | 'anomalies' | 'budget'

// ─── Shared ───
function Loader() {
  return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
}
function Empty({ text }: { text: string }) {
  return <div className="flex flex-col items-center py-16 text-gray-400"><AlertCircle className="mb-3 h-10 w-10" /><p className="text-sm">{text}</p></div>
}
function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof TrendingUp; label: string; value: string | number; sub?: string; color: string
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

// ─── Daily Trend Tab ───
function TrendTab() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState('30')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await analyticsApi.dailyTrend({ days })
      setData(res.trends ?? res ?? [])
    } catch { setData([]) }
    setLoading(false)
  }, [days])

  useEffect(() => { load() }, [load])

  if (loading) return <Loader />
  if (!data.length) return <Empty text="暫無趨勢資料" />

  const totalQueries = data.reduce((s: number, d: any) => s + (d.total_queries ?? 0), 0)
  const totalTokens = data.reduce((s: number, d: any) => s + (d.total_tokens ?? 0), 0)
  const totalCost = data.reduce((s: number, d: any) => s + (d.total_cost ?? 0), 0)

  return (
    <div className="space-y-6">
      {/* Period selector */}
      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 text-gray-500" />
        <span className="text-sm text-gray-600">時間範圍：</span>
        {[
          { v: '7', l: '7 天' },
          { v: '30', l: '30 天' },
          { v: '90', l: '90 天' },
        ].map(({ v, l }) => (
          <button
            key={v}
            onClick={() => setDays(v)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              days === v ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={Zap} label="查詢總數" value={totalQueries.toLocaleString()} color="bg-blue-50 text-blue-600" />
        <StatCard icon={Activity} label="Token 總量" value={totalTokens.toLocaleString()} color="bg-purple-50 text-purple-600" />
        <StatCard icon={DollarSign} label="總成本 (USD)" value={`$${totalCost.toFixed(2)}`} color="bg-green-50 text-green-600" />
      </div>

      {/* Queries Chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="mb-4 text-sm font-semibold text-gray-700">每日查詢量趨勢</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickMargin={8} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid #e5e7eb' }}
              formatter={(v: number | undefined) => [v != null ? v.toLocaleString() : '0', '']}
            />
            <Legend />
            <Line type="monotone" dataKey="total_queries" name="查詢數" stroke="#3b82f6" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Cost Chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="mb-4 text-sm font-semibold text-gray-700">每日成本趨勢 (USD)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickMargin={8} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid #e5e7eb' }}
              formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(4)}`, '']}
            />
            <Legend />
            <Line type="monotone" dataKey="total_cost" name="成本" stroke="#10b981" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="total_tokens" name="Tokens" stroke="#8b5cf6" strokeWidth={1.5} dot={false} yAxisId={0} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ─── Monthly by Tenant Tab ───
function TenantsTab() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await analyticsApi.monthlyByTenant()
        setData(res.data ?? res ?? [])
      } catch { setData([]) }
      setLoading(false)
    })()
  }, [])

  if (loading) return <Loader />
  if (!data.length) return <Empty text="暫無租戶月度資料" />

  const tenantKeys = [...new Map(data.map((d: any) => {
    const key = d.tenant_id ?? d.tenant_name
    const label = d.tenant_name ?? String(key)
    return [String(key), label]
  })).entries()].map(([key, label]) => ({ key, label }))

  const months: Record<string, any> = {}
  data.forEach((d: any) => {
    const key = d.month
    if (!months[key]) months[key] = { month: key }
    const tenantKey = String(d.tenant_id ?? d.tenant_name)
    months[key][tenantKey] = d.total_cost ?? 0
  })
  const chartData = Object.values(months).sort((a: any, b: any) => a.month.localeCompare(b.month))

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="mb-4 text-sm font-semibold text-gray-700">月度租戶成本比較</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} tickMargin={8} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid #e5e7eb' }}
              formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(2)}`, '']}
            />
            <Legend />
            {tenantKeys.map((t, i) => (
              <Bar key={t.key} dataKey={t.key} name={t.label} stackId="cost" fill={COLORS[i % COLORS.length]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detail table */}
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">月份</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">租戶</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">查詢數</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Tokens</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">成本</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((d: any, i: number) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-700">{d.month}</td>
                <td className="px-4 py-3 text-gray-700">{d.tenant_name}</td>
                <td className="px-4 py-3 text-right text-gray-700">{(d.total_queries ?? 0).toLocaleString()}</td>
                <td className="px-4 py-3 text-right text-gray-700">{(d.total_tokens ?? 0).toLocaleString()}</td>
                <td className="px-4 py-3 text-right font-medium text-gray-900">${(d.total_cost ?? 0).toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Anomalies Tab ───
function AnomaliesTab() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [threshold, setThreshold] = useState('2.0')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await analyticsApi.anomalies({ threshold })
      setData(res.anomalies ?? res ?? [])
    } catch { setData([]) }
    setLoading(false)
  }, [threshold])

  useEffect(() => { load() }, [load])

  if (loading) return <Loader />

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <span className="text-sm text-gray-600">偏差閾值：</span>
        {['1.5', '2.0', '3.0'].map(t => (
          <button
            key={t}
            onClick={() => setThreshold(t)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              threshold === t ? 'bg-amber-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t}x
          </button>
        ))}
      </div>

      {!data.length ? (
        <Empty text="無異常偵測結果 — 使用量穩定 ✓" />
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">租戶</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">日期</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">查詢數</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">偏差倍率</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">說明</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((d: any, i: number) => {
                const ratio = d.deviation_ratio ?? 0
                const severity = ratio >= 3 ? 'text-red-600 bg-red-50' : ratio >= 2 ? 'text-amber-600 bg-amber-50' : 'text-yellow-600 bg-yellow-50'
                return (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-700">{d.tenant_name}</td>
                    <td className="px-4 py-3 text-gray-600">{d.date}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{(d.total_queries ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${severity}`}>
                        <TrendingUp className="h-3 w-3" />
                        {ratio.toFixed(1)}x
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{d.message}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Budget Alerts Tab ───
function BudgetTab() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await analyticsApi.budgetAlerts()
        setData(res.alerts ?? res ?? [])
      } catch { setData([]) }
      setLoading(false)
    })()
  }, [])

  if (loading) return <Loader />
  if (!data.length) return <Empty text="暫無預算警報" />

  return (
    <div className="space-y-4">
      {data.map((d: any, i: number) => {
        const ratio = d.usage_ratio ?? 0
        const pct = Math.min(ratio * 100, 100)
        const isExceeded = ratio >= 1
        const isWarning = ratio >= 0.8

        return (
          <div key={i} className={`rounded-xl border p-5 ${
            isExceeded ? 'border-red-200 bg-red-50' : isWarning ? 'border-amber-200 bg-amber-50' : 'border-gray-200 bg-white'
          }`}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {isExceeded ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100">
                    <TrendingDown className="h-5 w-5 text-red-600" />
                  </div>
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                  </div>
                )}
                <div>
                  <p className="font-semibold text-gray-900">{d.tenant_name}</p>
                  <p className="text-xs text-gray-500">{d.resource}</p>
                </div>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                isExceeded ? 'bg-red-200 text-red-700' : 'bg-amber-200 text-amber-700'
              }`}>
                {isExceeded ? '已超額' : '預警'}
              </span>
            </div>

            <div className="mt-4">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-600">使用量 / 上限</span>
                <span className="font-medium">{(d.current ?? 0).toLocaleString()} / {(d.limit ?? 0).toLocaleString()} ({pct.toFixed(0)}%)</span>
              </div>
              <div className="h-2.5 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${isExceeded ? 'bg-red-500' : 'bg-amber-500'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>

            {d.message && <p className="mt-3 text-xs text-gray-600">{d.message}</p>}
          </div>
        )
      })}
    </div>
  )
}

// ─── Main Page ───
const tabs: { key: Tab; label: string; icon: typeof TrendingUp }[] = [
  { key: 'trend', label: '使用趨勢', icon: TrendingUp },
  { key: 'tenants', label: '租戶成本', icon: DollarSign },
  { key: 'anomalies', label: '異常偵測', icon: AlertTriangle },
  { key: 'budget', label: '預算警報', icon: Activity },
]

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>('trend')

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">成本分析</h1>
          <p className="mt-1 text-sm text-gray-500">平台使用量趨勢、租戶成本比較與異常偵測</p>
        </div>

        <div className="flex gap-1 rounded-xl bg-gray-100 p-1">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition ${
                tab === key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {tab === 'trend' && <TrendTab />}
        {tab === 'tenants' && <TenantsTab />}
        {tab === 'anomalies' && <AnomaliesTab />}
        {tab === 'budget' && <BudgetTab />}
      </div>
    </div>
  )
}
