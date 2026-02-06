# UniHR 多租戶 B2B SaaS 產品構想與技術規格（評估版）

日期：2026-02-06

> 目的：把「現有 UniHR 勞資法 AI（核心系統）」產品化為可對外服務的 **Core API**，並在其上建立一套 **多租戶（Multi-tenant）SaaS**，讓不同公司擁有各自的帳號、資料庫與「公司內規/知識庫」，同時共享你持續優化的「台灣勞動法專業問答能力」。

---

## 閱讀指南（建議順序）

- 想先看「這產品是什麼」：第 0～4 章
- 想先確認「資料不外流」：第 5～6 章
- 想先看「企業怎麼用、怎麼上傳文件」：第 3A 章（使用者旅程）
- 想給新團隊快速串接 Core：第 16 章（Core 技術介紹）
- 想看工程任務與排程：第 18 章（Task Plan）

## 目錄

- 0. 一句話定義
- 1. 背景與動機
- 2. 目標與非目標
- 3. 使用者與典型情境
- 3A. 使用者旅程與操作細節
- 4. 系統總體架構
- 5. 資料隔離與安全
- 6. 問答協調器（Orchestrator/BFF）
- 7. 服務拆分
- 8. 資料模型
- 9. API 合約
- 10. 技術選型
- 11. 部署與營運
- 12. 品質與回歸
- 13. Roadmap
- 14. 風險與對策
- 15. 決策建議
- 16. Core 系統技術介紹（給新專案工程師）
- 17. 客戶端知識庫管理（文件處理與介面）
- 18. Task Plan（開發任務清單）

---

## 0. 一句話定義

**Core（你現有系統）**：台灣勞動法專業 RAG/QA 引擎（你持續最佳化的核心能力）。

**SaaS（新產品）**：企業 HR/主管/員工使用的多租戶平台：登入、權限、公司內規知識庫與問答協調（Orchestrator/BFF）、稽核、用量追蹤與配額管理；並透過 API 來整合 Core 回答。

---

## 1. 背景與動機

### 1.1 現況（已存在）
- 你目前有一套可運作的「勞資法 AI 問答」：
  - Flask + Gunicorn + Nginx（Linux 伺服器）
  - RAG 管線：向量檢索（Pinecone）+ 生成（OpenAI）+ 法律向量模型（Voyage）
  - 特點：12 份「專家驗證」文件可用高權重確保命中與品質（你已建立最佳化手段）

### 1.2 你想解決的問題
- 不同客戶（不同公司）想使用系統時：
  - 必須保證「公司內規/內部制度/敏感資訊」不外流
  - 必須能管理「公司、使用者、角色、權限、稽核、用量與成本歸屬、配額」
  - 你仍希望 **集中火力** 長期優化「勞動法 Core 的檢索/回答品質」，而不是每個客戶都客製一套分叉版本

### 1.3 核心策略
採用「**雙層架構（Platform + Product）**」：
1) **Core 勞資法 AI（平台能力）**：對外提供 API（可獨立迭代、獨立部署）。
2) **多租戶 SaaS（產品）**：做租戶管理、公司內規知識庫與問答協調（Orchestrator/BFF）。

---

## 2. 目標與非目標

### 2.1 產品目標（MVP）
- 多租戶：支援多家公司註冊與獨立空間（Tenant Isolation）
- 帳號系統：登入、角色（Owner/Admin/HR/Employee/Viewer）、權限控管
- 公司內規知識庫：文件上傳、解析、切片、向量化、檢索
- 問答：同時使用「公司內規」與「勞動法 Core」並合併輸出
- 稽核：對話、檢索來源、誰問了什麼、輸出給了什麼（保留必要證據）
- 用量追蹤：每租戶 token / query / 向量化成本記錄（內部成本歸屬，非金流收費）

### 2.2 非目標（第一階段不做，避免失焦）
- 完整 HRIS（人事系統）、薪資、出勤等 ERP 級功能
- 自建 LLM/自訓模型（先用 API + RAG 最快落地）
- 法律責任的正式法律意見書輸出（僅提供參考與法源，需清楚免責）

---

## 3. 使用者與典型情境

### 3.1 角色
- 公司 Owner：付費、管理員指派、稽核報表
- HR/Admin：上傳內規、設定回答策略、查看稽核、處理權限
- 一般員工：提問、查政策、獲得內規 + 法律補充

### 3.2 典型情境
- 員工問：「請病假要附什麼證明？」
  - 公司內規：公司要求/流程（優先）
  - 勞動法：最低標準與相關法規（補充下限與風險）

---

## 3A. 使用者旅程與操作細節

> 從「企業客戶第一次接觸到日常使用」的完整流程，
> 確保新團隊理解每一步使用者會做什麼、遇到什麼、系統該怎麼回應。

### 3A.1 企業註冊流程

**誰來註冊？** 通常是公司 HR 主管或老闆（Owner）。

```
步驟 1：進入註冊頁面
  → 填寫：公司名稱、統一編號、聯絡人姓名、Email、手機、密碼
  → 勾選：服務條款、隱私政策
  → 送出

步驟 2：Email 驗證
  → 系統寄驗證信 → 點擊連結確認

步驟 3：帳號啟用
  → 自動建立：
     - Tenant（公司空間）
     - Owner 帳號（最高管理者）
     - 空的公司知識庫（Pinecone index 預建立）
  → 導向 Onboarding 引導頁
```

**設計考量：**
- MVP 可先用「邀請制」（你手動開通），不需要開放自助註冊
- 統一編號可做重複檢查（避免同公司註冊多次）
- 考慮是否需要人工審核（B2B 通常需要）

### 3A.2 登入方式

**MVP：**
- Email + 密碼登入
- 忘記密碼（Email 重設連結）

**Phase 2：**
- Google SSO（一鍵登入）
- Microsoft SSO（企業常用）
- 企業 SAML/OIDC（大型客戶 IT 部門要求）

**登入後的體驗：**
```
登入成功
  → 系統辨識 tenant_id + user_id + role
  → 依角色導向不同首頁：
     - Owner/Admin → 管理後台（文件管理、用量、稽核）
     - HR → 問答 + 文件管理
     - Employee → 問答介面
```

### 3A.3 首次使用引導（Onboarding）

企業第一次使用時，系統應有引導流程，否則客戶不知道該做什麼：

```
Onboarding 步驟：

1. 歡迎頁面
   「歡迎使用 UniHR 勞資 AI 顧問！
    要讓 AI 了解貴公司的制度，請先上傳公司內規文件。」

2. 上傳第一份文件（引導式）
   → 提示推薦先上傳的文件類型：
     ✅ 工作規則 / 員工手冊（最重要，涵蓋最廣）
     ✅ 請假辦法
     ✅ 加班/薪資辦法
   → 拖放或選檔上傳
   → 即時顯示處理進度

3. 測試問答
   → 系統建議測試問題：「員工請特休假需要幾天前申請？」
   → 讓管理者看到 AI 是否正確引用剛上傳的文件
   → 如果命中 → 「✅ 您的文件已成功被 AI 學習！」
   → 如果未命中 → 「⚠️ 建議檢查文件內容或重新上傳」

4. 邀請同事
   → 輸入同事 Email → 設定角色（HR/Employee）
   → 系統寄邀請信
```

### 3A.4 文件上傳的完整使用者體驗

#### 上傳前：使用者看到什麼

```
┌──────────────────────────────────────────────┐
│  📁 文件管理                                   │
│                                              │
│  已上傳 3 份文件 ｜ 共 47 個知識段落             │
│                                              │
│  [+ 上傳新文件]                                │
│                                              │
│  檔案名稱         狀態     段落數  上傳日期      │
│  ─────────────────────────────────────────── │
│  工作規則.pdf      ✅ 完成   28    2026-02-01  │
│  請假辦法.docx     ✅ 完成   12    2026-02-03  │
│  加班費計算.xlsx   ⚠️ 部分   7     2026-02-05  │
│                                              │
└──────────────────────────────────────────────┘
```

#### 上傳中：即時回饋

```
上傳 薪資結構辦法.pdf ...

  ████████████░░░░░░  60%

  ✅ 步驟 1/4：檔案上傳完成
  ✅ 步驟 2/4：文件解析完成（偵測到 15 頁，文字型 PDF）
  🔄 步驟 3/4：文字切片中...（已產生 8/12 個段落）
  ⬜ 步驟 4/4：AI 向量化（讓 AI 能理解這份文件）
```

#### 上傳後：品質回饋

**成功案例：**
```
✅ 薪資結構辦法.pdf 處理完成！

  📊 處理結果：
  - 總頁數：15 頁
  - 產生段落：12 個知識段落
  - 文字品質：良好
  - AI 現在可以回答關於薪資結構的問題了

  💡 建議測試：「公司的薪資結構有幾個級距？」
```

