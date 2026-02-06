import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { MessageSquare, FileText, BarChart3, LogOut, Shield, ClipboardList, Building2, ServerCog, KeyRound, Gauge, TrendingUp } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/', icon: MessageSquare, label: 'AI 問答' },
  { to: '/documents', icon: FileText, label: '文件管理' },
  { to: '/usage', icon: BarChart3, label: '用量統計', roles: ['owner', 'admin'] },
  { to: '/audit', icon: ClipboardList, label: '稽核日誌', roles: ['owner', 'admin'] },
  { to: '/departments', icon: Building2, label: '部門管理', roles: ['owner', 'admin', 'hr'] },
  { to: '/company', icon: Building2, label: '公司管理', roles: ['owner', 'admin'] },
  { to: '/sso-settings', icon: KeyRound, label: 'SSO 設定', roles: ['owner', 'admin'] },
  { to: '/admin', icon: ServerCog, label: '平台管理', superuserOnly: true },
  { to: '/admin/quotas', icon: Gauge, label: '配額管理', superuserOnly: true },
  { to: '/analytics', icon: TrendingUp, label: '成本分析', superuserOnly: true },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleNav = navItems.filter(item => {
    if ((item as any).superuserOnly) return user?.is_superuser === true
    return !item.roles || item.roles.includes(user?.role ?? '')
  })

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-gray-200 bg-white">
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 border-b border-gray-200 px-4">
          <Shield className="h-6 w-6 text-blue-600" />
          <span className="text-lg font-bold text-gray-900">UniHR</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {visibleNav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="border-t border-gray-200 p-4">
          <div className="mb-2">
            <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name || user?.email}</p>
            <p className="text-xs text-gray-500">{user?.role?.toUpperCase()}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            登出
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
