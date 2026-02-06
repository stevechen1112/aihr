import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { LogOut, ServerCog, Gauge, TrendingUp, Shield } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/', icon: ServerCog, label: '平台管理' },
  { to: '/quotas', icon: Gauge, label: '配額管理' },
  { to: '/analytics', icon: TrendingUp, label: '成本分析' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-gray-200 bg-white">
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 border-b border-gray-200 px-4">
          <Shield className="h-6 w-6 text-red-600" />
          <div>
            <span className="text-lg font-bold text-gray-900">UniHR</span>
            <span className="ml-1.5 rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-bold text-red-700">ADMIN</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-red-50 text-red-700'
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
            <p className="text-xs text-red-600 font-semibold">SUPERUSER</p>
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
