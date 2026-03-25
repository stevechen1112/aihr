import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, ArrowRight, Minus } from 'lucide-react'
import PublicSiteNav from '../components/PublicSiteNav'
import PublicSiteFooter from '../components/PublicSiteFooter'

const PLANS = [
  {
    name: 'free',
    display: 'Free',
    desc: '適合初期體驗',
    monthly_twd: 0,
    yearly_twd: 0,
    monthly_usd: 0,
    yearly_usd: 0,
    limits: { users: '5', docs: '20', queries: '500 / 月', storage: '100 MB' },
    features: {
      ai_chat: true, document_upload: true, basic_analytics: true,
      audit_logs: false, sso: false, white_label: false, custom_domain: false,
      api_access: false, priority_support: false, department_management: false,
    },
    cta: '免費開始',
    highlight: false,
  },
  {
    name: 'pro',
    display: 'Pro',
    desc: '成長中的團隊',
    monthly_twd: 890,
    yearly_twd: 8900,
    monthly_usd: 29,
    yearly_usd: 290,
    limits: { users: '50', docs: '200', queries: '5,000 / 月', storage: '1 GB' },
    features: {
      ai_chat: true, document_upload: true, basic_analytics: true,
      audit_logs: true, sso: true, white_label: true, custom_domain: false,
      api_access: true, priority_support: true, department_management: true,
    },
    cta: '選擇 Pro',
    highlight: true,
  },
  {
    name: 'enterprise',
    display: 'Enterprise',
    desc: '大型企業',
    monthly_twd: 2990,
    yearly_twd: 29900,
    monthly_usd: 99,
    yearly_usd: 990,
    limits: { users: '無限制', docs: '無限制', queries: '無限制', storage: '無限制' },
    features: {
      ai_chat: true, document_upload: true, basic_analytics: true,
      audit_logs: true, sso: true, white_label: true, custom_domain: true,
      api_access: true, priority_support: true, department_management: true,
    },
    cta: '聯絡我們',
    highlight: false,
  },
]

const FEATURE_LABELS: Record<string, string> = {
  ai_chat: 'AI 智慧問答',
  document_upload: '文件上傳與解析',
  basic_analytics: '基礎分析',
  audit_logs: '稽核日誌',
  sso: 'SSO 單一登入',
  white_label: '白標品牌',
  custom_domain: '自訂域名',
  api_access: 'API 存取',
  priority_support: '優先客服',
  department_management: '部門管理',
}

