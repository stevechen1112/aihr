import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { authApi, ssoApi } from './api'
import type { User } from './types'

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  loginWithSSO: (code: string, redirectUri: string, tenantId: string, provider: string, state: string, codeVerifier: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    try {
      const u = await authApi.me()
      setUser(u)
    } catch {
      setToken(null)
      setUser(null)
      localStorage.removeItem('token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (token) {
      fetchUser()
    } else {
      setLoading(false)
    }
  }, [token, fetchUser])

  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    localStorage.setItem('token', access_token)
    setToken(access_token)
  }

  const loginWithSSO = async (code: string, redirectUri: string, tenantId: string, provider: string, state: string, codeVerifier: string) => {
    const { access_token } = await ssoApi.callback({
      code,
      redirect_uri: redirectUri,
      tenant_id: tenantId,
      provider,
      state,
      code_verifier: codeVerifier,
    })
    localStorage.setItem('token', access_token)
    setToken(access_token)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, loginWithSSO, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
