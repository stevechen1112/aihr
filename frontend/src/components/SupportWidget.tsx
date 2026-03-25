import { useEffect, useState } from 'react'
import { LifeBuoy, Mail, BookOpen, Calendar, X } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { publicApi } from '../api'

interface SupportConfig {
  enabled: boolean
  email: string
  docs_url: string
  booking_url: string
}

export default function SupportWidget() {
  const [config, setConfig] = useState<SupportConfig | null>(null)
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    publicApi.support().then(setConfig).catch(() => null)
  }, [])

  if (!config?.enabled) return null

  const wrapperClass = location.pathname === '/'
    || location.pathname === '/pricing'
    || location.pathname === '/signup'
    ? 'pointer-events-none fixed right-5 bottom-24 z-40 flex flex-col items-end gap-3 md:bottom-28'
    : 'pointer-events-none fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3'

  return (
    <div className={wrapperClass}>
      {open && (
        <div className="pointer-events-auto w-80 rounded-2xl border border-gray-200 bg-white p-5 shadow-2xl shadow-black/10">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">需要協助？</p>
              <p className="mt-1 text-xs text-gray-500">透過文件、Email 或預約支援與 UniHR 團隊聯繫。</p>
            </div>
            <button onClick={() => setOpen(false)} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-2 text-sm">
            <a href={config.docs_url} target="_blank" rel="noreferrer" className="flex items-center gap-3 rounded-xl border border-gray-200 px-4 py-3 text-gray-700 hover:bg-gray-50">
              <BookOpen className="h-4 w-4 text-blue-600" />
              <div>
                <p className="font-medium">查看說明文件</p>
                <p className="text-xs text-gray-500">部署、設定與常見問題</p>
              </div>
            </a>

            <a href={`mailto:${config.email}`} className="flex items-center gap-3 rounded-xl border border-gray-200 px-4 py-3 text-gray-700 hover:bg-gray-50">
              <Mail className="h-4 w-4 text-emerald-600" />
              <div>
                <p className="font-medium">Email 支援</p>
                <p className="text-xs text-gray-500">{config.email}</p>
              </div>
            </a>

            <a href={config.booking_url} target="_blank" rel="noreferrer" className="flex items-center gap-3 rounded-xl border border-gray-200 px-4 py-3 text-gray-700 hover:bg-gray-50">
              <Calendar className="h-4 w-4 text-amber-600" />
              <div>
                <p className="font-medium">預約協助</p>
                <p className="text-xs text-gray-500">安排導入或技術支援時段</p>
              </div>
            </a>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen(value => !value)}
        className="pointer-events-auto inline-flex items-center gap-2 rounded-full bg-gray-900 px-4 py-3 text-sm font-medium text-white shadow-lg shadow-black/20 hover:bg-black"
      >
        <LifeBuoy className="h-4 w-4" />
        支援
      </button>
    </div>
  )
}