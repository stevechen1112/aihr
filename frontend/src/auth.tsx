import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { authApi, ssoApi, type LoginResponse } from './api'
import type { User } from './types'

const AUTH_BOOTSTRAP_TIMEOUT_MS = 5000

function withTimeout<T>(promise: Promise<T>, timeoutMs = AUTH_BOOTSTRAP_TIMEOUT_MS): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error('auth bootstrap timeout'))
    }, timeoutMs)

    promise
      .then((value) => {
        window.clearTimeout(timer)
        resolve(value)
      })
      .catch((error) => {
        window.clearTimeout(timer)
        reject(error)
      })
  })
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<LoginResponse>
  completeMfaLogin: (mfaToken: string, code: string) => Promise<void>
  loginWithSSO: (code: string, redirectUri: string, tenantId: string, provider: string, state: string, codeVerifier: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    try {
      const u = await withTimeout(authApi.me())
      setUser(u)
      setToken('cookie-session')
    } catch {
      try {
        await withTimeout(authApi.refresh({ silent: true }))
        const u = await withTimeout(authApi.me())
        setUser(u)
        setToken('cookie-session')
      } catch {
        setToken(null)
        setUser(null)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const login = async (email: string, password: string) => {
    const result = await authApi.login(email, password)
    if (!result.mfa_required) {
      await fetchUser()
    }
    return result
  }

  const completeMfaLogin = async (mfaToken: string, code: string) => {
    await authApi.verifyMfaLogin(mfaToken, code)
    await fetchUser()
  }

  const loginWithSSO = async (code: string, redirectUri: string, tenantId: string, provider: string, state: string, codeVerifier: string) => {
    await ssoApi.callback({
      code,
      redirect_uri: redirectUri,
      tenant_id: tenantId,
      provider,
      state,
      code_verifier: codeVerifier,
    })
    await fetchUser()
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore logout errors and clear local state anyway
    }
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, completeMfaLogin, loginWithSSO, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
