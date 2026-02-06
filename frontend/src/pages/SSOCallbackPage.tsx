import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Loader2, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

/**
 * /login/callback
 * Handles the OAuth redirect. Reads ?code=...&state=tenantId from URL,
 * exchanges the code via backend, and redirects to /.
 */
export default function SSOCallbackPage() {
  const { loginWithSSO } = useAuth()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'error'>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state') || ''

    const tenantId = localStorage.getItem('sso_tenant_id') || ''
    const provider = localStorage.getItem('sso_provider') || ''
    const storedState = localStorage.getItem('sso_state') || ''
    const codeVerifier = localStorage.getItem('sso_code_verifier') || ''
    const redirectUri = `${window.location.origin}/login/callback`

    if (!code) {
      setStatus('error')
      setErrorMsg('未收到授權碼（code），請重新嘗試 SSO 登入。')
      return
    }
    if (!tenantId || !provider) {
      setStatus('error')
      setErrorMsg('缺少租戶 ID 或 SSO 提供者資訊，請重新嘗試。')
      return
    }
    if (!state || !storedState || state !== storedState) {
      setStatus('error')
      setErrorMsg('SSO 驗證狀態不一致，請重新嘗試。')
      return
    }
    if (!codeVerifier) {
      setStatus('error')
      setErrorMsg('缺少 PKCE 驗證資訊，請重新嘗試。')
      return
    }

    loginWithSSO(code, redirectUri, tenantId, provider, state, codeVerifier)
      .then(() => {
        toast.success('SSO 登入成功')
        localStorage.removeItem('sso_tenant_id')
        localStorage.removeItem('sso_provider')
        localStorage.removeItem('sso_state')
        localStorage.removeItem('sso_code_verifier')
        navigate('/', { replace: true })
      })
      .catch((err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'SSO 登入失敗'
        setStatus('error')
        setErrorMsg(msg)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl">
        {status === 'loading' ? (
          <>
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-blue-600" />
            <p className="text-sm text-gray-600">正在處理 SSO 登入，請稍候…</p>
          </>
        ) : (
          <>
            <AlertCircle className="mx-auto mb-4 h-10 w-10 text-red-500" />
            <p className="mb-2 text-sm font-medium text-red-700">{errorMsg}</p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              返回登入
            </button>
          </>
        )}
      </div>
    </div>
  )
}
