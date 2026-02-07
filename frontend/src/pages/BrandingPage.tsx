import { useState, useEffect } from 'react'
import { companyApi } from '../api'
import { Palette, Save, Eye, MessageSquare, LayoutDashboard } from 'lucide-react'

interface BrandingData {
  brand_name: string
  brand_logo_url: string
  brand_primary_color: string
  brand_secondary_color: string
  brand_favicon_url: string
}

export default function BrandingPage() {
  const [form, setForm] = useState<BrandingData>({
    brand_name: '',
    brand_logo_url: '',
    brand_primary_color: '#2563eb',
    brand_secondary_color: '#1e40af',
    brand_favicon_url: '',
  })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    companyApi.branding().then((data: BrandingData) => {
      setForm({
        brand_name: data.brand_name || '',
        brand_logo_url: data.brand_logo_url || '',
        brand_primary_color: data.brand_primary_color || '#2563eb',
        brand_secondary_color: data.brand_secondary_color || '#1e40af',
        brand_favicon_url: data.brand_favicon_url || '',
      })
    })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMsg('')
    try {
      await companyApi.updateBranding(form as unknown as Record<string, unknown>)
      setMsg('品牌設定已儲存成功！下次載入時將套用新設定。')
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-auto">
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-3">
          <Palette className="h-6 w-6 text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">品牌設定（白標）</h1>
        </div>
        <p className="mt-1 text-sm text-gray-500">自訂您的品牌外觀，Pro / Enterprise 方案可用</p>
      </div>

      <div className="flex-1 p-6">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Brand Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">品牌名稱</label>
            <input
              value={form.brand_name}
              onChange={e => setForm({ ...form, brand_name: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="例：MyCompany HR"
            />
          </div>

          {/* Logo URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Logo URL</label>
            <input
              value={form.brand_logo_url}
              onChange={e => setForm({ ...form, brand_logo_url: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="https://example.com/logo.png"
            />
            {form.brand_logo_url && (
              <div className="mt-2 flex items-center gap-2">
                <Eye className="h-4 w-4 text-gray-400" />
                <img src={form.brand_logo_url} alt="Logo preview" className="h-8 object-contain" />
              </div>
            )}
          </div>

          {/* Colors */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">主色（Primary）</label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={form.brand_primary_color}
                  onChange={e => setForm({ ...form, brand_primary_color: e.target.value })}
                  className="h-10 w-10 cursor-pointer rounded border border-gray-300"
                />
                <input
                  value={form.brand_primary_color}
                  onChange={e => setForm({ ...form, brand_primary_color: e.target.value })}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="#2563eb"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">輔色（Secondary）</label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={form.brand_secondary_color}
                  onChange={e => setForm({ ...form, brand_secondary_color: e.target.value })}
                  className="h-10 w-10 cursor-pointer rounded border border-gray-300"
                />
                <input
                  value={form.brand_secondary_color}
                  onChange={e => setForm({ ...form, brand_secondary_color: e.target.value })}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="#1e40af"
                />
              </div>
            </div>
          </div>

          {/* Favicon URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Favicon URL</label>
            <input
              value={form.brand_favicon_url}
              onChange={e => setForm({ ...form, brand_favicon_url: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="https://example.com/favicon.ico"
            />
          </div>

          {/* Live Preview */}
          <div className="rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
              <Eye className="h-4 w-4" /> 即時預覽
            </h3>

            {/* Sidebar preview */}
            <div className="flex rounded-lg border border-gray-100 overflow-hidden" style={{ height: 200 }}>
              <div className="w-48 p-3 text-white flex flex-col" style={{ backgroundColor: form.brand_primary_color }}>
                <div className="flex items-center gap-2 mb-4">
                  {form.brand_logo_url ? (
                    <img src={form.brand_logo_url} alt="Logo" className="h-6 w-6 object-contain rounded" />
                  ) : (
                    <div className="h-6 w-6 rounded bg-white/20" />
                  )}
                  <span className="text-sm font-bold truncate">{form.brand_name || 'UniHR'}</span>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2 rounded px-2 py-1.5 bg-white/20">
                    <LayoutDashboard className="h-3 w-3" /> 儀表板
                  </div>
                  <div className="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-white/10">
                    <MessageSquare className="h-3 w-3" /> AI 問答
                  </div>
                </div>
              </div>
              <div className="flex-1 bg-gray-50 p-4">
                <div className="h-3 w-32 rounded bg-gray-200 mb-2" />
                <div className="h-2 w-48 rounded bg-gray-100 mb-4" />
                <div className="grid grid-cols-3 gap-2">
                  {[1,2,3].map(i => (
                    <div key={i} className="rounded-lg border border-gray-200 bg-white p-2">
                      <div className="h-2 w-12 rounded mb-1" style={{ backgroundColor: form.brand_primary_color, opacity: 0.6 }} />
                      <div className="h-4 w-8 rounded bg-gray-200" />
                    </div>
                  ))}
                </div>
                <button className="mt-3 rounded px-3 py-1 text-xs text-white" style={{ backgroundColor: form.brand_secondary_color }}>
                  按鈕樣式
                </button>
              </div>
            </div>
          </div>

          {/* Save */}
          {msg && (
            <p className={`text-sm ${msg.includes('成功') || msg.includes('已儲存') ? 'text-green-600' : 'text-red-600'}`}>{msg}</p>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? '儲存中...' : '儲存品牌設定'}
          </button>
        </div>
      </div>
    </div>
  )
}
