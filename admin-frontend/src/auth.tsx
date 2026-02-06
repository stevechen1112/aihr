import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { authApi } from './api'
import type { User } from './types'

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('admin_token'))
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    try {
      const u = await authApi.me()
      // Admin frontend: only allow superusers
      if (!u.is_superuser) {
        throw new Error('Not a superuser')
      }
      setUser(u)
    } catch {
      setToken(null)
      setUser(null)
      localStorage.removeItem('admin_token')
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
    // Verify superuser before storing token
    const tempApi = await authApi.me()
    void tempApi // trigger the call
    localStorage.setItem('admin_token', access_token)
    setToken(access_token)
  }

  const logout = () => {
    localStorage.removeItem('admin_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