**部分問題案例：**
```
⚠️ 加班費計算.xlsx 處理完成，但有以下注意事項：

  📊 處理結果：
  - 偵測到 3 個工作表
  - 成功解析：Sheet1（加班費率表）、Sheet2（假日加班）
  - ⚠️ Sheet3 含有圖表，AI 無法讀取圖表內容

  💡 建議：如果 Sheet3 有重要資訊，請將其轉為文字說明後重新上傳
```

**失敗案例：**
```
❌ 勞資會議紀錄.pdf 無法處理

  原因：此 PDF 為掃描圖片（沒有可選取的文字）
  
  💡 解決方案：
  1. 如果有電子版（Word/文字型 PDF），請改上傳電子版
  2. 掃描文件的文字辨識功能（OCR）即將推出，届時可重試
```

### 3A.5 文件格式與品質如何確保（摘要）

- 文件格式支援策略、OCR/Excel 等分期支援：詳見第 17.5（MVP vs 後續切分建議）
- 文件品質保證機制（自動檢查 + 管理者測試工具）：詳見第 17.2（現實挑戰）與第 17.3（介面需求）

### 3A.6 員工日常使用體驗

```
員工登入後看到的畫面：

┌──────────────────────────────────────────────┐
│  💬 UniHR 勞資 AI 顧問    [台積電股份有限公司]   │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ 👤 請問特休假沒休完可以換錢嗎？           │  │
│  │                                        │  │
│  │ 🤖 根據公司規定與勞動法：                │  │
│  │                                        │  │
│  │ 📋 公司內規：                           │  │
│  │ 根據《員工休假辦法》第8條，年度終結未休   │  │
│  │ 之特休假，公司依未休日數折算工資發放。    │  │
│  │ 需於每年12月15日前向HR確認。             │  │
│  │                                        │  │
│  │ ⚖️ 勞動法規：                           │  │
│  │ 依《勞動基準法》第38條第4項，年度終結    │  │
│  │ 或契約終止而未休之日數，雇主應發給工資。  │  │
│  │ 此為法律最低保障，公司不得低於此標準。    │  │
│  │                                        │  │
│  │ ⚠️ 注意：如有疑義，建議洽詢公司HR或法務  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [輸入問題...]                         [送出]  │
└──────────────────────────────────────────────┘
```

**使用者體驗重點：**
- 清楚區分「公司內規」與「勞動法規」兩個來源
- 標明引用的具體文件名和條號
- 附上免責提示
- 回答速度：目標 5~15 秒（含兩路檢索 + LLM 生成）
- 可查看歷史對話

### 3A.7 異常情境處理

| 情境 | 使用者看到什麼 | 系統做什麼 |
|---|---|---|
| 公司沒上傳任何文件 | 「您的公司尚未設定內規文件，以下僅提供勞動法規的通用回答。請聯繫管理者上傳公司制度文件。」 | 只呼叫 Core，不查 tenant KB |
| 問題與內規無關（純法律） | 正常回答勞動法 + 提示「公司知識庫中未找到相關內規」 | Core 回答為主 |
| 內規與法律衝突 | 「⚠️ 注意：公司規定可能低於法律最低標準，建議諮詢HR/法務確認。」 | 明確提示衝突 |
| Core API 暫時不可用 | 「目前法律資料庫暫時維護中，以下僅根據公司內規回答，法律補充稍後提供。」 | 降級：僅回覆內規 |
| 問題與勞資完全無關 | 「抱歉，本系統專注於勞動法規與公司人事制度，無法回答此類問題。」 | 與 Core 一致的分類邏輯 |
| 檔案上傳過大（>50MB） | 「檔案過大，請壓縮或拆分後重新上傳（上限 50MB）」 | 前端 + 後端雙重檢查 |
| 同時多人上傳文件 | 各自看到自己的進度，互不影響 | 背景佇列逐一處理 |

---

## 4. 系統總體架構（建議）

### 4.1 高層架構圖

```
[Browser / App]
      |
      v
[SaaS Web/API]  (多租戶、AuthZ、公司內規 KB、對話與稽核、用量追蹤與配額)
      |
      |  (service-to-service)
      v
[Core Labor-Law AI API]  (你的勞資法 RAG 引擎，只處理共用法規與你自己的最佳化)
      |
      +--> OpenAI (generation)
      +--> Voyage (embeddings)
      +--> Pinecone (shared labor-law index)

[SaaS Web/API]
  +--> Pinecone (per-tenant index or per-tenant project)
  +--> Relational DB (tenants/users/docs/conversations/audit)
  +--> Object Storage (原始文件、切片中間檔)
```

### 4.2 關注點分離（責任邊界）

**Core 勞資法 AI API（你現有系統演進）**
- 只維護：
  - 台灣勞動法「共用」知識庫與檢索品質
  - 你定義的回答格式、引用法源、免責聲明
  - 專家驗證文檔機制（優先權重、版本管理）
- 盡量不做：
  - 租戶帳號、權限
  - 租戶私有文件與向量索引
  - PII/個資/公司內部政策的長期保存

**多租戶 SaaS（新系統）**
- 只維護：
  - Tenant（公司）/User（使用者）/Role（角色）
  - 公司內規知識庫（上傳、向量化、索引、刪除、版本）
  - 問答協調器（Orchestrator/BFF）：合併 company KB + core KB
  - 稽核、用量追蹤、配額（quota）

---

## 5. 資料隔離與安全（最重要章節）

### 5.1 隔離原則（硬性規定）
- 每家公司內規知識庫必須 **完全獨立**
- 任何跨租戶資料存取都必須被視為重大資安事件
- 稽核記錄必須可追溯：誰、何時、問了什麼、用了哪些來源、回了什麼

### 5.2 向量資料隔離策略（從強到弱）

**A. 最安全：每租戶獨立 Pinecone 專案/帳號**
- 優點：隔離最徹底，權限/金鑰天然分離
- 缺點：營運成本與管理複雜度較高
- 適合：中大型企業、資安要求高

**B. 推薦平衡：每租戶獨立 Pinecone Index（同一專案）**
- 優點：隔離強、管理可控、成本較好
- 缺點：Index 數量增加需規劃命名、生命周期
- 適合：大多數 B2B SaaS

**C. 不建議作為唯一隔離：同一 Index + namespace**
- 風險：一旦程式 bug 或權限誤設，可能讀到別家公司資料
- 可用：做「加速」或「輔助分類」可以，但不應作為唯一安全邊界

> 結論：公司內規 KB 建議採用 **B**（Index per tenant）起步；對高敏感客戶提供 **A**（Project/Account per tenant）升級方案。

### 5.3 其他安全要點
- SaaS → Core 之間採「服務對服務」認證（建議：mTLS 或簽章 token），禁止前端直接呼叫 Core
- Core 不接收 tenant_id 也可以（降低誤用風險）；若需要追蹤，使用 request_id / correlation_id
- 資料最小化：Core 不儲存租戶私有資料；SaaS 端控制 PII 保存策略
- 加密：
  - at-rest：DB、Object Storage、向量資料（依供應商能力）
  - in-transit：全程 TLS
- 稽核：所有跨資源行為（上傳/刪除/索引/查詢/匯出）都必須寫入 audit log

---

## 6. 問答協調器（Orchestrator/BFF）設計

### 6.1 核心流程（建議）
1) 身分與權限：確認 user ∈ tenant、角色允許問答
2) 內規檢索：查詢 tenant 專屬 KB
3) 法律檢索：呼叫 Core 勞資法 API
4) 合併與裁決（Policy）：
   - 內規命中且可信 → 內規優先
   - 法律提供下限、風險提示、法源引用
   - 內規與法律衝突 → 提示「法律最低標準」並建議 HR/法務確認
5) 輸出：統一的 JSON schema + 前端呈現
6) 稽核：寫入 conversation + retrieval trace

### 6.2 合併策略（簡化可落地版本）
- Answer = `company_policy_section` + `labor_law_section` + `conflict_check` + `disclaimer`
- 透明化來源：
  - company_policy：文件名/版本/段落（不要暴露不必要敏感內容）
  - labor_law：法條名稱/條號/摘要

---

## 7. 服務拆分（建議模組）

### 7.1 SaaS 端（新系統）
- Auth Service：登入、JWT/Session、密碼、MFA（可選）
- Tenant Service：公司、方案、配額、啟停用
- Document Service：上傳、解析、切片、向量化、索引、刪除、版本
- Chat Orchestrator：問答協調器（最重要）
- Audit/Analytics：稽核、報表、事件追蹤
- Usage & Cost Tracking：追蹤每租戶的 token 消耗、query 次數、向量化成本（內部成本歸屬用，非對外收費系統）

