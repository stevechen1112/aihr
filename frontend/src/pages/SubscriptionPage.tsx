import { useState, useEffect } from 'react'
import { subscriptionApi } from '../api'
import { CreditCard, Check, ArrowUp, Zap } from 'lucide-react'

interface Plan {
  name: string
  display_name: string
  price_monthly_usd: number
  price_yearly_usd: number
  max_users: number | null
  max_documents: number | null
  max_storage_mb: number | null
  monthly_query_limit: number | null
  monthly_token_limit: number | null
  features: Record<string, boolean>
}

interface CurrentPlan {
  plan: string
  display_name: string
  features: Record<string, boolean>
  limits: Record<string, number | null>
  usage: Record<string, number>
  upgrade_available: boolean
}

const FEATURE_LABELS: Record<string, string> = {
  ai_chat: 'AI 智慧問答',
  document_upload: '文件上傳',
  basic_analytics: '基礎分析',
  audit_logs: '稽核日誌',
  sso: 'SSO 單一登入',
  white_label: '白標品牌',
  custom_domain: '自訂域名',
  api_access: 'API 存取',
  priority_support: '優先客服',
  data_export: '資料匯出',
  department_management: '部門管理',
  advanced_analytics: '進階分析',
}

export default function SubscriptionPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [current, setCurrent] = useState<CurrentPlan | null>(null)
  const [upgrading, setUpgrading] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    Promise.all([
      subscriptionApi.plans(),
      subscriptionApi.current(),
    ]).then(([p, c]) => {
      setPlans(p)
      setCurrent(c)
    })
  }, [])

  const handleUpgrade = async (planName: string) => {
    if (!confirm(`確定要升級至 ${planName.toUpperCase()} 方案？`)) return
    setUpgrading(true)
    setMsg('')
    try {
      const result = await subscriptionApi.upgrade(planName)
      setMsg(result.message)
      // Refresh current plan
      const c = await subscriptionApi.current()
      setCurrent(c)
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || '升級失敗')
    } finally {
      setUpgrading(false)
    }
  }

  const formatLimit = (val: number | null) => val === null ? '無限制' : val.toLocaleString()

  return (
    <div className="flex h-full flex-col overflow-auto">
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-3">
          <CreditCard className="h-6 w-6 text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">訂閱方案</h1>
        </div>
        <p className="mt-1 text-sm text-gray-500">查看目前方案、比較功能、升級取得更多能力</p>
      </div>

      <div className="flex-1 p-6">
        {/* Current Usage */}
        {current && (
          <div className="mb-8 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h2 className="text-lg font-semibold text-blue-800 flex items-center gap-2">
              <Zap className="h-5 w-5" />
              目前方案：{current.display_name}
            </h2>
            <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-blue-600">使用者</p>
                <p className="text-lg font-bold text-blue-900">
                  {current.usage.users} / {formatLimit(current.limits.max_users)}
                </p>
              </div>
              <div>
                <p className="text-xs text-blue-600">文件</p>
                <p className="text-lg font-bold text-blue-900">
                  {current.usage.documents} / {formatLimit(current.limits.max_documents)}
                </p>
              </div>
              <div>
                <p className="text-xs text-blue-600">本月查詢</p>
                <p className="text-lg font-bold text-blue-900">
                  {current.usage.monthly_queries?.toLocaleString()} / {formatLimit(current.limits.monthly_query_limit)}
                </p>
              </div>
              <div>
                <p className="text-xs text-blue-600">本月 Token</p>
                <p className="text-lg font-bold text-blue-900">
                  {current.usage.monthly_tokens?.toLocaleString()} / {formatLimit(current.limits.monthly_token_limit)}
                </p>
              </div>
            </div>
          </div>
        )}

        {msg && <p className={`mb-4 text-sm ${msg.includes('已升級') ? 'text-green-600' : 'text-red-600'}`}>{msg}</p>}

        {/* Plan Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map(plan => {
            const isCurrent = current?.plan === plan.name
            return (
              <div
                key={plan.name}
                className={`rounded-xl border-2 p-6 transition ${
                  isCurrent ? 'border-blue-500 bg-blue-50/50' : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="mb-4">
                  <h3 className="text-xl font-bold text-gray-900">{plan.display_name}</h3>
                  <p className="mt-1">
                    <span className="text-3xl font-bold text-gray-900">${plan.price_monthly_usd}</span>
                    <span className="text-sm text-gray-500"> /月</span>
                  </p>
                  {plan.price_yearly_usd > 0 && (
                    <p className="text-xs text-gray-400">年繳 ${plan.price_yearly_usd}/年（省 {Math.round((1 - plan.price_yearly_usd / (plan.price_monthly_usd * 12)) * 100)}%）</p>
                  )}
                </div>

                {/* Limits */}
                <div className="mb-4 space-y-1 text-sm text-gray-600">
                  <p>使用者：{formatLimit(plan.max_users)}</p>
                  <p>文件：{formatLimit(plan.max_documents)}</p>
                  <p>查詢：{formatLimit(plan.monthly_query_limit)}/月</p>
                </div>

                {/* Features */}
                <ul className="mb-6 space-y-2">
                  {Object.entries(plan.features).map(([key, enabled]) => (
                    <li key={key} className={`flex items-center gap-2 text-sm ${enabled ? 'text-gray-700' : 'text-gray-300 line-through'}`}>
                      <Check className={`h-4 w-4 ${enabled ? 'text-green-500' : 'text-gray-200'}`} />
                      {FEATURE_LABELS[key] || key}
                    </li>
                  ))}
                </ul>

                {/* Action */}
                {isCurrent ? (
                  <div className="rounded-lg bg-blue-100 px-4 py-2 text-center text-sm font-medium text-blue-700">
                    目前方案
                  </div>
                ) : current && current.upgrade_available && ['pro', 'enterprise'].includes(plan.name) && plan.name !== current.plan ? (
                  <button
                    onClick={() => handleUpgrade(plan.name)}
                    disabled={upgrading}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    <ArrowUp className="h-4 w-4" />
                    {upgrading ? '處理中...' : '升級'}
                  </button>
                ) : null}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
