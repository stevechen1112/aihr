import { useState, useEffect } from 'react'
import { ssoApi } from '../api'
import { Loader2, Plus, Trash2, Shield, AlertCircle, CheckCircle2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface SSOConfigItem {
  id: string
  tenant_id: string
  provider: string
  client_id: string
  client_secret: string
  enabled: boolean
  allowed_domains: string[]
  auto_create_user: boolean
  default_role: string
}

const PROVIDERS = ['google', 'microsoft'] as const

export default function SSOSettingsPage() {
  const [configs, setConfigs] = useState<SSOConfigItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  // Form state
  const [provider, setProvider] = useState<string>('google')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [domains, setDomains] = useState('')
  const [autoCreate, setAutoCreate] = useState(true)
  const [defaultRole, setDefaultRole] = useState('employee')
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    ssoApi.listConfigs().then(setConfigs).catch(() => []).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setProvider('google')
    setClientId('')
    setClientSecret('')
    setEnabled(true)
    setDomains('')
    setAutoCreate(true)
    setDefaultRole('employee')
    setShowForm(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await ssoApi.createConfig({
        provider,
        client_id: clientId,
        client_secret: clientSecret,
        enabled,
        allowed_domains: domains ? domains.split(',').map(d => d.trim()).filter(Boolean) : [],
        auto_create_user: autoCreate,
        default_role: defaultRole,
      })
      toast.success('SSO 設定已儲存')
      resetForm()
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '儲存失敗'
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (prov: string) => {
    if (!confirm(`確定刪除 ${prov} SSO 設定？`)) return
    try {
      await ssoApi.deleteConfig(prov)
      toast.success('已刪除')
      load()
    } catch {
      toast.error('刪除失敗')
    }
  }

  const handleToggle = async (cfg: SSOConfigItem) => {
    try {
      await ssoApi.updateConfig(cfg.provider, { enabled: !cfg.enabled })
      toast.success(cfg.enabled ? '已停用' : '已啟用')
      load()
    } catch {
      toast.error('更新失敗')
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-indigo-600" />
            <h1 className="text-lg font-semibold text-gray-900">SSO 設定</h1>
          </div>
          {!showForm && (
            <button onClick={() => setShowForm(true)} className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">
              <Plus className="h-4 w-4" /> 新增 Provider
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Create form */}
        {showForm && (
          <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-gray-700">新增 SSO Provider</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Provider</label>
                <select value={provider} onChange={e => setProvider(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {PROVIDERS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Default Role</label>
                <select value={defaultRole} onChange={e => setDefaultRole(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {['employee', 'viewer', 'hr', 'admin'].map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-500 mb-1">Client ID</label>
                <input type="text" value={clientId} onChange={e => setClientId(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono" />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-500 mb-1">Client Secret</label>
                <input type="password" value={clientSecret} onChange={e => setClientSecret(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono" />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-500 mb-1">Allowed Domains（逗號分隔，空白=不限制）</label>
                <input type="text" value={domains} onChange={e => setDomains(e.target.value)} placeholder="example.com, corp.example.com"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} className="rounded" /> 啟用
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={autoCreate} onChange={e => setAutoCreate(e.target.checked)} className="rounded" /> 自動建立用戶
                </label>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={resetForm} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">取消</button>
              <button onClick={handleSave} disabled={saving || !clientId || !clientSecret}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving && <Loader2 className="h-3 w-3 animate-spin" />} 儲存
              </button>
            </div>
          </div>
        )}

        {/* Existing configs */}
        {loading ? (
          <div className="flex h-40 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : configs.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-gray-400">
            <AlertCircle className="mb-3 h-10 w-10" />
            <p className="text-sm">尚未設定 SSO Provider</p>
          </div>
        ) : (
          <div className="space-y-3">
            {configs.map(cfg => (
              <div key={cfg.provider} className="rounded-xl border border-gray-200 bg-white p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${cfg.enabled ? 'bg-green-50' : 'bg-gray-100'}`}>
                    {cfg.enabled ? <CheckCircle2 className="h-5 w-5 text-green-600" /> : <AlertCircle className="h-5 w-5 text-gray-400" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{cfg.provider.charAt(0).toUpperCase() + cfg.provider.slice(1)}</p>
                    <p className="text-xs text-gray-500">
                      Client ID: {cfg.client_id.slice(0, 12)}… &middot; Role: {cfg.default_role}
                      {cfg.allowed_domains.length > 0 && <> &middot; Domains: {cfg.allowed_domains.join(', ')}</>}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleToggle(cfg)}
                    className={`rounded-full px-3 py-1 text-xs font-medium ${cfg.enabled ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                    {cfg.enabled ? '已啟用' : '已停用'}
                  </button>
                  <button onClick={() => handleDelete(cfg.provider)}
                    className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