### 7.2 Core 端（現有系統演進）
- Labor-law retrieval pipeline：你現有的 RAG
- Expert validated documents：高優先權、版本控
- Quality eval harness：回歸測試、問題集、A/B

---

## 8. 資料模型（SaaS 建議）

> 下列是概念模型，實作可用 PostgreSQL。

### 8.1 主要表
- tenants
  - id, name, plan, status, created_at
- users
  - id, tenant_id, email, password_hash (或 SSO), status
- roles / user_roles
  - tenant_id, user_id, role
- documents
  - id, tenant_id, source_type, filename, version, status, uploaded_by, created_at
- document_chunks
  - id, tenant_id, document_id, chunk_hash, text, metadata
- conversations
  - id, tenant_id, user_id, started_at
- messages
  - id, conversation_id, role(user/assistant/system), content, created_at
- retrieval_traces
  - id, tenant_id, conversation_id, message_id, sources_json, latency_ms
- audit_logs
  - id, tenant_id, actor_user_id, action, target_type, target_id, ip, created_at, detail_json
- usage_records（成本追蹤核心表）
  - id, tenant_id, user_id, action_type(chat/embed/index), input_tokens, output_tokens, pinecone_queries, embedding_calls, latency_ms, estimated_cost_usd, created_at

### 8.2 Object Storage
- 原始文件：PDF/DOCX/HTML
- 中間產物：抽取文本、切片結果（可選）

---

## 9. API 合約（草案）

### 9.1 Core 勞資法 API（現有系統提供）

**POST /v1/labor/chat**
- Request
  - question: string
  - context (optional): string
  - request_id (optional): string
- Response
  - answer: string
  - citations: [{ title, url_or_source, law_ref, excerpt }]
  - safety: { disclaimer, confidence } (optional)
  - latency_ms

> 設計重點：Core 回答「通用勞動法」，不要依賴 tenant。

### 9.2 SaaS API（對前端）

**POST /v1/chat**
- Request
  - message: string
  - conversation_id (optional)
- Response
  - conversation_id
  - answer
  - sections: { company_policy, labor_law, notes }
  - sources: { company_docs: [...], labor_law: [...] }

**POST /v1/tenant/documents**
- multipart upload

**DELETE /v1/tenant/documents/{id}**

**GET /v1/audit**

**GET /v1/usage?from=&to=&group_by=tenant|day|action**
- Response
  - total_input_tokens, total_output_tokens
  - total_pinecone_queries
  - total_embedding_calls
  - estimated_cost_usd
  - breakdown: [{ tenant_id, period, ...同上欄位 }]

---

## 10. 技術選型建議（務實可落地）

### 10.1 SaaS 後端
- Python（與 Core 同語言，利於團隊一致）
- Web framework：FastAPI（建議，型別與 OpenAPI 好用）或 Flask（延續現有習慣）
- DB：PostgreSQL
- Queue：Redis + RQ/Celery（文件向量化、長任務）
- Object Storage：S3 相容（MinIO/AWS S3）

### 10.2 文件解析
- PDF：pypdf / pdfplumber（依品質）
- DOCX：python-docx
- HTML：readability/lxml
- 切片：固定長度 + 重疊（例如 800~1200 tokens；依實測調整）

### 10.3 向量檢索
- 公司內規：tenant-per-index
- 勞動法：shared index（既有 unihr-legal-v3 類似概念）

---

## 11. 部署與營運

### 11.1 部署拓撲（建議）
- Core：維持你現有的 Linux 部署（Gunicorn + Nginx + systemd）
- SaaS：獨立一台或同一台（建議獨立）
- 日誌：集中化（至少保留 access/error/audit）

### 11.2 關鍵營運檢查
- SLA 監控：/health
- 外部連通：Gunicorn bind 必須對外可達（例如 0.0.0.0），避免再次發生「綁 127.0.0.1 導致外部 404/連線失敗」
- 成本監控（per-tenant 級別）：
  - 每租戶 LLM token 消耗（input / output tokens 分開記）
  - 每租戶 Core API 呼叫次數與延遲
  - 每租戶 Pinecone query 次數（內規 KB + 共用 KB 分開記）
  - 每租戶文件向量化成本（embedding API 呼叫次數 × 單價）
  - 彙總報表：每日/每週/每月，可依租戶、時段、功能拆分
  - 用途：內部成本分析、定價策略參考、異常偵測（某租戶突然暴增）

---

## 12. 品質與回歸（你最在意的地方）

### 12.1 Core 的品質提升閉環
- 固定題庫：50/100/500 題（含常見與刁鑽）
- 每次改動（prompt/檢索參數/專家文檔/分流器）都跑回歸評估
- 記錄：
  - Top-k 命中率
  - Expert docs 命中率
  - 回答一致性
  - 法源引用正確率

### 12.2 SaaS 的品質目標
- 內規命中率：使用者問公司流程時要能穩定命中
- 衝突偵測：內規 vs 法律最低標準的衝突提示

---

## 13. MVP → V1 Roadmap（建議）

### Phase 0：現有 Core 稳定化
- API 版本化、schema 固定
- 加入 request_id / correlation_id
- 建立回歸題庫與自動化評估腳本

### Phase 1：SaaS MVP
- Tenant/User/Role
- 文件上傳與向量化（背景任務）
- Chat Orchestrator（公司內規 + Core）
- 稽核 log

### Phase 2：企業化
- SSO（Google/Microsoft/企業 SAML）
- 細緻權限（部門/職務）
- 匯出稽核報表
- **平台管理後台（System Admin Dashboard）**
  - 全租戶總覽（企業列表、狀態、方案、用量）
  - 跨租戶用量分析（Token 消耗趨勢、API 呼叫、成本歸屬）
  - 租戶管理（建立/暫停/恢復、調整方案）
  - 跨租戶用戶搜尋與管理
  - 系統健康監控（服務狀態、錯誤率、回應延遲）
- 多環境（staging/prod）、灰度發布

### Phase 3：商業化深化
- 配額管理與超額告警（每租戶 query/token 上限，超額提醒）
- 客戶自助管理後台（各租戶 admin 管理自己的公司空間）
- 高資安方案（tenant project/account）
- API rate limiting 與濫用偵測

### Phase 4：生產化與前後台分離
- 前端拆分：系統管理台（admin）與客戶端（client）分離為獨立應用
- Admin API 網路隔離（IP 白名單 / VPN / 內網限制）
- 白標支援（自訂 domain、logo、色系、品牌名稱）
- CI/CD 自動化（GitHub Actions + Docker Registry + 自動部署）
- 生產環境基礎建設（HTTPS、監控、日誌集中化、備份策略）
- 負載測試與效能調優
- Admin API 獨立微服務 + 獨立資料庫讀副本（進階）
- 多區域部署支援：客戶資料落地要求（進階）

> 注意：本系統不做金流收費（Stripe/綠界等），定價與收費在系統外處理。成本追蹤的目的是讓你知道每家客戶的實際服務成本，作為報價與商務談判的依據。

---

## 14. 風險清單與對策

- 租戶資料外流（最高風險）
  - 對策：tenant-per-index 或 tenant-per-account；嚴格 AuthZ；稽核；安全測試
- 成本不可控（LLM + 向量查詢）
  - 對策：per-tenant 用量追蹤即時告警、快取常見問答、降階策略（低價模型 fallback）、答案重用、可設定每租戶 query/token 上限
- 回答法律責任爭議
  - 對策：清楚免責；提供法源引用；提示需 HR/法務確認
- 內規文件品質差（掃描 PDF、破碎文字）
  - 對策：OCR pipeline（後置）；文件品質提示；手動校正工具

---

## 15. 決策建議（你用來評估的結論）

- 這個架構 **OK 且合理**：
  - 你可以專心把 Core 勞資法 QA 做到極致（品質、法源、專家文檔）
  - 多租戶 SaaS 做企業需求（帳號、權限、內規、稽核、用量追蹤與配額）
- 成敗關鍵：
  1) 租戶資料隔離必須做到「物理隔離等級」
  2) Orchestrator 的合併策略要可控、可稽核
  3) Core 要有回歸評估與版本管理，才能長期高速迭代不翻車

---

## 16. Core 系統技術介紹（給新專案工程師）

> 本節讓開發多租戶 SaaS 的工程師快速理解「Core 勞資法 AI」的技術細節，以便正確串接。

### 16.1 Core 是什麼

