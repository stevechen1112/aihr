import { useState, useEffect } from 'react'
import { chatApi } from '../api'
import { Loader2, MessageSquare, Clock, ThumbsUp, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

interface DashboardData {
  total_conversations: number
  total_messages: number
  avg_turns_per_conversation: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  daily_conversations: { date: string; count: number }[]
  feedback: {
    total: number
    positive: number
    negative: number
    positive_rate: number
    categories: { category: string; count: number }[]
  }
}

const COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6']

export default function RAGDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  useEffect(() => {
    setLoading(true)
    chatApi
      .ragDashboard(days)
      .then(setData)
      .catch(() => toast.error('載入儀表板失敗'))
      .finally(() => setLoading(false))
  }, [days])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!data) return null

  const feedbackPieData = [
    { name: '正面', value: data.feedback.positive },
    { name: '負面', value: data.feedback.negative },
  ].filter(d => d.value > 0)

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-4 md:p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <h1 className="text-xl font-bold text-gray-900">RAG 品質儀表板</h1>
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value={7}>最近 7 天</option>
            <option value={30}>最近 30 天</option>
            <option value={90}>最近 90 天</option>
          </select>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard icon={MessageSquare} label="對話總數" value={data.total_conversations} color="blue" />
          <KPICard icon={TrendingUp} label="平均輪次" value={data.avg_turns_per_conversation} color="purple" />
          <KPICard icon={Clock} label="平均延遲" value={`${data.avg_latency_ms}ms`} color="amber" />
          <KPICard
            icon={ThumbsUp}
            label="好評率"
            value={data.feedback.total > 0 ? `${(data.feedback.positive_rate * 100).toFixed(1)}%` : 'N/A'}
            color="green"
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily conversations */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">每日對話數</h3>
            {data.daily_conversations.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.daily_conversations}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    tickFormatter={v => v.slice(5)}
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="對話數" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-sm text-gray-400 py-12">此期間無數據</p>
            )}
          </div>

          {/* Feedback pie */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">回饋分佈</h3>
            {feedbackPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={feedbackPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {feedbackPieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i]} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-sm text-gray-400 py-12">尚無回饋數據</p>
            )}
          </div>
        </div>

        {/* Latency details */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">回覆延遲統計</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-gray-900">{data.avg_latency_ms}<span className="text-sm text-gray-400">ms</span></p>
              <p className="text-xs text-gray-500 mt-1">平均</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{data.p50_latency_ms}<span className="text-sm text-gray-400">ms</span></p>
              <p className="text-xs text-gray-500 mt-1">P50</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{data.p95_latency_ms}<span className="text-sm text-gray-400">ms</span></p>
              <p className="text-xs text-gray-500 mt-1">P95</p>
            </div>
          </div>
        </div>

        {/* Feedback stats */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">回饋統計</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-blue-600">{data.feedback.total}</p>
              <p className="text-xs text-gray-500 mt-1">總回饋數</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{data.feedback.positive}</p>
              <p className="text-xs text-gray-500 mt-1">👍 正面</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-500">{data.feedback.negative}</p>
              <p className="text-xs text-gray-500 mt-1">👎 負面</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function KPICard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  color: 'blue' | 'green' | 'amber' | 'purple'
}) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className={`inline-flex rounded-lg p-2 ${colorMap[color]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="mt-3 text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  )
}
