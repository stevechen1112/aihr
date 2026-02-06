import { useState, useEffect } from 'react'
import { auditApi } from '../api'
import type { UsageSummary, UsageByAction } from '../types'
import { BarChart3, Loader2, Coins, MessageSquare, Database, Cpu, FileSpreadsheet, FileText } from 'lucide-react'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Coins, label: string, value: string | number, sub?: string, color: string
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

export default function UsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null)
  const [byAction, setByAction] = useState<UsageByAction[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState<'csv' | 'pdf' | null>(null)

  useEffect(() => {
    Promise.all([
      auditApi.usageSummary().catch(() => null),
      auditApi.usageByAction().catch(() => []),
    ]).then(([s, a]) => {
      setSummary(s)
      setByAction(a)
    }).finally(() => setLoading(false))
  }, [])

  const handleExport = async (format: 'csv' | 'pdf') => {
    setExporting(format)
    try {
      const blob = await auditApi.exportUsage(format)
      const ext = format === 'csv' ? 'csv' : 'pdf'
      downloadBlob(blob, `usage_records_${new Date().toISOString().slice(0, 10)}.${ext}`)
    } catch {
      alert('匯出失敗，請稍後再試')
    } finally {
      setExporting(null)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">用量統計</h1>
            <p className="text-sm text-gray-500">查看 API 呼叫與 Token 消耗</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('csv')}
              disabled={!!exporting}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {exporting === 'csv' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4" />}
              匯出 CSV
            </button>
            <button
              onClick={() => handleExport('pdf')}
              disabled={!!exporting}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {exporting === 'pdf' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              匯出 PDF
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {!summary ? (
          <div className="flex flex-col items-center py-12 text-gray-400">
            <BarChart3 className="mb-3 h-10 w-10" />
            <p className="text-sm">尚無用量資料</p>
          </div>
        ) : (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                icon={MessageSquare}
                label="總操作次數"
                value={summary.total_actions.toLocaleString()}
                color="bg-blue-50 text-blue-600"
              />
              <StatCard
                icon={Cpu}
                label="輸入 Tokens"
                value={summary.total_input_tokens.toLocaleString()}
                sub={`輸出: ${summary.total_output_tokens.toLocaleString()}`}
                color="bg-purple-50 text-purple-600"
              />
              <StatCard
                icon={Database}
                label="Pinecone 查詢"
                value={summary.total_pinecone_queries.toLocaleString()}
                sub={`Embedding: ${summary.total_embedding_calls.toLocaleString()}`}
                color="bg-green-50 text-green-600"
              />
              <StatCard
                icon={Coins}
                label="預估成本"
                value={`$${summary.total_cost.toFixed(4)}`}
                sub="USD"
                color="bg-amber-50 text-amber-600"
              />
            </div>

            {/* By action type */}
            {byAction.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <div className="border-b border-gray-100 px-5 py-3">
                  <h2 className="text-sm font-semibold text-gray-700">依操作類型分佈</h2>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50/50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <th className="px-5 py-3">操作類型</th>
                      <th className="px-5 py-3 text-right">次數</th>
                      <th className="px-5 py-3 text-right">輸入 Tokens</th>
                      <th className="px-5 py-3 text-right">輸出 Tokens</th>
                      <th className="px-5 py-3 text-right">預估成本</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {byAction.map(item => (
                      <tr key={item.action_type} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3">
                          <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                            {item.action_type}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-sm text-gray-700 font-medium">{item.count.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right text-sm text-gray-500">{item.total_input_tokens.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right text-sm text-gray-500">{item.total_output_tokens.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right text-sm text-gray-700 font-medium">${item.total_cost.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