Core 是一套**已上線運作**的台灣勞動法 AI 問答系統，部署在 Linux 伺服器上，對外提供 HTTP API。它的核心能力是：
- 接收使用者的勞動法相關問題
- 透過 RAG（Retrieval-Augmented Generation）管線檢索相關法規
- 結合 LLM 生成專業回答並附上法源引用

SaaS 系統**不需要複製或修改 Core 的任何程式碼**，只需透過 HTTP API 呼叫它。

### 16.2 Core 技術棧

| 元件 | 技術 | 說明 |
|---|---|---|
| Web Framework | Flask (Python 3.12) | 主應用程式 |
| WSGI Server | Gunicorn | 多 worker、180s timeout |
| Reverse Proxy | Nginx | 前端 proxy，監聽 80/443 |
| LLM | OpenAI GPT-4o | 回答生成 |
| Embeddings | Voyage-law-2 | 法律專用向量模型，1024 維 |
| Vector DB | Pinecone (unihr-legal-v3) | 3,185+ 向量，35+ 台灣勞動法 |
| 專家文檔 | 12 份律師驗證文件 | 權重 +1000 確保命中 |
| 知識圖譜 | JSON-based KG | 法規關聯與查詢增強 |
| 查詢分類 | QueryClassifier | 區分勞資/非勞資/問候/特休等 |

### 16.3 Core 現有 API Endpoints

**目前已存在的 endpoints（生產環境）：**

#### POST /chat （主要端點，SaaS 將串接此 API）
- **Request Body (JSON)**:
  ```json
  {
    "message": "加班費怎麼計算？",
    "session_id": "optional-uuid",
    "history": [],
    "response_type": "simple"
  }
  ```
- **Response (JSON, HTTP 200)**:
  ```json
  {
    "answer": "根據勞動基準法第24條...",
    "session_id": "uuid-string",
    "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
  }
  ```
- **Error Response (HTTP 400/500)**:
  ```json
  {"error": "錯誤訊息"}
  ```

#### GET /health（健康檢查）
- **Response**:
  ```json
  {
    "status": "ok",
    "pinecone_index": "unihr-legal-v3",
    "record_count": 3185,
    "knowledge_graph": "available",
    "model": "gpt-4o-2024-08-06"
  }
  ```

#### GET /models（可用模型列表）
#### POST /api/chat/submit（相容端點，功能同 /chat）
#### GET /api/chat/init（初始化/CORS 預檢）

### 16.4 SaaS 串接 Core 的方式

```python
# SaaS 系統中呼叫 Core 的範例（Python / httpx）
import httpx
import uuid

CORE_API_URL = "http://139.162.79.41:5000"  # 內網或 VPN
SERVICE_TOKEN = "your-service-token"         # Phase 0 會加上

async def query_labor_law(question: str, request_id: str = None):
    """呼叫 Core 勞資法 API"""
    resp = await httpx.AsyncClient().post(
        f"{CORE_API_URL}/chat",
        json={
            "message": question,
            "session_id": request_id or str(uuid.uuid4()),
        },
        headers={
            "Authorization": f"Bearer {SERVICE_TOKEN}",
            "X-Request-ID": request_id or str(uuid.uuid4()),
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()  # {"answer": "...", "session_id": "...", ...}
```

### 16.5 Core 的限制與注意事項

| 項目 | 現況 | SaaS 應對 |
|---|---|---|
| 回應時間 | 3~15 秒（視問題複雜度） | SaaS 前端需做 loading 狀態 |
| 並發能力 | Gunicorn workers（CPU×2+1） | SaaS 需做 rate limiting / queue |
| 無 tenant 概念 | Core 不知道誰問的 | 好事：Core 不會洩漏租戶資訊 |
| 無認證（目前） | Phase 0 會加 service token | SaaS 不應讓前端直打 Core |
| 無 token 用量回傳 | 目前不回傳 token 數 | Phase 0 會加，SaaS 用此做成本追蹤 |
| 免責聲明 | Core 回答已含免責語 | SaaS 可在外層再包一層 |

### 16.6 兩個專案的 Git Repo 結構建議

```
# Core（本專案，已存在）
unihr/
├── src/app.py          # Flask 主應用
├── data/               # 專家文檔、知識圖譜
├── scripts/            # 索引建置、品質評估
├── tests/              # 回歸測試
└── docs/               # 文件（含本規格書）

# SaaS（新專案，獨立 repo）
unihr-saas/
├── app/
│   ├── main.py             # FastAPI 入口
│   ├── routers/            # chat, documents, auth, audit, usage
│   ├── services/
│   │   ├── orchestrator.py # 問答協調器（呼叫 Core + 內規 KB）
│   │   ├── core_client.py  # Core API 封裝
│   │   ├── document.py     # 文件上傳/切片/向量化
│   │   └── usage.py        # 用量追蹤
│   ├── models/             # SQLAlchemy/Pydantic
│   ├── db/                 # migrations
│   └── config.py
├── tests/
├── docker-compose.yml      # PostgreSQL, Redis
├── requirements.txt
└── README.md
```

### 16.7 伺服器與網路拓撲

```
┌─────────────────────────────────────────────┐
│  Core 伺服器 (139.162.79.41)                 │
│  ├── Gunicorn :5000 (bind 0.0.0.0)          │
│  ├── Nginx :80                              │
│  ├── systemd: unihr.service                 │
│  └── 關鍵：bind 必須是 0.0.0.0 不是 127.0.0.1 │
│       （曾因此導致全站 404，已修復）            │
└──────────────────┬──────────────────────────┘
                   │  HTTP POST /chat
                   │
┌──────────────────┴──────────────────────────┐
│  SaaS 伺服器 (新建)                           │
│  ├── FastAPI :8000                          │
│  ├── PostgreSQL :5432                       │
│  ├── Redis :6379                            │
│  └── Pinecone (per-tenant index)            │
└──────────────────┬──────────────────────────┘
                   │
              [瀏覽器/App]
```

---

## 17. 客戶端知識庫管理（文件處理與介面）

> 本節從「客戶（HR/Admin）的角度」思考：他們會上傳什麼、遇到什麼問題、需要什麼介面。
> 具體 UI/UX 設計與實作交由新專案團隊，本節提供方向與需求規格。

### 17.1 客戶會上傳什麼文件？

**典型企業內規文件類型：**

| 類別 | 範例 | 常見格式 | 難度 |
|---|---|---|---|
| 員工手冊/工作規則 | 公司工作規則、員工守則 | PDF/DOCX | 低～中 |
| 請假辦法 | 病假/事假/特休/產假規定 | PDF/DOCX | 低 |
| 薪資與獎金辦法 | 薪資結構、年終獎金、加班費計算 | PDF/DOCX/Excel | 中 |
| 考績與晉升 | 績效評估辦法、晉升標準 | PDF/DOCX | 低 |
| 差旅報銷 | 出差管理辦法、報銷標準 | PDF | 低 |
| 福利制度 | 團保、健檢、員工旅遊 | PDF/DOCX/HTML | 低 |
| 離職與資遣 | 離職流程、資遣辦法、交接規定 | PDF/DOCX | 低 |
| 勞資會議紀錄 | 會議決議、協議事項 | PDF（掃描）| 高 |
| 團體協約 | 工會協議 | PDF | 中 |
| 公告/函文 | 人事公告、政策變更通知 | PDF/圖片 | 高 |

### 17.2 文件處理的現實挑戰

**客戶不是工程師**，他們上傳的文件品質參差不齊：

| 挑戰 | 說明 | 建議處理 |
|---|---|---|
| 掃描 PDF | 圖片型 PDF，無文字層 | OCR（Tesseract/雲端 OCR），標記為「OCR 品質」 |
| 表格密集 | 薪資表、假別對照表 | 表格專用解析（pdfplumber/camelot），保留結構 |
| 混合格式 | 同一份文件有文字+表格+圖片 | 分段處理，圖片附註「此段含圖片無法解析」 |
| Excel 試算表 | 薪資級距、加班費對照 | 轉為結構化文字，保留欄位名稱與數值 |
| 舊文件更新 | 新版辦法取代舊版 | 版本管理：停用舊版向量、索引新版 |
| 文件過大 | 100+ 頁員工手冊 | 切片策略 + 進度顯示 + 背景處理 |
| 機密等級 | 薪資辦法比請假辦法更敏感 | 可標記文件機密等級，控制誰能查到 |

### 17.3 客戶管理介面需求（給新團隊的 UX 方向）

#### A. 文件上傳頁
- 拖放上傳或選檔上傳
- 支援格式提示：PDF、DOCX、HTML、TXT（MVP）；Excel（Phase 2）
- 上傳後顯示處理狀態：`上傳中 → 解析中 → 向量化中 → 完成 / 失敗`
- 失敗時顯示原因（如「此 PDF 為掃描圖片，文字辨識品質較低，建議上傳文字版」）

