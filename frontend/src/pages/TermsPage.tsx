import { Link } from 'react-router-dom'
import PublicSiteFooter from '../components/PublicSiteFooter'
import PublicSiteNav from '../components/PublicSiteNav'

const sections = [
  {
    title: '1. 服務內容與範圍',
    items: [
      'UniHR 提供企業 HR 知識庫、文件解析、AI 問答、租戶管理與相關 SaaS 功能（以下稱「本服務」）。',
      '本服務為企業訂閱制雲端軟體，非勞動法律諮詢服務。AI 產生之回覆僅供參考，不構成法律意見。',
      '我們得為維護安全、效能或符合法規要求調整功能、限制使用或安排維護時段，並將合理提前通知。',
    ],
  },
  {
    title: '2. 帳號註冊與管理',
    items: [
      '本服務採邀請制註冊，由租戶管理員邀請成員加入。接受邀請即表示同意本條款及隱私權政策。',
      '客戶應妥善管理帳號安全、角色權限與邀請流程，並確保所有使用者皆已了解並同意本條款。',
      '如發現帳號遭未授權存取，應立即通知本公司。',
    ],
  },
  {
    title: '3. 客戶責任',
    items: [
      '客戶須確保上傳內容合法且具備適當權利，不得上傳侵權、違法或含惡意程式之檔案。',
      '不得利用本服務進行違法行為、逆向工程、惡意掃描、超量存取或其他破壞性行為。',
      '客戶應對其員工之使用行為負責，包括但不限於資料上傳與 AI 查詢內容。',
    ],
  },
  {
    title: '4. 費用與付款',
    items: [
      '付費方案依網站公告方案頁或個別報價單所載內容收費，以新臺幣計價。',
      '付款透過藍新金流（NewebPay）處理，本公司不儲存付款卡號。',
      '訂閱自付款成功日起算，到期未續約者，服務將於到期日後暫停存取（資料保留 30 天）。',
      '已付費用除法律規定外，恕不退還。',
    ],
  },
  {
    title: '5. 資料所有權與智慧財產',
    items: [
      '客戶保有其上傳內容與資料之一切權利。本公司僅在提供服務所必要範圍內處理客戶資料。',
      'UniHR 平台本身（軟體、介面、演算法、文件）之智慧財產權歸本公司所有。',
      'AI 回覆內容基於客戶資料與公開知識生成，客戶得自由使用，但應自行判斷其正確性。',
    ],
  },
  {
    title: '6. 個人資料保護',
    items: [
      '本公司依中華民國個人資料保護法蒐集、處理及利用個人資料，詳見「隱私權政策」。',
      '客戶作為其員工個資之管理者，應確保已取得員工同意或具備合法蒐集基礎。',
      '本公司提供資料匯出與刪除功能，以協助客戶履行個資法第 3 條所定當事人權利。',
    ],
  },
  {
    title: '7. 服務水準與責任限制',
    items: [
      '本公司致力維持合理之服務可用性，但不保證 100% 不中斷。',
      '如因第三方服務（雲端供應商、AI 模型供應商）異常導致服務受影響，本公司不負超出法定範圍之責任。',
      'AI 回覆可能包含錯誤或過時資訊，客戶應自行驗證並承擔使用風險。',
      '本公司就本服務之最大賠償責任，以客戶最近 12 個月已付費用總額為限。',
    ],
  },
  {
    title: '8. 終止與資料處理',
    items: [
      '任一方得提前 30 日以書面通知終止服務。重大違約或未付款達 30 日以上，本公司得立即暫停服務。',
      '終止後，客戶得於 30 日內匯出其資料。逾期後本公司將刪除客戶資料（法令要求保留者除外）。',
      '本條款第 5（智慧財產）、第 6（個資保護）、第 7（責任限制）條於終止後仍有效力。',
    ],
  },
  {
    title: '9. 準據法與管轄',
    items: [
      '本條款以中華民國法律為準據法。',
      '因本條款所生之爭議，雙方同意以臺灣臺北地方法院為第一審管轄法院。',
    ],
  },
]

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[linear-gradient(135deg,#fffaf5_0%,#fff3f0_55%,#f8ede8_100%)] text-gray-900">
      <PublicSiteNav />
      <div className="px-4 py-10">
      <div className="mx-auto max-w-4xl overflow-hidden rounded-[32px] border border-white/70 bg-white/90 shadow-2xl backdrop-blur">
        <div className="border-b border-orange-100 bg-[radial-gradient(circle_at_top_right,_rgba(251,146,60,0.14),_transparent_38%),linear-gradient(135deg,#fff,#fff7ed)] px-8 py-10 md:px-12">
          <p className="text-sm font-medium uppercase tracking-[0.28em] text-orange-600">UniHR Legal</p>
          <h1 className="mt-3 text-3xl font-bold md:text-4xl">服務條款</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-600 md:text-base">
            本條款規範 UniHR SaaS 服務的使用方式、雙方責任、權利歸屬與終止機制。生效日為 2026-03-23。
          </p>
        </div>

        <div className="space-y-8 px-8 py-10 md:px-12">
          {sections.map((section) => (
            <section key={section.title} className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">{section.title}</h2>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-gray-700">
                {section.items.map((item) => (
                  <li key={item} className="rounded-xl bg-orange-50/70 px-4 py-3">{item}</li>
                ))}
              </ul>
            </section>
          ))}

          <section className="rounded-2xl border border-dashed border-orange-200 bg-orange-50/70 px-6 py-5 text-sm leading-6 text-gray-700">
            如需企業版主契約、DPA 或 SLA 補充條款，請聯繫 legal@unihr.app。
          </section>

          <div className="flex items-center justify-between gap-4 border-t border-gray-100 pt-6 text-sm text-gray-500">
            <span>最後更新：2026-03-23</span>
            <Link to="/" className="font-medium text-orange-600 transition-colors hover:text-orange-700">返回首頁</Link>
          </div>
        </div>
      </div>
      </div>
      <PublicSiteFooter />
    </div>
  )
}