export default function PricingPage() {
  const [annual, setAnnual] = useState(false)
  const [currency, setCurrency] = useState<'twd' | 'usd'>('twd')

  const getPrice = (plan: typeof PLANS[0]) => {
    if (plan.name === 'free') return '免費'
    const price = annual
      ? currency === 'twd' ? plan.yearly_twd : plan.yearly_usd
      : currency === 'twd' ? plan.monthly_twd : plan.monthly_usd
    const symbol = currency === 'twd' ? 'NT$' : '$'
    return `${symbol}${price.toLocaleString()}`
  }

  const getPeriod = () => annual ? '/年' : '/月'

  return (
    <div className="min-h-screen bg-white">
      <PublicSiteNav />

      {/* Header */}
      <section className="bg-gradient-to-b from-rose-50/50 to-white pb-10 pt-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h1 className="text-4xl font-extrabold text-gray-900">簡單透明的定價</h1>
          <p className="mt-4 text-lg text-gray-500">從免費開始，隨著團隊成長升級。</p>

          {/* Toggle */}
          <div className="mt-8 flex items-center justify-center gap-6">
            <div className="flex items-center gap-3 rounded-full border border-gray-200 bg-gray-50 p-1">
              <button
                onClick={() => setAnnual(false)}
                className={`rounded-full px-5 py-2 text-sm font-medium transition-all ${!annual ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}
              >
                月繳
              </button>
              <button
                onClick={() => setAnnual(true)}
                className={`rounded-full px-5 py-2 text-sm font-medium transition-all ${annual ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}
              >
                年繳 <span className="text-xs text-emerald-600 font-semibold">省 17%</span>
              </button>
            </div>
            <button
              onClick={() => setCurrency(c => c === 'twd' ? 'usd' : 'twd')}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50 transition-colors"
            >
              {currency === 'twd' ? 'TWD → USD' : 'USD → TWD'}
            </button>
          </div>
        </div>
      </section>

      {/* Plan Cards */}
      <section className="py-10">
        <div className="mx-auto grid max-w-5xl gap-6 px-6 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative flex flex-col rounded-2xl border p-8 transition-shadow ${
                plan.highlight
                  ? 'border-[#d15454] shadow-lg shadow-rose-100'
                  : 'border-gray-200 shadow-sm hover:shadow-md'
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#d15454] px-4 py-1 text-xs font-semibold text-white shadow">
                  最受歡迎
                </div>
              )}
              <h3 className="text-lg font-bold text-gray-900">{plan.display}</h3>
              <p className="mt-1 text-sm text-gray-500">{plan.desc}</p>
              <div className="mt-6">
                <span className="text-4xl font-extrabold text-gray-900">{getPrice(plan)}</span>
                {plan.name !== 'free' && (
                  <span className="ml-1 text-base text-gray-400">{getPeriod()}</span>
                )}
              </div>

              {/* Limits */}
              <ul className="mt-6 space-y-2.5 text-sm text-gray-600">
                {Object.entries(plan.limits).map(([k, v]) => (
                  <li key={k} className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                    <span>{k === 'users' ? '使用者' : k === 'docs' ? '文件' : k === 'queries' ? '查詢' : '儲存空間'} {v}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <div className="mt-auto pt-8">
                {plan.name === 'enterprise' ? (
                  <a
                    href="mailto:sales@example.com"
                    className="block w-full rounded-xl border border-gray-200 bg-white py-3 text-center text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    {plan.cta}
                  </a>
                ) : (
                  <Link
                    to="/signup"
                    className={`block w-full rounded-xl py-3 text-center text-sm font-semibold transition-colors ${
                      plan.highlight
                        ? 'bg-[#d15454] text-white shadow-sm hover:bg-[#c04444]'
                        : 'bg-gray-900 text-white hover:bg-gray-800'
                    }`}
                  >
                    {plan.cta}
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Feature Comparison */}
      <section className="border-t border-gray-100 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-10 text-center text-2xl font-bold text-gray-900">功能比較</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 text-left font-medium text-gray-500">功能</th>
                  {PLANS.map((p) => (
                    <th key={p.name} className="py-3 text-center font-semibold text-gray-900">{p.display}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(FEATURE_LABELS).map(([key, label]) => (
                  <tr key={key} className="border-b border-gray-100">
                    <td className="py-3 text-gray-600">{label}</td>
                    {PLANS.map((p) => (
                      <td key={p.name} className="py-3 text-center">
                        {p.features[key as keyof typeof p.features] ? (
                          <Check className="mx-auto h-5 w-5 text-emerald-500" />
                        ) : (
                          <Minus className="mx-auto h-5 w-5 text-gray-300" />
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-gray-100 bg-gray-50/50 py-16">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-center text-2xl font-bold text-gray-900">常見問題</h2>
          <div className="mt-10 space-y-6">
            {[
              { q: '免費方案有使用期限嗎？', a: '沒有，免費方案永久有效。額度用完可升級 Pro 方案。' },
              { q: '可以隨時升級嗎？', a: '可以，升級後立即生效，費用按比例計算。' },
              { q: '支援哪些付款方式？', a: '透過藍新金流支援信用卡、ATM 轉帳等台灣主流付款方式。' },
              { q: '資料存放在哪裡？', a: '預設存放於台灣（AWS AP-Northeast），符合個人資料保護法。' },
            ].map((faq) => (
              <div key={faq.q} className="rounded-xl border border-gray-100 bg-white p-5">
                <h3 className="font-semibold text-gray-900">{faq.q}</h3>
                <p className="mt-2 text-sm text-gray-500">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-2xl font-bold text-gray-900">準備好開始了？</h2>
          <Link
            to="/signup"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[#d15454] px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-rose-200/50 hover:bg-[#c04444] transition-all"
          >
            免費註冊
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <PublicSiteFooter />
    </div>
  )
}