#### B. 知識庫管理頁
- 文件清單：檔名、上傳時間、上傳者、狀態、切片數量、版本
- 操作：預覽內容（切片後的文字）、停用、刪除、重新索引
- 版本管理：上傳新版時標記舊版為「已取代」，舊版向量自動移除
- 搜尋測試：管理者可輸入問題，看看會命中哪些內規段落（Debug 用）

#### C. 文件品質回饋
- 上傳完成後，系統提示：
  - ✅ 品質良好：成功解析 N 個段落
  - ⚠️ 部分問題：某些頁面為掃描圖片、某些表格可能遺失格式
  - ❌ 無法處理：檔案損毀、加密 PDF、不支援的格式
- 讓客戶知道哪些內容「AI 看得到」、哪些「AI 看不到」

#### D. 回答來源透明化
- 員工問問題後，回答中標示：
  - 📋 公司內規：來自《XX辦法》第N條（文件名 + 段落摘要）
  - ⚖️ 勞動法規：來自《勞動基準法》第N條
- 管理者可在稽核頁看到完整 retrieval trace

### 17.4 文件處理 Pipeline（技術方向）

```
上傳 → 格式偵測 → 解析 → 品質檢查 → 切片 → Embedding → Pinecone
                                                         ↓
                                                   tenant-{id}-kb index
```

**各階段細節：**

1. **格式偵測**：依副檔名 + magic bytes 判斷
2. **解析**：
   - PDF（文字型）：pypdf / pdfplumber
   - PDF（掃描型）：OCR pipeline（Phase 2，MVP 先標記為不支援）
   - DOCX：python-docx
   - HTML：readability + lxml
   - Excel：openpyxl → 轉結構化文字（Phase 2）
3. **品質檢查**：
   - 文字密度太低 → 可能是掃描 PDF
   - 亂碼偵測 → 編碼問題
   - 空白頁偵測
4. **切片**：
   - 固定長度 800~1200 tokens + 重疊 100~200 tokens
   - 盡量在段落/章節邊界切（依標題、換行、分隔線）
   - 每個 chunk 保留 metadata：document_id、page_number、section_title
5. **Embedding**：Voyage-law-2（與 Core 同模型，確保語義空間一致）
6. **寫入**：tenant 專屬 Pinecone index

### 17.5 MVP vs 後續的切分建議

| 功能 | MVP（Phase 1） | Phase 2 | Phase 3 |
|---|---|---|---|
| 支援格式 | PDF（文字型）、DOCX、TXT | 掃描 PDF（OCR）、Excel | 圖片、HTML 網頁抓取 |
| 上傳介面 | 基本上傳 + 狀態顯示 | 拖放、批次上傳 | 自動同步（雲端硬碟） |
| 版本管理 | 手動取代 | 自動偵測同名新版 | 版本比較與 diff |
| 品質回饋 | 成功/失敗 | 詳細品質報告 | 改善建議 |
| 搜尋測試 | 無 | 管理者測試介面 | A/B 測試切片策略 |
| 機密等級 | 無 | 文件分級 | 依角色控制可查範圍 |

### 17.6 本節結論

> 文件處理與管理介面的**具體 UI 設計和實作由新專案團隊負責**。
> 本節提供的是「客戶會遇到什麼」和「系統該怎麼應對」的方向指引，
> 確保新團隊不會忽略這些實際場景。

---

## 18. Task Plan（開發任務清單）

> 以下為完整的開發任務，分兩條線：Core 改造（本專案）與 SaaS 新建（新專案）。
> 標記：⬜ 未開始 ｜ 🔲 可選 ｜ ✅ 完成後打勾

### Phase 0：Core 穩定化與 API 準備（本專案，預估 1~2 週）

**目標**：讓 Core 成為一個穩定、可被外部服務安全呼叫的 API。

- ⬜ **T0-1** 新增 `/v1/labor/chat` endpoint
  - 包裝現有 `/chat` 邏輯
  - 固定 request/response JSON schema
  - 加入 `request_id` 欄位（方便追蹤與關聯）
  - 回傳 `latency_ms` 欄位

- ⬜ **T0-2** 回傳 token 用量資訊
  - response 新增 `usage: { input_tokens, output_tokens, model }` 欄位
  - 從 OpenAI API response 中擷取 token 數量
  - SaaS 會用此欄位做 per-tenant 成本追蹤

- ⬜ **T0-3** 新增 service-to-service 認證
  - 實作 Bearer token 驗證（middleware）
  - 設定環境變數 `CORE_SERVICE_TOKEN`
  - 非法 token → 403
  - `/health` 不需認證（供監控用）

- ⬜ **T0-4** 回傳 citations（法源引用）
  - response 新增 `citations: [{ law_name, article, excerpt }]`
  - 從 RAG 檢索結果中擷取

- ⬜ **T0-5** API 版本化路由
  - `/v1/labor/chat`、`/v1/health`
  - 保留舊 `/chat` 不動（給現有 www.unihr.com.tw 網站繼續用）

- ⬜ **T0-6** 建立回歸測試題庫
  - 至少 50 題標準 QA（含預期答案關鍵字）
  - 自動化評估腳本（跑完輸出命中率/一致性分數）
  - 每次 Core 變更前後都跑一次

- ⬜ **T0-7** 文件化 Core API 合約
  - OpenAPI / Swagger spec（自動產生或手寫）
  - 提供給 SaaS 工程師作為串接依據

---

### Phase 1：SaaS MVP（新專案，預估 4~6 週）

**目標**：可運作的多租戶系統，支援公司內規上傳 + 問答 + 稽核。

#### 1A. 基礎建設（第 1~2 週）

- ✅ **T1-1** 專案初始化
  - FastAPI + PostgreSQL + Redis
  - Docker Compose 開發環境
  - CI/CD pipeline（GitHub Actions 或類似）
  - 環境變數管理（.env）

- ✅ **T1-2** 資料庫 schema 與 migration
  - 建立 tenants, users, roles, documents, document_chunks, conversations, messages, retrieval_traces, audit_logs, usage_records 表
  - 使用 Alembic 管理 migration

- ✅ **T1-3** Auth Service
  - 註冊、登入（email + password）
  - JWT token 發放與驗證
  - Middleware：從 token 解出 tenant_id + user_id + role
  - 權限檢查 decorator（RBAC: owner/admin/hr/employee/viewer + superuser bypass）

- ✅ **T1-4** Tenant Service
  - 建立公司、啟停用
  - 建立 tenant 專屬 Pinecone index（命名規則：`tenant-{tenant_id}-kb`）
  - Tenant 配額設定（query 上限 / token 上限）

#### 1B. 文件與知識庫（第 2~3 週）

- ✅ **T1-5** Document Service
  - 文件上傳 API（PDF/DOCX/TXT，MVP 先支援文字型）
  - 格式偵測（副檔名 + magic bytes）
  - 文件解析（pypdf, python-docx, lxml）
  - 品質檢查（掃描偵測、亂碼偵測、空白頁偵測）
  - 文字切片（800~1200 tokens, 重疊 100~200 tokens，段落邊界優先）
  - 背景任務：切片 → Voyage embedding → 寫入 tenant Pinecone index
  - 處理狀態追蹤：上傳中 → 解析中 → 向量化中 → 完成/失敗
  - 失敗原因回饋（加密 PDF、掃描圖片等）
  - 文件刪除（同步刪除 Pinecone 中對應向量）
  - 版本管理：上傳新版時停用舊版向量
  - 文件清單與狀態查詢 API

- ✅ **T1-6** 內規知識庫檢索
  - 查詢 tenant 專屬 Pinecone index
  - 回傳 top-k 結果 + 來源文件名/段落
  - 確保：查詢時一定帶 tenant 專屬 index name，不會誤查到其他公司

#### 1C. 問答與協調（第 3~4 週）

- ✅ **T1-7** Core Client 封裝
  - 封裝 Core API 呼叫（httpx async）
  - 超時處理（60s）、重試（1 次）、降級回應
  - 解析 response 中的 answer、citations、usage

- ✅ **T1-8** Chat Orchestrator
  - 接收使用者問題
  - 並行呼叫：(a) tenant 內規檢索 + (b) Core 勞資法 API
  - 合併策略：
    - 內規命中 → 內規優先，法律補充
    - 僅法律命中 → 法律回答 + 提示公司可能有內規
    - 衝突 → 提示法律最低標準
  - 輸出統一 JSON：company_policy / labor_law / notes / disclaimer

- ✅ **T1-9** 對話管理
  - conversation CRUD
  - message 儲存（含 retrieval_traces）
  - 歷史對話列表

