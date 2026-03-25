import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

export default function PublicSiteNav() {
  const { token } = useAuth()

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-100 bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link to="/" className="text-xl font-bold tracking-tight text-gray-900">
          Uni<span className="text-[#d15454]">HR</span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          <a href="/#features" className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900">
            功能介紹
          </a>
          <Link to="/pricing" className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900">
            方案與價格
          </Link>
          <a href="/#faq" className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900">
            常見問題
          </a>
          <a href="/#contact" className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900">
            聯絡我們
          </a>
        </div>

        <div className="flex items-center gap-3">
          {token ? (
            <Link
              to="/app"
              className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-black"
            >
              前往工作台
            </Link>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900">
                登入
              </Link>
              <Link
                to="/signup"
                className="rounded-lg bg-[#d15454] px-5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#c04444]"
              >
                免費開始
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}