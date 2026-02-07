import { useState, useEffect, useCallback } from 'react'
import { Globe, Plus, Trash2, Loader2, CheckCircle, AlertCircle, Copy, RefreshCw, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api'

interface CustomDomain {
  id: string
  domain: string
  verified: boolean
  verification_token: string
  ssl_provisioned: boolean
  created_at: string | null
}

interface VerifyResult {
  domain: string
  verified: boolean
  message: string
}

export default function CustomDomainsPage() {
  const [domains, setDomains] = useState<CustomDomain[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [verifying, setVerifying] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<CustomDomain[]>('/custom-domains/')
      setDomains(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const domain = newDomain.trim().toLowerCase()
    if (!domain) return
    setAdding(true)
    try {
      await api.post('/custom-domains/', { domain })
      toast.success('域名已新增，請依指示設定 DNS')
      setNewDomain('')
      setShowForm(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '新增失敗'
      toast.error(msg)
    } finally {
      setAdding(false)
    }
  }

  const handleVerify = async (id: string) => {
    setVerifying(id)
    try {
      const { data } = await api.post<VerifyResult>(`/custom-domains/${id}/verify`)
      if (data.verified) {
        toast.success(data.message)
      } else {
        toast.error(data.message)
      }
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '驗證失敗'
      toast.error(msg)
    } finally {
      setVerifying(null)
    }
  }

  const handleDelete = async (id: string, domain: string) => {
    if (!confirm(`確定要刪除域名 ${domain}？此操作無法復原。`)) return
    try {
      await api.delete(`/custom-domains/${id}`)
      toast.success('域名已刪除')
      load()
    } catch {
      toast.error('刪除失敗')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('已複製到剪貼簿')
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-auto">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Globe className="h-6 w-6 text-blue-600" />
              <h1 className="text-xl font-bold text-gray-900">自訂域名</h1>
            </div>
            <p className="mt-1 text-sm text-gray-500">設定您的品牌域名，需 Pro 或 Enterprise 方案</p>
          </div>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              新增域名
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 p-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Add form */}
          {showForm && (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
              <h3 className="mb-4 text-sm font-semibold text-blue-900">新增自訂域名</h3>
              <form onSubmit={handleAdd} className="flex gap-3">
                <input
                  type="text"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  placeholder="例如：hr.yourcompany.com"
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={adding || !newDomain.trim()}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {adding && <Loader2 className="h-4 w-4 animate-spin" />}
                  新增
                </button>
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setNewDomain('') }}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 transition-colors"
                >
                  取消
                </button>
              </form>
            </div>
          )}

          {/* Domain list */}
          {domains.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-gray-400">
              <Globe className="mb-3 h-12 w-12" />
              <p className="text-sm font-medium">尚未設定自訂域名</p>
              <p className="mt-1 text-xs">新增域名後，您的使用者可以透過您的品牌域名存取系統</p>
            </div>
          ) : (
            <div className="space-y-4">
              {domains.map((d) => (
                <div
                  key={d.id}
                  className="rounded-xl border border-gray-200 bg-white p-6"
                >
                  {/* Domain header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {d.verified ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <AlertCircle className="h-5 w-5 text-amber-500" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-900">{d.domain}</span>
                          <a
                            href={`https://${d.domain}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-gray-400 hover:text-blue-600"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                        <div className="mt-0.5 flex items-center gap-3">
                          <span className={`text-xs font-medium ${d.verified ? 'text-green-600' : 'text-amber-600'}`}>
                            {d.verified ? '已驗證' : '待驗證'}
                          </span>
                          {d.verified && (
                            <span className={`text-xs font-medium ${d.ssl_provisioned ? 'text-green-600' : 'text-gray-400'}`}>
                              {d.ssl_provisioned ? 'SSL 已啟用' : 'SSL 配置中'}
                            </span>
                          )}
                          {d.created_at && (
                            <span className="text-xs text-gray-400">
                              新增於 {new Date(d.created_at).toLocaleDateString('zh-TW')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!d.verified && (
                        <button
                          onClick={() => handleVerify(d.id)}
                          disabled={verifying === d.id}
                          className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50 transition-colors"
                        >
                          {verifying === d.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <RefreshCw className="h-3.5 w-3.5" />
                          )}
                          驗證
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(d.id, d.domain)}
                        className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        刪除
                      </button>
                    </div>
                  </div>

                  {/* DNS instructions (for unverified) */}
                  {!d.verified && (
                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <h4 className="mb-2 text-xs font-semibold text-amber-800">DNS 驗證步驟</h4>
                      <ol className="space-y-2 text-xs text-amber-700">
                        <li>
                          <span className="font-medium">1.</span> 在您的 DNS 管理介面新增一筆 <strong>TXT</strong> 記錄：
                        </li>
                        <li className="ml-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">名稱：</span>
                            <code className="rounded bg-amber-100 px-2 py-0.5 font-mono text-amber-900">
                              _unihr-verify.{d.domain}
                            </code>
                            <button
                              onClick={() => copyToClipboard(`_unihr-verify.${d.domain}`)}
                              className="text-amber-600 hover:text-amber-800"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </li>
                        <li className="ml-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">值：</span>
                            <code className="rounded bg-amber-100 px-2 py-0.5 font-mono text-amber-900">
                              {d.verification_token}
                            </code>
                            <button
                              onClick={() => copyToClipboard(d.verification_token)}
                              className="text-amber-600 hover:text-amber-800"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </li>
                        <li>
                          <span className="font-medium">2.</span> 等待 DNS 生效（通常需 5-30 分鐘）
                        </li>
                        <li>
                          <span className="font-medium">3.</span> 點擊上方「驗證」按鈕確認
                        </li>
                      </ol>
                      <p className="mt-3 text-xs text-amber-600">
                        此外，請新增 <strong>CNAME</strong> 記錄將 <code>{d.domain}</code> 指向 <code>app.unihr.com</code>
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
