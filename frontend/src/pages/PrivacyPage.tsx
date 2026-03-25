import { Link } from 'react-router-dom'
import PublicSiteNav from '../components/PublicSiteNav'
import PublicSiteFooter from '../components/PublicSiteFooter'

const sections = [
  {
    title: '1. 蒐集之個人資料類別（個資法第 8 條第 1 項第 3 款）',
    items: [
      '帳號資料：姓名、電子郵件、職稱、公司名稱與登入紀錄。',
      '服務資料：上傳文件內容、AI 問答對話紀錄、搜尋紀錄與租戶設定。',
      '技術資料：IP 位址、裝置與瀏覽器資訊、存取時間與安全稽核日誌。',
      '付款資料：交易編號、方案名稱、金額（付款卡號由藍新金流處理，本公司不保存）。',
    ],
  },
  {
    title: '2. 蒐集目的（個資法第 8 條第 1 項第 2 款）',
    items: [
      '「○六○　契約、類似契約或其他法律關係事務」：提供 UniHR SaaS 服務（文件檢索、AI 問答、租戶管理）。',
      '「○六九　契約、類似契約或其他法律關係管理之事務」：帳務通知、方案續約與客戶支援。',
      '「一三六　資（通）訊與資料庫管理」：維護服務穩定性、資安防護與故障排除。',
      '「一八二　其他經營合於營業登記項目或組織章程所定之業務」：產品改進與匿名統計分析。',
    ],
  },
  {
    title: '3. 利用之期間、地區、對象及方式（個資法第 8 條第 1 項第 4 款）',
    items: [
      '期間：自蒐集之日起至服務契約終止後 30 日，或法令要求之保存期限屆滿（以較晚者為準）。',
      '地區：中華民國境內及本公司雲端服務供應商所在地區（見子處理者清單）。',
      '對象：本公司及為提供服務所必要之子處理者（詳列於下方）。',
      '方式：以自動化方式儲存、處理及傳輸，並採加密及存取控制措施。',
    ],
  },
  {
    title: '4. 當事人權利（個資法第 3 條）',
    items: [
      '一、查詢或請求閱覽您的個人資料。',
      '二、請求製給複製本（個資匯出）。',
      '三、請求補充或更正資料。',
      '四、請求停止蒐集、處理或利用。',
      '五、請求刪除個人資料。',
      '上述權利不得預先拋棄或以特約限制。行使方式：登入後至「帳號設定」操作，或寄信至 privacy@unihr.app。本公司將於 15 日內回覆。',
    ],
  },
  {
    title: '5. 不提供個人資料之影響（個資法第 8 條第 1 項第 6 款）',
    items: [
      '帳號資料（姓名、電子郵件）為提供服務所必要，若您選擇不提供，將無法建立帳號或使用本服務。',
      '技術資料由系統自動產生，無法選擇不提供。',
    ],
  },
  {
    title: '6. 安全維護措施（個資法第 20-1 條）',
    items: [
      '採用租戶隔離（PostgreSQL Row Level Security）、角色權限控管、TLS 傳輸加密。',
      '稽核日誌保存 7 年，資料庫每日自動備份，上傳檔案經病毒掃描（ClamAV）。',
      '如發生個資外洩，本公司將依個資法第 12 條規定通知當事人及主管機關。',
    ],
  },
  {
    title: '7. 子處理者清單',
    items: [
      'Linode (Akamai)：雲端主機與運算。',
      'Cloudflare R2：物件儲存（上傳文件靜態加密）。',
      'Pinecone：向量資料庫（租戶隔離命名空間）。',
      'Google Gemini：LLM 回答生成（不儲存使用者資料）。',
      'Voyage AI：文件向量化與重排序（不儲存使用者資料）。',
      'LlamaParse：文件解析（僅暫時處理，處理完成後立即刪除）。',
      'Resend：交易型電子郵件寄送。',
      '藍新金流 (NewebPay)：線上付款處理。',
    ],
  },
  {
    title: '8. 蒐集者名稱及聯絡方式（個資法第 8 條第 1 項第 1 款）',
    items: [
      '名稱：UniHR（運營公司名稱依營業登記為準）。',
      '個資保護聯絡信箱：privacy@unihr.app',
      '客服信箱：support@unihr.app',
    ],
  },
]

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50 text-gray-900">
      <PublicSiteNav />
      <div className="px-4 py-10">
      <div className="mx-auto max-w-4xl overflow-hidden rounded-[32px] border border-white/70 bg-white/90 shadow-2xl backdrop-blur">
        <div className="border-b border-rose-100 bg-[radial-gradient(circle_at_top_left,_rgba(209,84,84,0.16),_transparent_40%),linear-gradient(135deg,#fff7f5,#fff)] px-8 py-10 md:px-12">
          <p className="text-sm font-medium uppercase tracking-[0.28em] text-[#d15454]">UniHR Legal</p>
          <h1 className="mt-3 text-3xl font-bold md:text-4xl">隱私權政策</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-600 md:text-base">
            本政策說明 UniHR 如何蒐集、使用、保存與保護您在使用 SaaS 服務時提供的資料。生效日為 2026-03-23。
          </p>
        </div>

        <div className="space-y-8 px-8 py-10 md:px-12">
          {sections.map((section) => (
            <section key={section.title} className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">{section.title}</h2>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-gray-700">
                {section.items.map((item) => (
                  <li key={item} className="rounded-xl bg-stone-50 px-4 py-3">{item}</li>
                ))}
              </ul>
            </section>
          ))}

          <section className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/70 px-6 py-5 text-sm leading-6 text-gray-700">
            如需資料保護補充條款（DPA）、子處理者變更通知或資料刪除申請，請寄信至 privacy@unihr.app。
            <span className="mt-2 block text-gray-500">
              相關文件：<Link to="/terms" className="text-[#d15454] hover:underline">服務條款</Link>
            </span>
          </section>

          <div className="flex items-center justify-between gap-4 border-t border-gray-100 pt-6 text-sm text-gray-500">
            <span>最後更新：2026-03-23</span>
            <Link to="/" className="font-medium text-[#d15454] transition-colors hover:text-[#c04444]">返回首頁</Link>
          </div>
        </div>
      </div>
      </div>
      <PublicSiteFooter />
    </div>
  )
}