#### 1D. 稽核與用量（第 4~5 週）

- ✅ **T1-10** Audit Service
  - 所有關鍵操作寫入 audit_logs
  - 操作包含：登入/文件上傳/文件刪除/問答/匯出
  - API：查詢稽核紀錄（依時間/使用者/操作類型）

- ✅ **T1-11** Usage & Cost Tracking
  - 每次問答記錄：input_tokens, output_tokens, pinecone_queries, embedding_calls
  - 從 Core response 的 `usage` 欄位擷取 token 數
  - 成本估算公式：`estimated_cost = input_tokens × rate + output_tokens × rate + ...`
  - API：查詢用量報表（依租戶/時段/操作類型彙總）

#### 1E. 測試與部署（第 5~6 週）

- ✅ **T1-12** 整合測試
  - SaaS → Core 端對端測試
  - 租戶隔離測試（A 公司不能查到 B 公司資料）
  - 權限測試（Employee 不能刪文件、不能看其他公司）
  - 用量記錄正確性測試

- ✅ **T1-13** Docker 部署（已完成本地和開發環境）
  - Docker Compose 完整環境（FastAPI + PostgreSQL + Redis + Celery + Frontend）
  - 前端 Nginx 容器（端口 3001）
  - 後端 API 服務（端口 8000）
  - 數據庫與緩存服務
  - 背景任務 Worker
  - ⏭️ 生產環境部署（待遠端伺服器：Nginx + HTTPS + systemd + 日誌集中化）

- ✅ **T1-14** 前端 MVP
  - 登入頁面（JWT 認證、自動跳轉）
  - 問答對話介面（對話列表、新對話、刪除、快捷問題建議）
  - 文件上傳管理頁（拖放上傳、進度顯示、狀態追蹤、清單、刪除）
  - 文件品質回饋顯示（成功/解析中/向量化中/失敗 + 自動輪詢）
  - 回答來源標示（📋 公司內規 / ⚖️ 勞動法規）
  - 用量儀表板（總操作數、Token 用量、Pinecone 查詢、成本統計、按類型分佈）
  - 技術棧：React + TypeScript + Vite + TailwindCSS + Axios

---

### Phase 2：企業化（預估 4~8 週，依優先序）

- ✅ **T2-1** SSO 整合（Google / Microsoft OAuth2）
  - Google OAuth2 callback + 自動建立/綁定用戶
  - Microsoft OAuth2 callback + 自動建立/綁定用戶
  - 前端 SSO 登入按鈕
  - 配置：per-tenant 可啟停不同 SSO provider

- ✅ **T2-2** 細緻權限（部門級、職務級）
  - Department model + CRUD API + 前端管理頁
  - User.department_id + Document.department_id
  - 部門級文件存取控制（employee/viewer 只能看自己部門）
  - FeaturePermission model（per-tenant + per-role 功能開關）
  - 功能開關 API（啟停 chat/documents/audit/kb 等模組）

- ✅ **T2-3** 稽核報表匯出（CSV/PDF）
  - `GET /audit/logs/export?format=csv|pdf`
  - `GET /audit/usage/export?format=csv|pdf`
  - 前端匯出按鈕（UsagePage + AuditLogsPage）
  - PDF 生成使用 ReportLab，CSV 含 BOM 支援 Excel

- ✅ **T2-7** 平台管理後台 — 後端 API（Superuser 專用）
  - `GET /admin/tenants` 全租戶列表（含用量統計摘要）
  - `GET /admin/tenants/{id}/stats` 單租戶詳細統計
  - `PUT /admin/tenants/{id}` 調整租戶狀態/方案
  - `GET /admin/users` 跨租戶用戶搜尋
  - `GET /admin/dashboard` 平台總覽（租戶數、用戶數、總用量、成本趨勢）
  - `GET /admin/system/health` 系統健康狀態
  - 所有端點均需 `is_superuser=True`

- ✅ **T2-8** 平台管理後台 — 前端儀表板
  - `/admin` 路由區塊（僅 superuser 可見）
  - 平台總覽儀表板（租戶數、用戶數、API 呼叫趨勢、成本趨勢圖表）
  - 租戶列表頁（搜尋、篩選、狀態管理）
  - 租戶詳情頁（用量明細、用戶列表、文件統計、近期操作）
  - 跨租戶用戶搜尋頁
  - 系統健康狀態頁（DB / Redis 狀態）
  - `is_superuser` 暴露至前端 Schema / Type

- ✅ **T2-4** 多環境支援（staging / production）
- ✅ **T2-5** 灰度發布機制
- ✅ **T2-6** Core API 版本升級策略（v1 → v2 平滑切換）

---

### Phase 3：商業化深化 ✅ 已完成（後端 + 前端）

#### 後端 API（已完成並通過測試）

- ✅ **T3-1** 配額管理與超額告警
  - 每租戶 query/token/user/document 上限設定（PLAN_QUOTAS: free/pro/enterprise）
  - 超額自動告警服務（QuotaAlertService + QuotaAlert model）
  - 平台管理後台配額管理 API（GET/PUT quota, apply-plan, alerts）
  - FastAPI Depends 層級配額強制（QuotaEnforcer → 429）

