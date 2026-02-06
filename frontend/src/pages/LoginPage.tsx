import { useState } from 'react'
import { useAuth } from '../auth'
import { ssoApi } from '../api'
import { Shield, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

// ─── SSO helpers ───
const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
const MICROSOFT_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'

function randomString(size = 64) {
  const bytes = new Uint8Array(size)
  window.crypto.getRandomValues(bytes)
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
  return Array.from(bytes, (b) => chars[b % chars.length]).join('')
}

async function sha256Base64Url(value: string) {
  const data = new TextEncoder().encode(value)
  const digest = await window.crypto.subtle.digest('SHA-256', data)
  const bytes = new Uint8Array(digest)
  let str = ''
  for (const b of bytes) str += String.fromCharCode(b)
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

// ─── SSO provider icons ───
function GoogleIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}

function MicrosoftIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 21 21">
      <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
      <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
      <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
    </svg>
  )
}

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [showSSO, setShowSSO] = useState(false)
  const [tenantId, setTenantId] = useState('')
  const [googleClientId, setGoogleClientId] = useState('')
  const [msClientId, setMsClientId] = useState('')

  const startSSO = async (provider: 'google' | 'microsoft', clientId: string) => {
    if (!tenantId || !clientId) return

    try {
      const { state } = await ssoApi.state({ tenant_id: tenantId, provider })

      const codeVerifier = randomString(64)
      const codeChallenge = await sha256Base64Url(codeVerifier)

      localStorage.setItem('sso_tenant_id', tenantId)
      localStorage.setItem('sso_provider', provider)
      localStorage.setItem('sso_state', state)
      localStorage.setItem('sso_code_verifier', codeVerifier)

      const redirectUri = `${window.location.origin}/login/callback`

      if (provider === 'google') {
        const params = new URLSearchParams({
          client_id: clientId,
          redirect_uri: redirectUri,
          response_type: 'code',
          scope: 'openid email profile',
          access_type: 'offline',
          prompt: 'consent',
          state,
          code_challenge: codeChallenge,
          code_challenge_method: 'S256',
        })
        window.location.href = `${GOOGLE_AUTH_URL}?${params}`
      } else {
        const params = new URLSearchParams({
          client_id: clientId,
          redirect_uri: redirectUri,
          response_type: 'code',
          scope: 'openid profile email User.Read',
          state,
          code_challenge: codeChallenge,
          code_challenge_method: 'S256',
        })
        window.location.href = `${MICROSOFT_AUTH_URL}?${params}`
      }
    } catch {
      toast.error('取得 SSO 授權失敗，請稍後再試')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      toast.success('登入成功')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '登入失敗'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600 shadow-lg">
            <Shield className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">UniHR</h1>
          <p className="mt-1 text-sm text-gray-500">企業人資 AI 助理平台</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="rounded-2xl bg-white p-8 shadow-xl">
          <h2 className="mb-6 text-lg font-semibold text-gray-900">歡迎登入</h2>

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">電子郵件</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-shadow"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">密碼</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-shadow"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? '登入中...' : '登入'}
          </button>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
            <div className="relative flex justify-center">
              <button type="button" onClick={() => setShowSSO(!showSSO)} className="bg-white px-3 text-xs text-gray-400 hover:text-gray-600 transition-colors">
                {showSSO ? '隱藏 SSO 登入' : '使用 SSO 登入'}
              </button>
            </div>
          </div>

          {/* SSO Section */}
          {showSSO && (
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">租戶 ID（請向管理員確認）</label>
                <input type="text" value={tenantId} onChange={(e) => setTenantId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs font-mono focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Google Client ID（選填）</label>
                <input type="text" value={googleClientId} onChange={(e) => setGoogleClientId(e.target.value)}
                  placeholder="xxxxx.apps.googleusercontent.com"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs font-mono focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Microsoft Client ID（選填）</label>
                <input type="text" value={msClientId} onChange={(e) => setMsClientId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs font-mono focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button type="button" disabled={!tenantId || !googleClientId}
                  onClick={() => startSSO('google', googleClientId)}
                  className="flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors">
                  <GoogleIcon /> Google
                </button>
                <button type="button" disabled={!tenantId || !msClientId}
                  onClick={() => startSSO('microsoft', msClientId)}
                  className="flex items-center justify-center gap-2 rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors">
                  <MicrosoftIcon /> Microsoft
                </button>
              </div>
            </div>
          )}
        </form>

        <p className="mt-4 text-center text-xs text-gray-400">
          © 2026 UniHR. All rights reserved.
        </p>
      </div>
    </div>
  )
}
