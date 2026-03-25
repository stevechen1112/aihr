import { Link } from 'react-router-dom'

export default function PublicSiteFooter() {
  return (
    <footer className="border-t border-gray-100 bg-gray-50 py-12">
      <div className="mx-auto grid max-w-6xl gap-8 px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <p className="text-lg font-bold text-gray-900">
            Uni<span className="text-[#d15454]">HR</span>
          </p>
          <p className="mt-3 max-w-md text-sm leading-6 text-gray-500">
            企業專屬AI人資長，讓規章制度、文件知識庫與日常問答在同一個平台完成。
          </p>
        </div>

        <div>
          <p className="text-sm font-semibold text-gray-900">快速導覽</p>
          <div className="mt-3 flex flex-col gap-2 text-sm text-gray-500">
            <a href="/#features" className="transition-colors hover:text-gray-700">功能介紹</a>
            <Link to="/pricing" className="transition-colors hover:text-gray-700">方案與價格</Link>
            <a href="/#faq" className="transition-colors hover:text-gray-700">常見問題</a>
            <Link to="/login" className="transition-colors hover:text-gray-700">登入</Link>
          </div>
        </div>

        <div>
          <p className="text-sm font-semibold text-gray-900">聯絡與法務</p>
          <div className="mt-3 flex flex-col gap-2 text-sm text-gray-500">
            <a href="mailto:support@unihr.app" className="transition-colors hover:text-gray-700">support@unihr.app</a>
            <a href="mailto:sales@unihr.app" className="transition-colors hover:text-gray-700">sales@unihr.app</a>
            <Link to="/terms" className="transition-colors hover:text-gray-700">服務條款</Link>
            <Link to="/privacy" className="transition-colors hover:text-gray-700">隱私權政策</Link>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-8 max-w-6xl border-t border-gray-200 px-6 pt-6 text-sm text-gray-400">
        &copy; {new Date().getFullYear()} UniHR. All rights reserved.
      </div>
    </footer>
  )
}