- ✅ **T3-2** 客戶自助管理後台
  - /api/v1/company/* 端點（dashboard, profile, quota, users, usage）
  - Owner/Admin 可邀請用戶、更新角色、停用帳號
  - 查看公司用量摘要與每人用量

- ✅ **T3-3** 高資安隔離方案（TenantSecurityConfig model）
  - 支援 standard/enhanced/dedicated 隔離等級
  - 可設定 IP 白名單、MFA、資料保留天數、加密金鑰 ID
  
- ✅ **T3-4** API rate limiting 與濫用偵測
  - Redis 滑動視窗 rate limiter（RateLimitMiddleware）
  - IP/User/Tenant 三層限流 + 濫用自動封鎖
  
- ✅ **T3-5** 成本分析進階（圖表化趨勢、異常偵測、預算預警）
  - /api/v1/analytics/* 端點（daily trends, monthly-by-tenant, anomalies, budget-alerts）

**Phase 3 測試結果**：52/52 通過（含 28 Phase 2 向下相容 + 24 Phase 3 新測試）

#### 前端頁面（已完成並構建）

- ✅ **AdminQuotaPage** 配額與安全管理頁面（/admin/quotas）
  - 租戶列表視圖（方案、狀態、用量統計）
  - 租戶詳細視圖（三個標籤頁）
    - **配額標籤**：使用狀況圖表、配額編輯表單、方案套用按鈕（free/pro/enterprise）
    - **安全標籤**：隔離等級選擇器、MFA 開關、IP 白名單、資料保留、加密金鑰
    - **告警標籤**：告警歷史記錄、立即檢查按鈕

- ✅ **CompanyPage** 公司自助管理頁面（/company）
  - **總覽標籤**：統計卡片（員工/文件/對話/月查詢）、配額使用狀況、超額警告
  - **成員管理標籤**：成員列表、邀請表單、角色編輯、停用帳號
  - **配額標籤**：唯讀配額視圖、使用進度條、方案顯示
  - **用量標籤**：總用量摘要、可展開的按成員用量統計表

- ✅ **AnalyticsPage** 成本分析儀表板（/analytics）
  - **使用趨勢標籤**：時間範圍選擇器（7/30/90天）、每日查詢量折線圖、每日成本折線圖、統計卡片
  - **租戶成本標籤**：月度租戶成本堆疊柱狀圖（recharts）、詳細數據表
  - **異常偵測標籤**：偏差閾值選擇器、異常記錄表（偏差倍率標記）
  - **預算警報標籤**：警報卡片列表、使用率進度條、超額/預警標記

- ✅ **路由與導航整合**
  - App.tsx 新增 3 條路由（/admin/quotas, /company, /analytics）
  - Layout.tsx 側邊欄新增導航項目（公司管理、配額管理、成本分析）
  - 角色權限過濾（superuser / owner+admin）

- ✅ **API 層擴充**
  - api.ts 新增 companyApi（9 個方法）
  - api.ts 新增 analyticsApi（4 個方法）
  - adminApi 擴充配額和安全管理方法（8 個新方法）

- ✅ **前端構建驗證**
  - TypeScript 編譯通過（零錯誤）
  - Vite 生產構建成功
  - 依賴項：recharts（圖表庫）

---

---

### Phase 4：生產化與前後台分離（預估 6~10 週）

**目標**：將系統從 MVP 階段升級為可對外販售的生產級 SaaS 產品。核心改造為前後台分離、網路隔離、白標支援與 CI/CD 自動化。

#### 4A. 前端架構分離（第 1~3 週）🔴 高優先

- ✅ **T4-1** 建立獨立系統管理台前端（admin-frontend）
  - 新建 `admin-frontend/` 獨立 Vite + React 專案
  - 遷移 AdminPage、AdminQuotaPage、AnalyticsPage 到獨立應用
  - 獨立的路由、認證流程、API 層
  - 部署於 `admin.unihr.com`（內部 domain）
  - 確保客戶端零 admin 程式碼（不打包、不下載）

- ✅ **T4-2** 客戶端前端精簡化
  - 移除現有 frontend 中的 AdminPage、AdminQuotaPage、AnalyticsPage
  - 移除 Layout.tsx 中的 `superuserOnly` 導航項目
  - 移除 api.ts 中的 adminApi（跨租戶管理方法）
  - 保留 CompanyPage（租戶自助管理）— 這是客戶方功能
  - 部署於 `app.unihr.com`（公開 domain）

- ✅ **T4-3** 白標前端支援 — 已完成（2025-02-08）
  - Tenant model 新增欄位：`brand_name`、`brand_logo_url`、`brand_primary_color`、`brand_secondary_color`、`custom_domain`
  - 客戶端啟動時載入租戶品牌設定（`GET /api/v1/company/branding`）
  - 登入頁、側邊欄 logo、頁首標題動態替換
  - 支援自訂 domain 對映（`{客戶}.unihr.com` 或客戶自有域名）
  - TailwindCSS CSS 變數化（primary/secondary color）

#### 4B. 後端 API 分離與網路隔離（第 2~4 週）🔴 高優先

- ✅ **T4-4** Admin API 網路隔離
  - 方案 A（簡單）：Nginx 反向代理層，`/api/v1/admin/*` 和 `/api/v1/analytics/*` 限制來源 IP
  - 方案 B（進階）：Admin API 獨立 FastAPI 服務，部署於內網，不暴露公網
  - 實作 IP 白名單 middleware（可設定允許的 CIDR 範圍）
  - Admin API 加上額外的存取日誌（who / when / from where）
  - 補充：新增 `ADMIN_TRUSTED_PROXY_IPS` 限制可信代理，避免偽造 X-Forwarded-For

- ✅ **T4-5** API Gateway 導入 — 已完成（2025-02-08）
  - 統一入口層：路由分發、速率限制、認證前置
  - 選型：Nginx / Traefik / Kong（建議先用 Nginx + Lua 或 Traefik）
  - 路由規則：
    - `admin.unihr.com/api/*` → Admin API（內網）
    - `app.unihr.com/api/*` → Tenant API（公網）
    - `{custom_domain}/api/*` → Tenant API（公網，帶 tenant 識別）
  - 健康檢查端點統一（`/healthz`）

- ✅ **T4-6** 自訂 domain 後端支援 — 已完成（2025-02-08）
  - 建立 domain → tenant_id 映射表（CustomDomain model）
  - Middleware：從 HTTP Host header 判斷 tenant（fallback 到 JWT tenant_id）
  - Let's Encrypt 自動 SSL 憑證（Traefik ACME 或 certbot）
  - DNS 驗證流程 API（CNAME 驗證）

#### 4C. CI/CD 與部署自動化（第 3~5 週）🟡 中優先

- ✅ **T4-7** GitHub Actions CI Pipeline
  - Push to main → 自動跑 lint + pytest
  - PR 建立 → 自動跑測試 + 建置驗證
  - 測試覆蓋率報告（pytest-cov）
  - Docker image 自動建置並推送至 Container Registry

- ✅ **T4-8** 自動部署 Pipeline — 已完成（2025-02-08）
  - Staging：main branch 合併 → 自動部署至 staging 環境
  - Production：手動觸發 or tag → 部署至生產環境
  - 部署策略：Rolling update（零停機）
  - 健康檢查 + 自動回滾機制
  - 環境變數透過 GitHub Secrets 或 Vault 管理

- ✅ **T4-9** Docker 映像最佳化 — 已完成（2025-02-08）
  - Multi-stage build（減少映像大小）
  - 前端映像：Nginx + 靜態檔案（< 50MB）
  - 後端映像：Python slim + 只安裝生產依賴（< 200MB）
  - Docker Compose production 配置最終化
  - 資源限制設定（CPU / Memory limits）

#### 4D. 生產基礎建設（第 4~6 週）🟡 中優先

- ✅ **T4-10** HTTPS 與域名配置
  - 購買並配置域名（unihr.com 或自選）
  - SSL 憑證自動管理（Let's Encrypt + auto-renew）
  - HSTS、CSP、CORS 安全標頭強化
  - HTTP → HTTPS 強制跳轉

- ✅ **T4-11** 監控與告警系統 — 已完成（2025-02-08）
  - 基礎監控：Prometheus + Grafana（或 UptimeRobot 等 SaaS 方案）
  - 應用指標：API 回應時間、錯誤率、活躍用戶數、佇列深度
  - 基礎建設指標：CPU、記憶體、磁碟、DB 連線數
  - 告警通道：Email / Slack / LINE Notify
  - 告警規則：API 5xx > 1%、回應時間 p95 > 3s、DB 連線池耗盡

- ✅ **T4-12** 日誌集中化 — 已完成（2025-02-08）
  - 結構化日誌（JSON format）+ request_id 追蹤
  - 集中收集：ELK Stack / Loki + Grafana（或 CloudWatch）
  - 日誌保留策略：30 天熱存、90 天冷存
  - 敏感資訊遮罩（PII masking）

- ✅ **T4-13** 備份與災難復原
  - PostgreSQL：每日自動備份（pg_dump / WAL archiving）
  - 備份加密與異地儲存（S3 / GCS）
  - 復原演練 SOP（每季一次）
  - RPO < 1 小時、RTO < 4 小時
  - 產出：`scripts/backup.sh`、`scripts/restore.sh`、`scripts/backup-full.sh`、`scripts/disaster-recovery.sh`

#### 4E. 效能與安全強化（第 5~8 週）🟢 可延後

- ✅ **T4-14** 負載測試 — 已完成（2026-02-07）
  - 使用 Locust 或 k6 建立負載測試腳本
  - 測試情境：100 concurrent users、1000 req/min
  - 找出瓶頸：DB 連線池、Celery worker 數、API 回應時間
  - 效能基準線建立與記錄
  - 產出：`tests/load/locustfile.py`、`tests/load/k6_load_test.js`、`tests/load/README.md`

- ✅ **T4-15** 資料庫調優 — 已完成（2026-02-07）
  - 索引最佳化（常用查詢的 EXPLAIN ANALYZE）
  - 連線池調參（pool_size、max_overflow）
  - 讀寫分離準備（Read Replica 配置）
  - Slow query log 監控
  - 產出：`alembic/versions/t4_15_db_indexes.py`、`scripts/db-performance.sh`、`configs/postgresql-tuning.conf`

- ✅ **T4-16** 安全稽核與滲透測試
  - OWASP Top 10 逐項檢查
  - SQL Injection / XSS / CSRF 防護驗證
  - 依賴套件漏洞掃描（pip-audit / npm audit）
  - Session 管理強化（token 輪替、concurrent session 限制）
  - 第三方滲透測試（上線前至少一次）
  - 產出：`scripts/security-audit.sh`

- ✅ **T4-17** 訂閱方案與用量計量基礎 — 已完成（2025-02-08）
  - 方案功能矩陣定義（Free / Pro / Enterprise 各含什麼）
  - 前端方案升級提示（達到 Free 上限時引導升級）
  - 用量計量匯出 API（給外部帳務系統或手動出帳用）
  - 注意：不做金流串接，仍為系統外處理

- ✅ **T4-18** Admin API 微服務化（進階）— 已完成（2026-02-07）
  - 將 `/api/v1/admin/*` 和 `/api/v1/analytics/*` 拆為獨立 FastAPI 服務
  - 獨立 Docker 容器，獨立埠號（只監聽內網）
  - PostgreSQL Read Replica（Admin 查詢走讀副本，避免影響客戶端效能）
  - 獨立 Redis 快取實例（Admin dashboard 數據快取）
  - 服務間通訊：內部 service token 認證
  - Docker Compose 新增 `admin-api` service 定義
  - 產出：`admin_service/`（__init__.py、main.py、db.py、cache.py、Dockerfile）

- ✅ **T4-19** 多區域部署支援（進階）— 已完成（2026-02-07）
  - 支援客戶資料落地要求（台灣、日本、東南亞等區域）
  - Tenant 模型新增 `region` 欄位（ap / us / eu / jp）
  - 每個區域獨立的：
    - PostgreSQL 實例（資料不出區域）
    - Redis 實例
    - Pinecone index（或指定 region）
    - Celery Worker
  - API Gateway 路由層根據 tenant region 轉發至對應區域服務
  - 跨區域共用：僅 Admin 平台管理台（讀取各區域資料的聚合視圖）
  - 合規文件：資料處理說明、儲存位置證明
  - 產出：`app/services/region.py`、`app/middleware/region_routing.py`、`app/api/v1/endpoints/regions.py`、`docker-compose.region.yml`、`docs/MULTI_REGION.md`

#### 4F. 文件與交付（第 7~10 週）🟢 可延後

- ✅ **T4-20** 使用者操作手冊 — 已完成（2026-02-07）
  - 租戶管理員手冊（公司設定、成員管理、文件上傳）
  - 一般員工使用手冊（問答操作、對話歷史）
  - 系統管理員手冊（平台監控、租戶管理、配額調整）
  - FAQ 與 Troubleshooting
  - 產出：`docs/USER_MANUAL.md`

- ✅ **T4-21** API 開發者文件 — 已完成（2026-02-07）
  - OpenAPI 3.0 規格自動產生（FastAPI 內建）
  - API 使用範例（curl / Python / JavaScript）
  - Webhook 事件說明（如未來擴充）
  - Rate Limit 說明與最佳實踐
  - 產出：`docs/API_DEVELOPER_GUIDE.md`

- ✅ **T4-22** 運維 SOP — 已完成（2026-02-07）
  - 部署流程 SOP
  - 回滾流程 SOP
  - 資料庫維護 SOP（migration、備份驗證）
  - 事故應對 SOP（P1/P2/P3 分級與處理流程）
  - 值班與通知排程
  - 產出：`docs/OPS_SOP.md`

---

### 任務依賴關係

```
Phase 0 (Core)
  T0-1 ──→ T0-2 ──→ T0-4
  T0-3 （獨立）
  T0-5 （依賴 T0-1）
  T0-6, T0-7 （獨立）
       │
       ▼ Phase 0 完成後
Phase 1 (SaaS)  ✅ 已完成
  T1-1 ──→ T1-2 ──→ T1-3 ──→ T1-4
                               │
                     T1-5 ──→ T1-6
                               │
  T0 完成 ──→ T1-7 ──→ T1-8 ──→ T1-9
                               │
                     T1-10, T1-11
                               │
                     T1-12 ──→ T1-13 ──→ T1-14
       │
       ▼ Phase 1 完成後
Phase 2 (企業化)  ✅ 已完成
  T2-3 （獨立，已完成）
  T2-2 （獨立，已完成）
  T2-1 （依賴 T1-3 Auth）
  T2-7 ──→ T2-8 （平台管理後台：API 先行，前端隨後）
  T2-4, T2-5, T2-6 （獨立，可並行）
       │
       ▼ Phase 2 完成後
Phase 3 (商業化)  ✅ 已完成
  T2-7/T2-8 ──→ T3-1 （配額管理依賴管理後台）
  T3-2 （客戶自助後台，獨立）
  T3-3, T3-4, T3-5 （獨立）
       │
       ▼ Phase 3 完成後
Phase 4 (生產化) 🟡 進行中
  ┌── 4A 前端分離 ──────────────────────────┐
  │ T4-1 (admin-frontend) ──→ T4-2 (client 精簡) │
  │ T4-3 (白標)  依賴 T4-2                       │
  └──────────────────────────────────────────┘
  ┌── 4B API 分離 ─────────────────────────────┐
  │ T4-4 (Admin 網路隔離)  依賴 T4-1            │
  │ T4-5 (API Gateway)    可與 T4-4 並行        │
  │ T4-6 (自訂 domain)    依賴 T4-3 + T4-5      │
  └──────────────────────────────────────────┘
  ┌── 4C CI/CD ─────────────────────────────┐
  │ T4-7 (CI) → T4-8 (CD) → T4-9 (映像最佳化) │
  │ 可與 4A/4B 並行                             │
  └──────────────────────────────────────────┘
  ┌── 4D 基礎建設 ──────────────────────────┐
  │ T4-10 (HTTPS)  依賴 T4-5                │
  │ T4-11 (監控) → T4-12 (日誌)  可並行     │
  │ T4-13 (備份)  獨立                       │
  └──────────────────────────────────────────┘
  ┌── 4E 效能安全 ──────────────────────────────────────┐
  │ T4-14 (負載測試)  依賴 4D 環境完成                 │
  │ T4-15 (DB 調優)   依賴 T4-14 結果                 │
  │ T4-16 (安全稽核)  獨立，上線前必完成               │
  │ T4-17 (方案計量)  獨立                             │
  │ T4-18 (Admin 微服務化) 依賴 T4-4，進階擴充        │
  │ T4-19 (多區域部署)   依賴 T4-5 + T4-18，進階擴充  │
  └────────────────────────────────────────────────┘
  ┌── 4F 文件交付 ──────────────────────────┐
  │ T4-20 ~ T4-22  可全程並行撰寫           │
  └──────────────────────────────────────────┘
```

> **Phase 4 關鍵路徑**：T4-1 → T4-2 → T4-4（前端分離 → Admin 網路隔離）是上線販售前的最高優先改造
>
> **Phase 4 上線門檻（Minimum）**：T4-1 + T4-2 + T4-4 + T4-7 + T4-10 + T4-13 + T4-16（前後台分離 + CI + HTTPS + 備份 + 安全稽核）✅ 已完成（2026-02-07）
>
> **進階擴充**：T4-18（Admin 微服務化）和 T4-19（多區域部署）為規模擴大後的進階架構改造，可在基本版上線穩定後再執行

---

## 附錄 A：名詞
- Tenant：租戶＝公司
- Core：勞資法 AI 核心 API
- SaaS：多租戶平台
- Orchestrator/BFF：協調查詢並合併答案的服務層

---

## 附錄 B：開發完成總結（2026年2月6日）

### 🎉 開發完成狀態

**✅ Phase 1: MVP** - 12/12 任務完成
- 多租戶架構、認證授權、文件管理、對話系統、稽核日誌、前端頁面
- Docker 本地部署環境完成

**✅ Phase 2: 企業化** - 8/8 任務完成  
- SSO（Google/Microsoft）、部門管理、權限細化、報表匯出、平台管理後台

**✅ Phase 3: 商業化深化** - 5/5 後端 + 前端完成
- 配額管理、客戶自助、安全隔離、API 限流、成本分析
- 52/52 測試通過
- 3 個主要管理頁面完成（AdminQuotaPage, CompanyPage, AnalyticsPage）

### 🚀 部署狀態

**✅ Docker 開發環境（本地）**
- 前端：http://localhost:3001 (Nginx 容器)
- 後端：http://localhost:8000 (FastAPI + Uvicorn)
- 數據庫：PostgreSQL 15 (端口 5432)
- 緩存：Redis 7 (端口 6379)
- 背景任務：Celery Worker
- 構建狀態：Frontend build 成功，Backend 運行正常

**⏭️ 生產環境部署（待規劃）**
- 遠端伺服器建置（雲端 VPS）
- HTTPS 與域名配置
- 系統服務化（systemd）
- 日誌與監控集中化

### 📊 技術棧總覽

**後端**
- FastAPI 0.115 + Python 3.11
- PostgreSQL 15 + SQLAlchemy 2.0
- Redis 7 + Celery
- JWT 認證 + RBAC 權限
- Pinecone 向量資料庫
- Voyage AI Embeddings

**前端**
- React 19.2 + TypeScript 5.9
- Vite 7.2 + TailwindCSS 4.1
- React Router 7.13
- Axios + Recharts
- Lucide React Icons

**DevOps**
- Docker + Docker Compose
- Alembic Migrations
- Pytest (52 測試通過)

### 📝 待辦事項

**Phase 0: Core 側改造**（獨立專案，不阻擋 SaaS）
- T0-1 ~ T0-7：Core API 版本化、認證、token 用量回傳等

**Phase 4: 生產化與前後台分離**（預估 6~10 週）
- 4A：前端拆分為系統管理台 + 客戶端（T4-1 ~ T4-3）
- 4B：Admin API 網路隔離 + API Gateway + 白標 domain（T4-4 ~ T4-6）
- 4C：CI/CD 自動化（T4-7 ~ T4-9）
- 4D：HTTPS、監控、日誌、備份（T4-10 ~ T4-13）
- 4E：負載測試、DB 調優、安全稽核、Admin 微服務化、多區域部署（T4-14 ~ T4-19）
- 4F：使用者手冊、API 文件、運維 SOP（T4-20 ~ T4-22）
- 共 22 個任務，關鍵路徑：T4-1 → T4-2 → T4-4（前後台分離是上線門檻）
