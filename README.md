# UniHR — 多租戶勞資 AI SaaS 平台

> 結合台灣勞動法專業知識與企業內規的多租戶 B2B SaaS，讓每家公司擁有獨立的 AI 問答助理、文件知識庫與管理後台。

---

## 目錄

- [系統簡介](#系統簡介)
- [核心功能](#核心功能)
- [系統架構](#系統架構)
- [技術棧](#技術棧)
- [文件處理引擎](#文件處理引擎)
- [進階檢索引擎](#進階檢索引擎)
- [多租戶隔離](#多租戶隔離)
- [前端頁面](#前端頁面)
- [API 端點](#api-端點)
- [快速開始](#快速開始)
- [環境變數](#環境變數)
- [常用指令](#常用指令)
- [測試](#測試)
- [常見問題排查](#常見問題排查)
- [備份與還原](#備份與還原)
- [生產環境維運檢查清單](#生產環境維運檢查清單)
- [目錄結構](#目錄結構)
- [開發計畫](#開發計畫)
- [文件索引](#文件索引)
- [授權](#授權)

---

## 新 PM / RD 快速上手（TL;DR）

### 1) 先確認你要看哪個環境

- **雲端（Linode / sslip.io / HTTP）**：最接近真實使用情境（含 gateway、DB、worker、網路延遲）
- **本機（Docker 開發環境）**：最快能跑起來做功能驗證與開發

### 2) 雲端（Linode）直接測試

- 使用者介面：`http://app.172-237-5-254.sslip.io`
- 系統方介面：`http://admin.172-237-5-254.sslip.io`
- API Swagger：`http://api.172-237-5-254.sslip.io/docs`

登入帳密：
- Superuser：看 Linode 上的 `/opt/aihr/.env.production`（`FIRST_SUPERUSER_EMAIL` / `FIRST_SUPERUSER_PASSWORD`）

### 3) RD 本機 10 分鐘跑起來（Docker）

```bash
cp .env.example .env
make dev
make migrate
docker-compose exec web python scripts/initial_data.py
```

### 4) 跑一次最準的雲端 E2E（建議 RD）

```powershell
$env:AIHR_BASE_URL="http://api.172-237-5-254.sslip.io"
$env:AIHR_SUPERUSER_EMAIL="<你的superuser email>"
$env:AIHR_SUPERUSER_PASS="<你的superuser password>"
C:/Users/User/Desktop/aihr/.venv/Scripts/python.exe scripts/live_e2e_test.py
```

### 5) 檢查本地與 Linode 設定一致性（建議上線前）

```powershell
# 只檢查本地 .env / .env.production
python scripts/check_local_cloud_parity.py

# 同時比對 Linode /opt/aihr/.env.production（遮罩顯示）
python scripts/check_local_cloud_parity.py --host 172.237.5.254 --user root --key C:/Users/User/.ssh/id_rsa_linode
```

---

## 系統簡介

UniHR 採用**雙層架構**：

1. **Core 層**（勞動法 AI 引擎）—— 台灣勞動法 RAG/QA 系統，持續優化法律問答品質。
2. **SaaS 層**（本專案）—— 多租戶管理平台，處理帳號、權限、企業知識庫、問答協調、稽核、用量追蹤。

員工提問時，系統同時查詢「公司內規」與「勞動法 Core」，合併產出最佳回答。

---

## 核心功能

### 多租戶管理
- 每家公司擁有獨立的空間、資料庫記錄與向量索引（pgvector per-tenant SQL 隔離）
- Row-Level Security + 中間層隔離，確保企業間資料零交叉
- 租戶配額管理（儲存空間、文件數量、每月查詢次數、Token 用量上限）

### 帳號與權限
- 五級角色：`superadmin` → `owner` → `admin` → `employee` → `viewer`
- JWT 認證 + SSO（Google / Microsoft OAuth 2.0，Email 自動識別組織）
- 三層速率限制（IP / 使用者 / 租戶）
- 前端 RoleGuard 路由守衛 + 後端統一 DI 權限檢查

### 企業知識庫
- 文件上傳 → 解析 → 切片 → 向量化 → 存入 pgvector（PostgreSQL），全流程背景處理（Celery）
- 支援 **23 種檔案格式**（詳見[文件處理引擎](#文件處理引擎)），含 LlamaParse 智慧解析
- 品質報告系統：每份文件自動評估解析品質（excellent / good / fair / poor / failed）

### AI 問答（Orchestrator）
- 混合檢索：語意搜尋 + BM25 關鍵字（jieba 分詞）+ RRF 融合 + Voyage Rerank
- HyDE 查詢擴展：生成假設性 HR 文件，提升語意檢索召回率
- LLM 答案生成：OpenAI GPT-4o-mini 根據檢索內容生成回答，僅引用提供資料，不自行捏造
- 同時查詢公司知識庫與 Core 勞動法，合併回答並標註來源
- Chunk 去重：per-document SHA256 雜湊，避免重複向量化
- 對話歷史保存，支援多輪追問
- **SSE 串流回應**：Server-Sent Events 實時串流，打字機效果即時顯示
- **Markdown 渲染**：支援 GFM 表格、程式碼高亮（rehype-highlight）、清單、標題等格式
- **來源引用面板**：可展開的參考來源顯示，區分公司政策與勞動法規，含相似度評分
- **使用者回饋系統**：👍👎 評分機制，含回饋分類與意見欄位，用於持續優化
- **後續建議**：AI 自動生成相關追問建議，引導使用者深入探索
- **對話管理**：搜尋歷史對話、匯出為 Markdown、多輪上下文理解

### 稽核與合規
- 完整操作日誌：誰問了什麼、檢索了哪些來源、回答了什麼
- **不可竄改稽核**：每筆記錄計算 SHA-256 `content_hash`，資料庫層觸發器阻擋任何 UPDATE/DELETE（保留期限內）
- **保留策略**：`expires_at = 建立時間 + 7 年`，到期後才可依規刪除（`purge_expired_audit_logs()`）
- **完整性驗證**：`verify_audit_log()` 可隨時重新計算比對 hash，偵測是否遭竄改
- 可追溯的證據鏈，滿足企業合規需求

### 用量追蹤與配額
- 每租戶 Token / Query / 向量化成本記錄
- 管理員配額管理介面，超額自動告警
- 分析儀表板：使用趨勢、熱門問題、部門統計

---

## 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React 19)                    │
│   Login · Chat · Documents · Admin · Analytics · Audit      │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                  Backend API (FastAPI)                       │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  │
│  │   Auth   │  │   Chat   │  │  Documents │  │  Admin   │  │
│  │  + SSO   │  │Orchestr. │  │  + KB API  │  │ + Audit  │  │
│  └──────────┘  └────┬─────┘  └─────┬──────┘  └──────────┘  │
│                     │              │                         │
│  ┌──────────────────▼──────────────▼───────────────────┐    │
│  │              Service Layer                          │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │  Retriever   │  │ Doc Parser   │  │  Quota    │  │    │
│  │  │Semantic+BM25 │  │ 23 Formats   │  │Enforcement│  │    │
│  │  │+HyDE+Rerank  │  │+LlamaParse   │  │ +Alerts   │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └───────────┘  │    │
│  └─────────│─────────────────│─────────────────────────┘    │
└────────────│─────────────────│──────────────────────────────┘
             │                 │
     ┌───────▼───────┐  ┌─────▼──────┐
     │  pgvector     │  │   Celery   │
     │ (PostgreSQL)  │  │   Worker   │
     │  HNSW index   │  │ (bg tasks) │
     └───────────────┘  └─────┬──────┘
                              │
┌─────────────┐  ┌───────────────┐  ┌────────────┐  ┌────────────┐
│ PostgreSQL  │  │    Redis      │  │ Voyage AI  │  │ OpenAI     │
│   15        │  │ 7 (queue+     │  │ Embedding  │  │ GPT-4o-mini│
│ (primary DB)│  │    cache)     │  │ + Rerank   │  │ +LlamaParse│
└─────────────┘  └───────────────┘  └────────────┘  └────────────┘
```

---

## 技術棧

### 後端

| 類別 | 技術 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.109.2 |
| ORM | SQLAlchemy | 2.0.27 |
| 資料庫遷移 | Alembic | 1.13.1 |
| 資料庫 | PostgreSQL | 15 |
| 快取 / 訊息佇列 | Redis | 7 |
| 背景任務 | Celery | 5.3.6 |
| 向量資料庫 | pgvector（PostgreSQL 擴充，HNSW 索引） | 0.3.0+ |
| Embedding 模型 | Voyage AI (`voyage-4-lite`, 1024 維) | 0.3.7 |
| LLM | OpenAI GPT-4o-mini (`gpt-4o-mini`) | 1.12.0 |
| 文件解析 | LlamaParse（智慧解析 10 種格式）+ 原生解析器降級 | 0.6.0+ |
| 中文分詞 | jieba（BM25 詞級分詞） | 0.42.1+ |
| 認證 | JWT (python-jose) + OAuth 2.0 SSO | — |

### 前端

| 類別 | 技術 | 版本 |
|------|------|------|
| 框架 | React | 19.2 |
| 語言 | TypeScript | 5.9 |
| 建構工具 | Vite | 7.2 |
| 樣式 | TailwindCSS | 4.1 |
| 路由 | React Router | 7.13 |
| 圖表 | Recharts | 3.7 |
| HTTP | Axios | 1.13 |
| 圖示 | Lucide React | 0.563 |
| Markdown 渲染 | react-markdown + remark-gfm + rehype-highlight | 9.x |

### 基礎設施

| 類別 | 技術 |
|------|------|
| 容器化 | Docker + Docker Compose（開發版 5 容器 / 生產版 12 容器） |
| 部署 | 支援 Development / Staging / Production 三環境 |
| 生產安全 | 啟動驗證器（config.py model_validator）、強制密碼檢查、非 root 執行 |
| 密鑰管理 | 自動密鑰生成工具（scripts/generate_secrets.py） |
| API 版本管理 | v1 (穩定) + v2 (新功能)，含 Deprecation Header |
| 監控 | Prometheus + Grafana（指標收集 + 儀錶板） |
| 閘道 | Nginx（反向代理 + SSL + 多域名路由） |

---

## 文件處理引擎

混合解析架構：**LlamaParse** 作為優先解析引擎（支援 10 種格式），品質不足時自動降級至原生解析器。原生解析器直接調用底層解析庫，精簡可控。

### 支援格式（23 種）

| 階段 | 格式 | 解析庫 | 特殊能力 |
|------|------|--------|----------|
| Phase 0 | PDF（文字型） | LlamaParse → `pypdf` | 智慧解析 + 降級 |
| Phase 0 | DOCX | LlamaParse → `python-docx` | 標題層級 + 表格提取 |
| Phase 0 | DOC | LlamaParse → `antiword` / `LibreOffice` | 舊格式降級處理 |
| Phase 0 | TXT | stdlib + `chardet` | 6 種編碼自動偵測 + BOM 清除 |
| Phase 1 | PDF（掃描型） | LlamaParse → `pytesseract` + `pdf2image` | 中英文 OCR |
| Phase 1 | PDF（表格） | LlamaParse → `pdfplumber` | 結構化表格提取 |
| Phase 1 | Excel（.xlsx/.xls） | LlamaParse → `openpyxl` | 多工作表解析 |
| Phase 1 | CSV | stdlib | 自動分隔符號偵測 |
| Phase 1 | HTML | `BeautifulSoup` + `lxml` | script/style/nav 清除、XSS 防護 |
| Phase 1 | Markdown | stdlib | 標題結構保留 |
| Phase 2 | RTF | LlamaParse → `striprtf` | RTF 控制碼清除 |
| Phase 2 | JSON | stdlib | 結構化資料 → 可讀文字 |
| Phase 2 | 圖片（JPG/PNG/TIFF/BMP） | `pytesseract` + `Pillow` | OCR + 辨識信心度 |
| Phase 6 | PPT/PPTX | LlamaParse → `python-pptx` | 投影片文字 + 備註提取 |
| Phase 6 | 網頁（URL） | `trafilatura` | 網頁主要內容擷取，去除廣告/導覽 |
| Phase 6 | 手寫文件 | LlamaParse（優先）+ `pytesseract` | 手寫體 OCR + 辨識信心度 |

> LlamaParse 支援格式：PDF、DOCX、DOC、PPTX、PPT、XLSX、XLS、RTF、EPUB、HWPX。該 10 種格式會優先使用 LlamaParse，若品質分數 < 0.5 則自動降級至原生解析器。

### 智慧切片器（TextChunker）

- **tiktoken 精確 Token 計算**（使用 OpenAI tokenizer，非估算）
- **章節邊界偵測**：遇到 Markdown `#` 標題自動開新 chunk
- **表格保護**：`[表格 N]` 區塊保持完整不拆散
- **重疊區保留**：chunk 間保留上下文（預設 150 tokens overlap）
- **碎片過濾**：自動丟棄 < 30 tokens 的碎片

### 品質報告系統（QualityReport）

每份文件解析後自動產出品質報告：

| 欄位 | 說明 |
|------|------|
| `quality_score` | 0.0 ~ 1.0 綜合分數 |
| `quality_level` | excellent / good / fair / poor / failed |
| `tables_detected` | 偵測到的表格數 |
| `ocr_used` | 是否使用 OCR |
| `ocr_confidence` | OCR 辨識信心度 |
| `encoding_detected` | 偵測到的編碼 |
| `warnings` / `errors` | 解析警告與錯誤 |
| `suggestions` | 改善建議 |
| `parse_engine` | 使用的解析引擎（`llamaparse` / `native`） |
| `handwriting_detected` | 是否偵測到手寫體 |

### Benchmark 自評結果

62 項測試 × 7 維度，**99.4/100 (A+)**：

```
A. 解析正確性    ████████████████████ 100.0%  (A+)
B. 邊界條件      ████████████████████ 100.0%  (A+)
C. 切片品質      ███████████████████░  96.0%  (A+)
D. 分詞品質      ████████████████████ 100.0%  (A+)
E. 檢索架構      ████████████████████ 100.0%  (A+)
F. 效能基準      ████████████████████ 100.0%  (A+)
G. 企業覆蓋率    ████████████████████ 100.0%  (A+)
```

---

## 進階檢索引擎

自建混合檢索系統（`KnowledgeBaseRetriever`），支援三種模式：

### 檢索模式

| 模式 | 說明 | 適用場景 |
|------|------|----------|
| `semantic` | pgvector 向量餘弦相似度（cosine distance） | 語意理解、概念匹配 |
| `keyword` | BM25Okapi 關鍵字匹配 | 精確詞彙、編號、法條查詢 |
| `hybrid`（預設） | 語意 + BM25 + RRF 融合 | 通用場景，兼顧語意與關鍵字 |

### 管線流程

```
查詢 → HyDE 查詢擴展（語意/混合模式）
       ↓
       ┬─ 語意檢索 (pgvector + Voyage Embedding，使用 HyDE 擴展查詢)
       └─ BM25 關鍵字檢索 (jieba 詞級分詞，使用原始查詢)
              ↓
       RRF 融合排序 (score = Σ 1/(k + rank), k=60)
              ↓
       Voyage Rerank-2 重排序
              ↓
       相似度閾值過濾
              ↓
       結果（含 content / score / source / metadata）
              ↓
       LLM 答案生成（OpenAI GPT-4o-mini，僅引用檢索內容）
```

### 特色

- **jieba 中文詞級分詞**：精準中文分詞（非逐字切分），支援 `NT$850,000` 等格式
- **HyDE 查詢擴展**：自動生成 50-100 字假設性 HR 文件，提升語意檢索召回率（僅語意/混合模式啟用）
- **LLM 答案生成**：OpenAI GPT-4o-mini 根據檢索結果生成回答，嚴格限制僅引用提供資料
- **Chunk 去重**：per-document SHA256 雜湊，避免重複內容進入向量庫
- **Voyage Rerank**：使用 `rerank-2` 模型對候選結果重新排序
- **Redis 查詢快取**：SHA256 cache key，5 分鐘 TTL，文件變更時自動失效
- **metadata 過濾**：支援依 `filter_dict` SQL 層級過濾 metadata 欄位
- **批次搜尋**：`batch_search()` 支援多查詢並行
- **Graceful Degradation**：Redis / BM25 不可用時自動降級

---

## 多租戶隔離

| 層級 | 隔離方式 |
|------|----------|
| 資料庫 | 所有表含 `tenant_id`，JOIN/WHERE 強制過濾 |
| 向量資料庫 | pgvector（PostgreSQL 擴充），透過 SQL `WHERE tenant_id` 隔離 |
| Row-Level Security | PostgreSQL RLS 政策，DB 層強制阻擋跨租戶查詢（`t8_1_tenant_rls` 遷移） |
| 檔案儲存 | 上傳目錄以 `tenant_id` 分隔 |
| API | 中間層從 JWT token 提取 `tenant_id`，注入所有查詢 |
| 快取 | Redis cache key 包含 `tenant_id`，不可跨租戶讀取 |

---

## 前端頁面

| 頁面 | 路徑 | 說明 |
|------|------|------|
| 登入 | `/login` | JWT 登入 + SSO（Email 自動識別組織） |
| SSO 回調 | `/login/callback` | OAuth 2.0 回調處理 |
| AI 問答 | `/` | SSE 串流對話、Markdown 渲染、來源面板、回饋按鈕、後續建議、對話搜尋、匯出 Markdown |
| RAG 儀表板 | `/rag-dashboard` | 對話量統計、延遲 P50/P95、回饋分布、每日趨勢圖表（管理員） |
| 知識庫管理 | `/documents` | 拖放上傳、狀態追蹤、部門篩選 |
| 我的用量 | `/my-usage` | 個人使用統計（所有角色） |
| 公司設定 | `/company` | 租戶基本資訊、SSO 設定 |
| 部門管理 | `/departments` | 樹狀層級結構、可收合節點 |
| 員工管理 | `/admin` | 使用者帳號管理、角色指派 |
| 用量統計 | `/usage` | Token / 查詢 / 儲存用量圖表 |
| 配額管理 | `/admin/quota` | 租戶配額設定與告警（超級管理員） |
| 分析儀表板 | `/analytics` | 使用趨勢、熱門問題、部門統計 |
| 稽核日誌 | `/audit` | 操作紀錄查詢、篩選、匯出 |
| SSO 設定 | `/sso-settings` | Google / Microsoft OAuth 設定 |
| 品牌設定 | `/branding` | Logo / 色彩 / 名稱 + 即時預覽 |
| 訂閱方案 | `/subscription` | 方案對比 + Modal 確認升級 |
| 自訂域名 | `/custom-domains` | 域名 CRUD + DNS 驗證引導 |
| 區域資訊 | `/regions` | 資料駐留區域 + 合規資訊 |

---

## API 端點

### v1 API（`/api/v1`）

| 模組 | 路由 | 功能 |
|------|------|------|
| Auth | `/auth/login`, `/auth/register` | JWT 登入 / 註冊 |
| SSO | `/sso/google`, `/sso/microsoft` | OAuth 2.0 SSO |
| Chat | `/chat/send`, `/chat/stream`, `/chat/history`, `/chat/search` | AI 問答（SSE 串流）、歷史、搜尋 |
| Feedback | `/chat/feedback` | 使用者回饋提交（評分 + 分類 + 意見） |
| RAG Dashboard | `/chat/rag-dashboard` | RAG 質量儀表板（對話量、延遲、回饋統計） |
| Documents | `/documents/upload`, `/documents/{id}` | 文件上傳 / CRUD |
| KB | `/kb/search`, `/kb/stats` | 知識庫檢索 / 統計 |
| Users | `/users/`, `/users/{id}` | 使用者管理 |
| Tenants | `/tenants/`, `/tenants/{id}` | 租戶管理 |
| Departments | `/departments/` | 部門 CRUD |
| Admin | `/admin/system/health`, `/admin/quota` | 系統管理 |
| Analytics | `/analytics/overview`, `/analytics/trends` | 數據分析 |
| Audit | `/audit/logs` | 稽核日誌 |
| Feature Flags | `/feature-flags/` | 功能開關 |

### v2 API（`/api/v2`）

新版 API，向下相容 v1，增加速率限制、版本 deprecation header。

### Admin API（`/admin`）

獨立管理微服務（port 8001），透過 Service Token 驗證，提供平台級管理功能。

| 端點 | 方法 | 說明 |
|------|------|------|
| `/admin/tenants` | GET | 全平台租戶列表 |
| `/admin/tenants/{id}` | GET/PUT | 租戶詳情與更新 |
| `/admin/tenants/{id}/quota` | PUT | 配額調整 |
| `/admin/analytics/overview` | GET | 平台營運概覽 |
| `/admin/analytics/revenue` | GET | 營收分析 |
| `/admin/health` | GET | 服務健康檢查 |

### 多區域 API（`/api/v1/regions`）

| 端點 | 方法 | 說明 |
|------|------|------|
| `/regions` | GET | 可用區域列表 |
| `/regions/current` | GET | 當前租戶區域 |
| `/regions/tenants/{id}/region` | GET/PUT | 租戶區域設定 |
| `/regions/tenants/{id}/data-residency` | GET | 資料駐留合規 |
| `/regions/compliance/summary` | GET | 全域合規摘要 |

### 訂閱與自訂網域

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/subscription/plans` | GET | 方案列表 |
| `/api/v1/subscription/current` | GET | 當前訂閱 |
| `/api/v1/subscription/change-plan` | POST | 變更方案 |
| `/api/v1/custom-domains` | GET/POST | 自訂網域管理 |
| `/api/v1/custom-domains/{id}/verify` | POST | 網域驗證 |
| `/api/v1/public/branding` | GET | 公開品牌資訊 |

---

## 生產架構

### CI/CD Pipeline（GitHub Actions）

```
Push to main
  ├─ ci.yml          → Lint + Test + Build（自動觸發）
  ├─ deploy-staging  → 部署至 Staging 環境（手動觸發）
  └─ deploy-production → 部署至 Production 環境（手動觸發，需審核）
```

### Docker 生產部署

生產環境透過 `docker-compose.prod.yml` 編排 **12 個容器**：

| 容器 | 說明 | Port | 安全特性 |
|------|------|------|----------|
| `web` | FastAPI 後端（uvicorn workers × 4） | 8000 | 無 --reload，無 volume mount，僅 uploads_data 持久化 |
| `db` | PostgreSQL 15（pgvector + 調優） | — | 不對外暴露，密碼必填檢查，資源限制 |
| `redis` | Redis 7（啟用 AOF + LRU） | — | requirepass 強制密碼，不對外暴露 |
| `worker` | Celery 背景任務 Worker | — | max-tasks-per-child=200 防記憶體洩漏 |
| `frontend` | React SPA（Nginx 靜態服務） | 80 | — |
| `admin-api` | Admin 微服務 | 8001 | Service Token 驗證 |
| `admin-frontend` | Admin 前端 SPA | 80 | — |
| `admin-redis` | Admin 獨立 Redis | — | 獨立密碼，隔離快取 |
| `gateway` | Nginx 反向代理閘道 | 80/443 | 統一入口，支援 SSL |
| `prometheus` | 監控指標收集 | 9090 | 僅內部訪問 |
| `grafana` | 監控儀錶板 | 3000 | 強制密碼，禁止註冊 |

**關鍵安全特性**：
- ✅ 所有容器 `restart: always`
- ✅ 完整健康檢查（`healthcheck`）
- ✅ 資源限制（CPU / Memory limits）
- ✅ 日誌輪替（json-file + max-size 50m）
- ✅ 非 root 使用者執行（Dockerfile 中建立 `unihr` 使用者）
- ✅ 資料庫/Redis 不對外暴露埠
- ✅ 環境變數透過 `.env.production` 管理，敏感值必填檢查（`:?` 語法）
- ✅ `app/config.py` 內建啟動驗證器，生產環境自動阻擋弱密鑰

### Nginx Gateway 多域名路由

```
app.unihr.com       → frontend + backend API
admin.unihr.com     → admin-frontend + admin-api
grafana.unihr.com   → Grafana 儀錶板
*.unihr.com         → 租戶自訂子網域
```

### 多區域部署

支援 4 個部署區域，每個區域獨立基礎設施：

| 區域代碼 | 區域名稱 | 資料駐留合規 |
|----------|----------|-------------|
| `ap` | 亞太（台灣） | PDPA |
| `us` | 北美（美國） | SOC 2 |
| `eu` | 歐洲（德國） | GDPR |
| `jp` | 日本（東京） | APPI |

使用 `docker-compose.region.yml` 覆蓋進行區域化部署。

### 監控堆疊

```
FastAPI metrics → Prometheus (scrape) → Grafana (dashboard)
                                     → Alertmanager (alerts → Slack/Email)
```

- **Prometheus**：每 15 秒抓取 `/metrics` 端點；啟用 node-exporter、postgres-exporter、redis-exporter、celery-exporter
- **Grafana**：預配置資料來源與儀錶板（自動 provisioning）
- **告警規則**：16 條規則分 4 組 — `unihr-backend`（高錯誤率/延遲/服務停機）、`unihr-security`（認證失敗激增/速率限制濫用）、`unihr-infrastructure`（Redis/PG 停機、磁碟/記憶體告警）、`unihr-celery`（Worker 停機/佇列積壓/失敗率）

---

## 快速開始

### 前置需求

- Docker & Docker Compose
- Node.js 18+（前端開發用）
- Python 3.11+（後端開發用）

### 一鍵啟動（Docker 開發環境）

```bash
# 1. 複製環境變數
cp .env.example .env

# 2. 編輯 .env 填入必要的 API keys
# 必填項目：
#   - OPENAI_API_KEY=sk-proj-...    # https://platform.openai.com/api-keys
#   - VOYAGE_API_KEY=pa-...          # https://www.voyageai.com/
#   - LLAMAPARSE_API_KEY=llx-...     # https://cloud.llamaindex.ai/
# 詳細取得方式請參閱「常見問題排查」→「API Keys 取得方式」章節

# 3. 啟動所有服務
make dev

# 4. 等待服務啟動（約 30 秒）
# 首次啟動需要下載 Docker 映像並建立資料庫

# 5. 初始化資料庫
make migrate

# 6. 建立預設管理員帳號
docker-compose exec web python scripts/initial_data.py

# 帳號/密碼來源：由環境變數 FIRST_SUPERUSER_EMAIL / FIRST_SUPERUSER_PASSWORD 決定
# 安全起見：不要把「生產環境真實密碼」寫進 README 或提交到 git。

# 7. 上傳測試文件（選用）
docker-compose exec web python scripts/batch_upload.py

# 8. 執行測試套件驗證（選用）
docker-compose exec web python scripts/run_tests.py
```

啟動後：
- **後端 API**：http://localhost:8000
- **API 文件**：http://localhost:8000/docs（Swagger UI 互動式文件）
- **前端介面**：http://localhost:3001（使用 FIRST_SUPERUSER_EMAIL / FIRST_SUPERUSER_PASSWORD 登入）
- **Admin API**：http://localhost:8001
- **Admin 文件**：http://localhost:8001/docs

**首次使用建議**：
1. 前往 http://localhost:3001 登入後台
2. 上傳 1-2 份測試文件（PDF / DOCX / TXT）
3. 等待文件處理完成（查看「知識庫管理」頁面狀態）
4. 前往「AI 問答」頁面測試提問

---

## 測試登入帳號（如何取得 / 忘記怎麼辦）

### Superuser（平台管理員）

- 系統的首位 Superuser 是由 `scripts/initial_data.py` 依照環境變數建立/確認：
- `FIRST_SUPERUSER_EMAIL`
- `FIRST_SUPERUSER_PASSWORD`
- **Linode/雲端**：請到伺服器上的 `.env.production` 查看（例如 `/opt/aihr/.env.production`）。

### E2E 測試用 HR 帳號

- `scripts/live_e2e_test.py` 會自動建立一次性 HR 測試帳號：
- Email：`hr-test-<timestamp>@example.com`
- Password：預設 `TestHR123!`（可用環境變數 `AIHR_HR_PASS` 覆蓋）
- 你跑完測試後，帳號 Email 會被寫在測試報告 `test-data/test-results/live_*/test_report.md` 的 Phase 0.4。

### 忘記密碼（建議作法）

- **不要嘗試去翻 git 歷史找密碼**（會留下外洩風險）。
- 直接在 `.env.production` 設定新的 `FIRST_SUPERUSER_PASSWORD`，然後執行：
- `docker compose -f docker-compose.prod.yml --env-file .env.production exec web python scripts/initial_data.py`
- 若該帳號已存在，請用管理 API 或 DB 方式重設（依你的維運流程）。

### 生產環境部署

#### 1. 生成密鑰與密碼

```bash
# 一鍵生成所有密鑰（SECRET_KEY、DB 密碼、Redis 密碼等）
python scripts/generate_secrets.py

# 或自動寫入 .env.production
cp .env.production.example .env.production
python scripts/generate_secrets.py --output .env.production
```

`generate_secrets.py` 會自動產生：
- `SECRET_KEY`（48 字元）
- `POSTGRES_PASSWORD`（32 字元）
- `REDIS_PASSWORD`（24 字元）
- `ADMIN_REDIS_PASSWORD`（24 字元）
- `GRAFANA_PASSWORD`（16 字元）

#### 2. 配置環境變數

編輯 `.env.production`，補充以下必填項目：

| 變數 | 說明 | 範例 |
|------|------|------|
| `FIRST_SUPERUSER_EMAIL` | 首位超級管理員 Email | `admin@yourcompany.com` |
| `FIRST_SUPERUSER_PASSWORD` | 超級管理員密碼（≥ 12 字元） | `YourStrongP@ssw0rd!` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-proj-...` |
| `VOYAGE_API_KEY` | Voyage AI API Key | `pa-...` |
| `LLAMAPARSE_API_KEY` | LlamaParse API Key | `llx-...` |
| `BACKEND_CORS_ORIGINS` | 允許的前端域名 | `https://app.yourcompany.com` |
| `CORE_API_URL` | Core 勞動法 API | `https://core.yourcompany.com` |

> ⚠️ **安全提醒**：
> - `SECRET_KEY` 必須 ≥ 32 字元隨機字串
> - 所有密碼禁用預設值（`postgres`、`admin123` 等）
> - **config.py 會在 `APP_ENV=production` 時自動檢查，若使用不安全配置將直接阻擋啟動**

#### 3. 部署方式

##### 方案 A：Linode 自動部署（推薦，支援遠端一鍵部署）

> **適用於**：已有 Linode VPS 或其他雲端 VM，想實現本地→遠端自動部署

**首次設定**（僅需一次）：

```powershell
# 1. 設定 SSH 免密碼登入（輸入伺服器密碼一次，之後永久免密碼）
.\scripts\setup_ssh_key.ps1

# 2. 初始部署（SSH 到伺服器執行）
ssh aihr-linode
cd /opt
git clone https://github.com/stevechen1112/aihr.git
cd aihr
bash scripts/deploy_linode.sh
# 腳本會暫停，提示你填寫 API keys 與超級管理員帳號
```

**之後的更新部署**（本地一鍵）：

```powershell
# 從本地 Windows 執行，自動推送代碼並觸發遠端部署
.\scripts\deploy_remote.ps1

# 進階選項
.\scripts\deploy_remote.ps1 -RestartOnly    # 僅重啟服務
.\scripts\deploy_remote.ps1 -FullDeploy     # 完整重建容器
```

**腳本會自動執行**：
1. ✅ 檢查本地 Git 更改並推送到 GitHub
2. ✅ SSH 連線到伺服器（免密碼）
3. ✅ 拉取最新代碼
4. ✅ 更新 Docker 容器
5. ✅ 執行資料庫遷移
6. ✅ 驗證服務狀態

**部署後存取**（使用 sslip.io 臨時網域）：
- **使用者介面**: http://app.172-237-5-254.sslip.io
- **系統方介面**: http://admin.172-237-5-254.sslip.io
- **API 文件**: http://api.172-237-5-254.sslip.io/docs
- **Grafana**: http://grafana.172-237-5-254.sslip.io

> 註：以上以 `172-237-5-254` 為例；若 Linode IP 有變更，sslip.io 網域也會跟著變。

> 📖 **詳細文件**:
> - [SSH 自動部署指南](docs/SSH_AUTO_DEPLOY.md) - 完整設定步驟與故障排除
> - [Linode 部署指南](docs/LINODE_DEPLOYMENT.md) - sslip.io 網域方案、SSL 配置
> - [快速參考](docs/LINODE_QUICKSTART.md) - 常用命令集合

##### 方案 B：手動部署

```bash
# 啟動所有容器（web / db / redis / worker / frontend / nginx / prometheus / grafana 等 12 個）
docker compose -f docker-compose.prod.yml up -d --build

# 等待服務啟動（約 15 秒）
sleep 15

# 執行資料庫遷移
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# 建立首位超級管理員（讀取 .env.production 配置）
docker compose -f docker-compose.prod.yml exec web python scripts/initial_data.py
```

#### 4. 驗證部署

```bash
# 檢查所有容器運行狀態
docker compose -f docker-compose.prod.yml ps

# 健康檢查（sslip.io / HTTP）
curl http://api.172-237-5-254.sslip.io/health

# 若你已配置正式網域 + HTTPS，改用：
# curl https://app.yourcompany.com/health
# curl https://admin.yourcompany.com/health

# 查看日誌
docker compose -f docker-compose.prod.yml logs -f web
```

生產環境入口：
- **前台**：https://app.yourcompany.com
- **後台**：https://admin.yourcompany.com
- **監控**：https://grafana.yourcompany.com

#### 5. 安全檢查清單

部署前請確認：

| 項目 | 狀態 |
|------|------|
| ✅ SECRET_KEY 已改為 ≥ 32 字元隨機字串 | ⬜ |
| ✅ 資料庫密碼非預設值 `postgres` | ⬜ |
| ✅ Redis 密碼已設定 | ⬜ |
| ✅ 超級管理員帳密已改為真實值 | ⬜ |
| ✅ CORS 只允許指定域名 | ⬜ |
| ✅ SSL 憑證已配置（nginx/certs/） | ⬜ |
| ✅ 所有外部 API Key 已填入 | ⬜ |
| ✅ Grafana 管理員密碼已修改 | ⬜ |
| ✅ 防火牆只開放 80/443 | ⬜ |
| ✅ PostgreSQL / Redis 未對外暴露 | ⬜ |

### 本地開發（不使用 Docker）

```bash
# 後端
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev

# Admin 微服務
cd admin_service
uvicorn main:app --reload --port 8001
```

---

## 環境變數

### 必填變數（生產環境）

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `SECRET_KEY` | JWT 簽名密鑰（≥ 32 字元） | ✅ | — |
| `FIRST_SUPERUSER_EMAIL` | 首位超級管理員 Email | ✅ | — |
| `FIRST_SUPERUSER_PASSWORD` | 超級管理員密碼（≥ 12 字元） | ✅ | — |
| `POSTGRES_PASSWORD` | PostgreSQL 密碼 | ✅ | `postgres` |
| `REDIS_PASSWORD` | Redis 密碼 | ✅ | — |
| `ADMIN_REDIS_PASSWORD` | Admin Redis 密碼 | ✅ | — |
| `OPENAI_API_KEY` | OpenAI API Key | ✅ | — |
| `VOYAGE_API_KEY` | Voyage AI（Embedding + Rerank） | ✅ | — |
| `GRAFANA_PASSWORD` | Grafana 管理員密碼 | ✅ | `admin` |

### AI / LLM 設定

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `OPENAI_MODEL` | OpenAI 模型名稱 | — | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | LLM 生成溫度 | — | `0.3` |
| `OPENAI_MAX_TOKENS` | LLM 最大輸出 Token | — | `1500` |
| `LLAMAPARSE_API_KEY` | LlamaParse 文件解析 API Key | — | — |
| `LLAMAPARSE_ENABLED` | 啟用 LlamaParse 解析 | — | `true` |
| `EMBEDDING_DIMENSION` | 向量維度 | — | `1024` |

### 資料庫設定

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `POSTGRES_SERVER` | PostgreSQL 主機 | — | `localhost` |
| `POSTGRES_USER` | 資料庫使用者 | — | `postgres` |
| `POSTGRES_DB` | 資料庫名稱 | — | `unihr_saas` |
| `REDIS_HOST` | Redis 主機 | — | `localhost` |
| `CELERY_BROKER_URL` | Celery Broker URL | — | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery 結果後端 | — | `redis://redis:6379/0` |

### 外部服務設定

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `CORE_API_URL` | Core 勞動法 API 位址 | — | `http://localhost:5000` |
| `GOOGLE_CLIENT_ID` | Google SSO | — | — |
| `GOOGLE_CLIENT_SECRET` | Google SSO Secret | — | — |
| `MICROSOFT_CLIENT_ID` | Microsoft SSO | — | — |
| `MICROSOFT_CLIENT_SECRET` | Microsoft SSO Secret | — | — |
| `SSO_DEFAULT_REDIRECT_URI` | SSO 回調 URI | — | `http://localhost:3001/login/callback` |

### 檢索與快取設定

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `RETRIEVAL_MODE` | 檢索模式（semantic / keyword / hybrid） | — | `hybrid` |
| `RETRIEVAL_RERANK` | 啟用重排序 | — | `true` |
| `RETRIEVAL_CACHE_TTL` | 快取 TTL（秒） | — | `300` |
| `RETRIEVAL_TOP_K` | 預設返回數量 | — | `5` |

### 安全與速率限制

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `RATE_LIMIT_ENABLED` | 啟用速率限制 | — | `true` |
| `RATE_LIMIT_GLOBAL_PER_IP` | IP 速率（req/min） | — | `200` |
| `RATE_LIMIT_PER_USER` | 使用者速率（req/min） | — | `60` |
| `RATE_LIMIT_PER_TENANT` | 租戶速率（req/min） | — | `300` |
| `RATE_LIMIT_CHAT_PER_USER` | 聊天速率（req/min） | — | `20` |
| `ADMIN_IP_WHITELIST_ENABLED` | 啟用 Admin IP 白名單 | — | `false` |
| `ADMIN_IP_WHITELIST` | 允許的 IP / CIDR | — | `127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | Redis 連線逾時（秒） | — | `2` |
| `REDIS_SOCKET_TIMEOUT` | Redis 操作逾時（秒） | — | `2` |
| `REDIS_SOCKET_KEEPALIVE` | 啟用 TCP Keep-Alive | — | `true` |
| `REDIS_HEALTH_CHECK_INTERVAL` | Redis Ping 健康確認間隔（秒） | — | `30` |
| `AUDIT_RETENTION_YEARS` | 稽核日誌保留年限 | — | `7` |

### 微服務與區域設定

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `ADMIN_SERVICE_TOKEN` | Admin 微服務 Token | ✅（生產） | — |
| `DEPLOY_REGION` | 部署區域代碼 | — | `ap` |
| `GRAFANA_ROOT_URL` | Grafana 外部 URL | — | `https://grafana.unihr.com` |
| `BACKEND_CORS_ORIGINS` | 允許的 CORS 來源（逗號分隔） | — | `http://localhost:3000,http://localhost:3001` |

完整列表參見：
- 開發：[.env.example](.env.example)
- Staging：[.env.staging.example](.env.staging.example) 
- 生產：[.env.production.example](.env.production.example)

> ⚠️ **生產環境安全提示**：  
> `app/config.py` 含 `model_validator`，在 `APP_ENV=production` 或 `staging` 時會自動檢查：
> - `SECRET_KEY` 不可為已知弱預設值或 < 32 字元 → **直接 raise ValueError 阻擋啟動**
> - `POSTGRES_PASSWORD` 不可為 `"postgres"` → **直接 raise ValueError 阻擋啟動**
> - `FIRST_SUPERUSER_EMAIL` 仍為 `"admin@example.com"` → **發出 UserWarning**
> - `FIRST_SUPERUSER_PASSWORD` 仍為 `"admin123"` → **發出 UserWarning**

---

## 常用指令

```bash
# === 開發環境 ===
make dev                # 啟動開發環境
make down               # 停止所有服務
make down-v             # 停止並清除資料
make logs               # 查看所有日誌
make logs-web           # 查看後端日誌
make logs-worker        # 查看 Worker 日誌
make migrate            # 執行資料庫遷移
make migrate-create     # 建立新遷移檔
make shell              # 進入後端容器 shell
make db-shell           # 進入 PostgreSQL shell
make redis-cli          # 進入 Redis CLI
make status             # 查看服務狀態
make health             # 健康檢查
make build              # 重建所有容器

# === 生產密鑰生成 ===
# 生成所有密鑰（顯示在終端）
python scripts/generate_secrets.py

# 自動寫入 .env.production
python scripts/generate_secrets.py --output .env.production

# === 部署 ===
make staging            # 啟動 Staging 環境
make prod               # 啟動 Production 環境（12 容器）

# 手動啟動生產環境
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
docker compose -f docker-compose.prod.yml exec web python scripts/initial_data.py
```

---

## 測試

### 後端單元測試

```bash
# 執行全部測試（52 項）
python -m pytest tests/ -v

# 文件引擎測試（90 項）
python tests/test_document_engine.py

# 文件引擎 Benchmark（62 項，含效能基準）
python tests/benchmark_document_engine.py
```

### 負載測試

```bash
# Locust 負載測試
cd tests/load
locust -f locustfile.py --host http://localhost:8000

# k6 負載測試
k6 run tests/load/k6_load_test.js
```

### 測試涵蓋範圍

| 測試檔案 | 測試項目 | 數量 |
|----------|----------|------|
| `test_tenant_isolation.py` | 租戶資料隔離 | 6 |
| `test_permissions.py` | 角色權限控制 | 8 |
| `test_usage_tracking.py` | 用量追蹤 | 5 |
| `test_e2e_chat.py` | 端對端問答 | 6 |
| `test_company_admin.py` | 公司管理 | 5 |
| `test_quota_management.py` | 配額管理 | 6 |
| `test_analytics_security.py` | 分析安全性 | 5 |
| `test_sso_security.py` | SSO 安全性 | 5 |
| `test_feature_flags_logic.py` | 功能開關 | 6 |
| `test_document_engine.py` | 文件處理引擎 | 90 |
| `benchmark_document_engine.py` | 能力自評 Benchmark | 62 |
| `test_cross_tenant_pentest.py` | 跨租戶滲透測試（IDOR / 越級存取） | — |
| `test_llm_security_guardrails.py` | LLM 安全護欄（Prompt 注入 / 資料外洩） | — |
| `test_load.py` | Locust 壓力 + 安全探測（NormalUser / SecurityProbe / RateLimitStress） | — |
| `tests/load/locustfile.py` | HTTP 負載測試 | — |
| `tests/load/k6_load_test.js` | k6 效能測試 | — |

---

## 常見問題排查

### 容器無法啟動

**問題**：`docker-compose up -d` 失敗

**排查步驟**：
```powershell
# 1. 檢查容器狀態
docker-compose ps

# 2. 查看失敗容器的日誌
docker-compose logs web
docker-compose logs db

# 3. 檢查埠號佔用
netstat -ano | findstr "8000"
netstat -ano | findstr "5432"

# 4. 清除舊容器重新啟動
docker-compose down -v
docker-compose up -d --build
```

**常見原因**：
- 埠號被佔用（8000 / 5432 / 6379）
- `.env` 檔案格式錯誤或缺少必填欄位
- Docker Desktop 未啟動或記憶體不足

### 生產環境啟動失敗

**問題**：`APP_ENV=production` 時因為安全檢查無法啟動

**錯誤訊息**：
```
ValueError: SECRET_KEY is insecure ('change_t…'). Set a strong random key (≥ 32 chars)
```

**解決方案**：
```powershell
# 1. 生成安全密鑰
python scripts/generate_secrets.py --output .env.production

# 2. 手動填入 API Keys 與管理員資訊
# 編輯 .env.production，確保以下欄位已填入：
# - SECRET_KEY（≥ 32 字元）
# - POSTGRES_PASSWORD（非 'postgres'）
# - FIRST_SUPERUSER_EMAIL（真實 email）
# - FIRST_SUPERUSER_PASSWORD（強密碼）
# - OPENAI_API_KEY
# - VOYAGE_API_KEY
# - LLAMAPARSE_API_KEY

# 3. 重新啟動
docker compose -f docker-compose.prod.yml up -d
```

### API Keys 取得方式

| 服務 | 用途 | 取得網址 | 費用 |
|------|------|----------|------|
| OpenAI | LLM 生成 + HyDE 查詢擴展 | https://platform.openai.com/api-keys | 依用量計費 |
| Voyage AI | Embedding (voyage-4-lite) + Rerank (rerank-2) | https://www.voyageai.com/ | 前 100M tokens 免費 |
| LlamaParse | 高品質文件解析（PDF/DOCX/PPT） | https://cloud.llamaindex.ai/ | 前 1000 頁免費 |

**OpenAI 設定**：
1. 註冊 OpenAI 帳號，前往 [API Keys](https://platform.openai.com/api-keys)
2. 點擊「Create new secret key」
3. 複製 `sk-proj-...` 開頭的 key
4. 貼入 `.env` 的 `OPENAI_API_KEY`

**Voyage AI 設定**：
1. 註冊 Voyage AI 帳號，前往 [Dashboard](https://www.voyageai.com/)
2. 複製 API Key（`pa-...` 開頭）
3. 貼入 `.env` 的 `VOYAGE_API_KEY`

**LlamaParse 設定**：
1. 註冊 LlamaIndex 帳號，前往 [LlamaCloud](https://cloud.llamaindex.ai/)
2. 複製 API Key（`llx-...` 開頭）
3. 貼入 `.env` 的 `LLAMAPARSE_API_KEY`

### 資料庫連線失敗

**問題**：`FATAL: password authentication failed for user "postgres"`

**解決方案**：
```powershell
# 1. 檢查 .env 中的資料庫密碼
Get-Content .env | Select-String "POSTGRES"

# 2. 清除舊的 volume 並重建
docker-compose down -v
docker volume prune -f
docker-compose up -d

# 3. 等待資料庫初始化完成（約 10 秒）
Start-Sleep -Seconds 10

# 4. 執行遷移
docker-compose exec web alembic upgrade head
```

### 測試套件失敗

**問題**：`scripts/run_tests.py` 某些問題答不出來或分數低

**排查步驟**：
```powershell
# 1. 確認所有文件已上傳
docker-compose exec web python scripts/batch_upload.py

# 2. 檢查 Redis 快取是否需要清除
docker-compose exec redis redis-cli FLUSHDB

# 3. 重啟服務確保程式碼已重新載入（Windows Docker 不會自動 reload）
docker-compose restart web worker

# 4. 檢查結構化答案 handler
docker-compose exec web python scripts/test_structured.py
```

### Chunk 去重問題

**問題**：重複上傳相同文件後，第二份文件沒有 chunks

**原因**：`document_tasks.py` 的 chunk 去重邏輯錯誤（tenant-scoped 而非 document-scoped）

**已修復**：Phase 8 已將去重改為 per-document SHA256 檢查

**驗證修復**：
```python
# 檢查 document_tasks.py 第 130 行左右
# 應該是：DChunk.document_id == UUID(document_id)
# 而非：DChunk.tenant_id == UUID(tenant_id)
```

### 前端無法連線後端

**問題**：前端顯示 `Network Error` 或 CORS 錯誤

**解決方案**：
```powershell
# 1. 檢查後端是否運行
curl http://localhost:8000/health

# 2. 檢查 CORS 設定
docker-compose exec web python -c "from app.config import settings; print(settings.BACKEND_CORS_ORIGINS)"

# 3. 更新 .env 的 CORS 設定
# BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002

# 4. 重啟容器
docker-compose restart web
```

### Celery Worker 處理文件卡住

**問題**：上傳文件後一直顯示 `processing`

**排查步驟**：
```powershell
# 1. 檢查 worker 日誌
docker-compose logs worker --tail=50

# 2. 檢查任務佇列
docker-compose exec redis redis-cli LLEN celery

# 3. 檢查是否有任務失敗
docker-compose exec web python -c "from app.celery_app import celery_app; print(celery_app.control.inspect().active())"

# 4. 重啟 worker
docker-compose restart worker
```

---

## 備份與還原

### PostgreSQL 資料庫備份

```powershell
# 開發環境
docker-compose exec db pg_dump -U postgres unihr_saas > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# 生產環境
docker compose -f docker-compose.prod.yml exec db pg_dump -U unihr unihr_saas > backup_prod_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# 自動備份腳本（已提供）
./scripts/backup.sh
```

### 資料庫還原

```powershell
# 1. 停止服務
docker-compose down

# 2. 重新啟動資料庫
docker-compose up -d db

# 3. 還原備份
Get-Content backup_20260211_120000.sql | docker-compose exec -T db psql -U postgres unihr_saas

# 4. 啟動其他服務
docker-compose up -d
```

### 備份還原驗證（自動化）

```bash
# 完整 4 步驟沙盒驗證：備份 → gzip 完整性 → sandbox 還原 → 資料表數量核對
bash scripts/verify_backup.sh

# 也可傳入已有備份檔
bash scripts/verify_backup.sh /path/to/backup.sql.gz

# 建議排程（crontab）
# 0 2 * * *   /opt/aihr/scripts/backup.sh          # 每日 02:00 備份
# 0 3 * * 0   /opt/aihr/scripts/verify_backup.sh   # 每週日 03:00 驗證
```

### 上傳檔案備份

```powershell
# 備份上傳目錄
Compress-Archive -Path uploads -DestinationPath uploads_backup_$(Get-Date -Format "yyyyMMdd").zip

# 還原
Expand-Archive -Path uploads_backup_20260211.zip -DestinationPath uploads -Force
```

### 完整系統備份

```powershell
# 1. 資料庫備份
docker-compose exec db pg_dump -U postgres unihr_saas > db_backup.sql

# 2. 上傳檔案備份
Compress-Archive -Path uploads -DestinationPath uploads_backup.zip

# 3. 環境變數備份（注意：不要提交到 Git）
Copy-Item .env .env.backup

# 4. Redis 資料備份（選用）
docker-compose exec redis redis-cli SAVE
Copy-Item redis_data/dump.rdb redis_backup.rdb
```

---

## 生產環境維運檢查清單

### 部署前檢查

- [ ] `.env.production` 所有必填欄位已填入
- [ ] SECRET_KEY 強度 ≥ 32 字元
- [ ] 資料庫密碼非預設值
- [ ] 超級管理員帳密已修改
- [ ] 所有 API Keys 已取得並填入
- [ ] CORS 只允許指定域名
- [ ] SSL 憑證已準備（nginx/certs/）
- [ ] 防火牆規則已設定（僅開放 80/443）
- [ ] PostgreSQL / Redis 未對外暴露

### 部署後驗證

```powershell
# 1. 檢查所有容器運行狀態
docker compose -f docker-compose.prod.yml ps

# 2. 健康檢查
curl https://app.yourcompany.com/health
curl https://admin.yourcompany.com/health

# 3. 測試登入
# 前往 https://app.yourcompany.com/login
# 使用 FIRST_SUPERUSER_EMAIL / PASSWORD 登入

# 4. 檢查資料庫遷移
docker compose -f docker-compose.prod.yml exec web alembic current

# 5. 檢查 Celery Worker
docker compose -f docker-compose.prod.yml logs worker --tail=20

# 6. 檢查監控
# 前往 https://grafana.yourcompany.com
# 使用 GRAFANA_PASSWORD 登入
```

### 每日檢查

- [ ] 檢查容器狀態：`docker compose -f docker-compose.prod.yml ps`
- [ ] 檢查磁碟空間：`df -h`
- [ ] 檢查錯誤日誌：`docker compose -f docker-compose.prod.yml logs --tail=100 | Select-String "ERROR"`
- [ ] 檢查 Grafana 告警
- [ ] 執行資料庫備份

### 每週檢查

- [ ] 檢查 PostgreSQL 效能：`docker compose -f docker-compose.prod.yml exec db psql -U unihr -c "SELECT * FROM pg_stat_activity;"`
- [ ] 檢查 Redis 記憶體使用：`docker compose -f docker-compose.prod.yml exec redis redis-cli INFO memory`
- [ ] 檢查磁碟 I/O：查看 Grafana 儀錶板
- [ ] 審查稽核日誌
- [ ] 測試備份還原流程

### 每月檢查

- [ ] 更新 Docker 映像：`docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d`
- [ ] 檢查安全性更新
- [ ] 審查用量統計與配額
- [ ] 執行負載測試
- [ ] 審查 SSL 憑證有效期

---

## 目錄結構

```
unihr-saas/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 環境設定（Pydantic Settings）
│   ├── celery_app.py              # Celery 設定
│   ├── api/
│   │   ├── v1/endpoints/          # v1 API 端點
│   │   │   ├── auth.py            #   認證
│   │   │   ├── chat.py            #   AI 問答
│   │   │   ├── documents.py       #   文件管理
│   │   │   ├── kb.py              #   知識庫檢索
│   │   │   ├── users.py           #   使用者管理
│   │   │   ├── tenants.py         #   租戶管理
│   │   │   ├── admin.py           #   系統管理
│   │   │   ├── analytics.py       #   數據分析
│   │   │   ├── audit.py           #   稽核日誌
│   │   │   ├── departments.py     #   部門管理
│   │   │   ├── sso.py             #   SSO 端點
│   │   │   ├── feature_flags.py   #   功能開關
│   │   │   ├── tenant_admin.py    #   租戶管理員
│   │   │   ├── subscription.py    #   訂閱方案管理
│   │   │   ├── custom_domains.py  #   自訂網域
│   │   │   ├── regions.py         #   多區域管理
│   │   │   └── public.py          #   公開品牌端點
│   │   └── v2/                    # v2 API（向下相容 v1）
│   ├── models/                    # SQLAlchemy 模型
│   │   ├── tenant.py              #   租戶 + 配額 + 方案 + 品牌
│   │   ├── user.py                #   使用者
│   │   ├── document.py            #   文件 + 切片
│   │   ├── chat.py                #   對話 + 訊息
│   │   ├── feedback.py            # ★ 使用者回饋（rating 1=👎, 2=👍）
│   │   ├── audit.py               #   稽核記錄
│   │   ├── permission.py          #   權限
│   │   ├── sso_config.py          #   SSO 設定
│   │   ├── feature_flag.py        #   功能開關
│   │   └── custom_domain.py       #   自訂網域
│   ├── schemas/                   # Pydantic Schemas
│   ├── core/
│   │   └── redis_client.py        # ★ Redis 執行緒安全單例 + 輕量熔斷器（Phase 9）
│   ├── crud/                      # 資料存取層
│   ├── services/                  # 核心業務邏輯
│   │   ├── document_parser.py     #   多格式解析引擎（LlamaParse + 原生，~1320 行）
│   │   ├── kb_retrieval.py        #   進階檢索引擎（jieba + HyDE，~595 行）
│   │   ├── chat_orchestrator.py   #   問答協調器（LLM 生成 + 降級）
│   │   ├── core_client.py         #   Core API 客戶端
│   │   ├── quota_enforcement.py   #   配額執行
│   │   ├── quota_alerts.py        #   配額告警
│   │   ├── security_isolation.py  #   安全隔離
│   │   └── feature_flags.py       #   功能開關
│   ├── tasks/                     # Celery 背景任務
│   │   └── document_tasks.py      #   文件處理任務
│   ├── middleware/                 # 中間件
│   │   ├── rate_limit.py          #   速率限制
│   │   └── versioning.py          #   API 版本管理
│   └── db/                        # 資料庫連線
├── admin_service/                 # ★ Admin 獨立微服務
│   ├── __init__.py                #   FastAPI app + Service Token 中間件
│   ├── main.py                    #   入口（port 8001）
│   ├── db.py                      #   資料庫連線
│   ├── cache.py                   #   Redis 快取
│   └── Dockerfile                 #   Docker 映像
├── frontend/                      # 租戶前端（React 19）
│   └── src/
│       ├── App.tsx                # 路由設定
│       ├── api.ts                 # API 客戶端
│       ├── auth.tsx               # 認證 Context
│       ├── types.ts               # TypeScript 型別
│       ├── components/
│       │   ├── Layout.tsx         # 側邊欄導覽 Layout
│       │   └── chat/              # ★ Phase 7 對話組件
│       │       ├── MarkdownRenderer.tsx   # Markdown 渲染（GFM + 程式碼高亮）
│       │       ├── SourcePanel.tsx        # 來源引用面板（可展開）
│       │       ├── FeedbackButtons.tsx    # 回饋按鈕（👍👎）
│       │       ├── FollowUpSuggestions.tsx # 後續建議顯示
│       │       └── TypingIndicator.tsx    # 打字指示器
│       └── pages/                 # 頁面元件（18 頁）
│           ├── LoginPage.tsx       #   登入 + SSO Email 自動識別
│           ├── ChatPage.tsx        # ★ SSE 串流對話 + Markdown + 來源 + 回饋 + 搜尋 + 匯出
│           ├── RAGDashboardPage.tsx # ★ RAG 質量儀表板（P50/P95 延遲、回饋統計）
│           ├── DocumentsPage.tsx    #   文件管理 + 部門篩選
│           ├── MyUsagePage.tsx      # ★ 個人用量統計
│           ├── CompanyPage.tsx
│           ├── AdminPage.tsx
│           ├── AdminQuotaPage.tsx
│           ├── AnalyticsPage.tsx
│           ├── AuditLogsPage.tsx
│           ├── DepartmentsPage.tsx  #   樹狀層級結構
│           ├── UsagePage.tsx
│           ├── SSOSettingsPage.tsx
│           ├── SSOCallbackPage.tsx
│           ├── BrandingPage.tsx     #   品牌設定 + 即時預覽
│           ├── SubscriptionPage.tsx #   訂閱 + Modal 升級確認
│           ├── CustomDomainsPage.tsx # ★ 自訂域名 CRUD
│           └── RegionsPage.tsx     # ★ 區域與資料駐留
├── admin-frontend/                # ★ 管理員後台前端
│   └── src/
│       ├── App.tsx                # 後台路由
│       ├── api.ts                 # Admin API 客戶端
│       ├── auth.tsx               # 管理員認證
│       └── pages/                 # 後台頁面
│           ├── LoginPage.tsx
│           ├── AdminPage.tsx
│           ├── AdminQuotaPage.tsx
│           └── AnalyticsPage.tsx
├── nginx/                         # ★ Nginx 閘道設定
│   ├── gateway.conf               #   多域名反向代理（app/admin/grafana）
│   ├── admin.conf                 #   Admin 站點設定
│   └── client.conf                #   租戶站點設定
├── monitoring/                    # ★ 監控堆疊
│   ├── prometheus.yml             #   Prometheus 抓取設定
│   ├── alert_rules.yml            #   告警規則
│   └── grafana/
│       └── provisioning/          #   Grafana 自動配置
├── configs/                       # ★ 資料庫調優
│   └── postgresql-tuning.conf     #   PostgreSQL 效能調優參數
├── .github/workflows/             # ★ CI/CD Pipeline
│   ├── ci.yml                     #   持續整合（Lint + Test + Build）
│   ├── deploy-staging.yml         #   Staging 部署
│   └── deploy-production.yml      #   Production 部署
├── tests/                         # 測試套件
│   ├── test_*.py                  #   單元測試（52 項）
│   ├── benchmark_document_engine.py  # 效能基準測試
│   └── load/                      # ★ 負載測試
│       ├── locustfile.py          #   Locust 負載測試
│       ├── k6_load_test.js        #   k6 效能測試
│       └── results/               #   測試結果
├── alembic/                       # 資料庫遷移
│   └── versions/                  #   遷移版本鏈
│       ├── t7_5_feedback.py       # ★ Phase 7: chat_feedbacks 表（評分+分類+意見）
│       ├── t8_1_tenant_rls.py     # ★ Phase 9: PostgreSQL Row-Level Security 政策
│       └── t8_2_audit_immutable.py # ★ Phase 9: 稽核不可竄改（content_hash + expires_at + PG trigger）
├── scripts/                       # 工具腳本
│   ├── create_tables.py           #   資料表建立
│   ├── create_test_users.py       #   測試帳號建立
│   ├── generate_secrets.py        # ★ 生產密鑰生成工具（SECRET_KEY / POSTGRES_PASSWORD / REDIS_PASSWORD 等）
│   ├── verify_backup.sh           # ★ Phase 9: 備份還原自動化驗證（4 步驟沙盒）
│   └── initial_data.py            #   初始化資料（讀取 FIRST_SUPERUSER_EMAIL/PASSWORD）
├── docs/                          # 專案文件
│   ├── PROJECT_PLAN.md            #   完整產品規格書（1500+ 行）
│   ├── API_GUIDE.md               #   API 使用指南
│   ├── API_DEVELOPER_GUIDE.md     # ★ API 開發者整合指南
│   ├── USER_MANUAL.md             # ★ 使用者操作手冊
│   ├── OPS_SOP.md                 # ★ 維運 SOP
│   ├── MULTI_REGION.md            # ★ 多區域部署指南
│   ├── UX_FLOW_REVIEW.md          # ★ UX 流程全角色檢視報告
│   ├── PHASE2_TEST_REPORT.md      #   Phase 2 測試報告
│   ├── PHASE3_TEST_REPORT.md      #   Phase 3 測試報告
│   ├── PHASE7_UPGRADE_PROPOSAL.md # ★ Phase 7 升級提案（對話體驗升級）
│   ├── QUALITY_PERFORMANCE_REPORT.md # Phase 9 品質效能報告
│   ├── RLS_ROLLOUT_PLAN.md        # ★ Phase 9: RLS 分階段啟用計畫
│   └── TENANT_ISOLATION_RISK_AUDIT.md # ★ Phase 9: 租戶隔離風險稽核報告
├── docker-compose.yml             # 開發環境
├── docker-compose.staging.yml     # Staging 覆蓋
├── docker-compose.prod.yml        # ★ 生產環境（12 容器）
├── docker-compose.region.yml      # ★ 多區域覆蓋
├── docker-compose.production.yml  # Production 覆蓋
├── .env.example                   # 開發環境變數範本
├── .env.staging.example           # ★ Staging 環境變數範本
├── .env.production.example        # ★ Production 環境變數範本
├── .env.development.example       # ★ 開發環境變數範本
├── Dockerfile                     # 後端映像
├── Makefile                       # 常用指令
├── requirements.txt               # Python 依賴
└── requirements-test.txt          # ★ 測試依賴
```

> ★ 標記為 Phase 4/5 新增項目

---

## 開發計畫

| 階段 | 內容 | 狀態 |
|------|------|------|
| Phase 1 | 基礎建設：多租戶 + 認證 + 文件管線 + AI 問答 | ✅ 完成 |
| Phase 2 | 安全強化：SSO + 速率限制 + API 版本 + 功能旗標 | ✅ 完成 |
| Phase 3 | 管理功能：配額 + 分析 + 前端頁面 | ✅ 完成 |
| Phase 3+ | 文件引擎升級：19 格式 + 進階檢索 + 混合搜尋 | ✅ 完成 |
| Phase 4 | 生產化：前後台分離 + CI/CD + 白標 + 監控 + 安全稽核 + 微服務化 + 多區域（22 任務） | ✅ 完成 |
| Phase 5 | UX 流程審查：全角色 UX 檢視 + 11 項修復（路由守衛 + SSO 自動識別 + 權限 DI 統一 + UI 增強） | ✅ 完成 |
| Phase 6 | AI 引擎升級：LlamaParse 智慧解析 + jieba 分詞 + HyDE 查詢擴展 + LLM 答案生成 + Chunk 去重 | ✅ 完成 |
| Phase 7 | 對話體驗升級：SSE 串流 + Markdown 渲染 + 來源面板 + 回饋系統 + RAG 儀表板 + 行動版響應式（15 任務） | ✅ 完成 |
| Phase 8 | 生產安全加固：config.py 啟動驗證器 + 密鑰生成工具 + docker-compose.prod.yml 強化（15 項安全特性） | ✅ 完成 |
| Phase 9 | 縱深防禦加固：Redis 熔斷 + 不可竄改稽核 + RLS + 備份驗證 + 安全監控告警 + 壓力測試（7 項） | ✅ 完成 |

### Phase 9 任務清單（縱深防禦加固 — 完成）

| 項目 | 說明 | 狀態 |
|------|------|------|
| SEC-15 | Redis SPOF 輕量防護：執行緒安全單例 + Ping 熔斷，不可用時自動允許通過（不阻斷服務） | ✅ |
| SEC-16 | PostgreSQL 備份排程強化：WAL 串流複製前置設定（`wal_level=replica`）+ healthcheck | ✅ |
| SEC-17 | 備份還原驗證腳本：4 步驟沙盒驗證（gzip 完整性 → sandbox restore → 資料量核對） | ✅ |
| SEC-18 | 不可竄改稽核日誌：SHA-256 hash + `expires_at` + PG BEFORE 觸發器 + 自動淨化 | ✅ |
| SEC-19 | 安全監控告警擴充：4 → 16 條規則（security/infra/celery 3 個新群組）+ 啟用 4 個 exporter | ✅ |
| SEC-20 | PostgreSQL Row-Level Security：Alembic 遷移 + 分階段啟用計畫（`RLS_ENFORCEMENT_ENABLED`） | ✅ |
| SEC-21 | 壓力 + 安全探測測試：Locust `test_load.py`（NormalUser/SecurityProbe/RateLimitStress）+ 驗收鉤子 | ✅ |

### Phase 8 任務清單（生產安全加固 — 完成）

| 項目 | 說明 | 狀態 |
|------|------|------|
| SEC-1 | config.py 新增 `model_validator`，生產環境自動檢查 SECRET_KEY / POSTGRES_PASSWORD 是否安全 | ✅ |
| SEC-2 | 新增 `FIRST_SUPERUSER_EMAIL` / `FIRST_SUPERUSER_PASSWORD` 配置，取代硬編碼 `admin@example.com / admin123` | ✅ |
| SEC-3 | `scripts/initial_data.py` 改為讀取 `settings.FIRST_SUPERUSER_*`，使用預設值時發出警告 | ✅ |
| SEC-4 | `scripts/generate_secrets.py` — 一鍵生成 SECRET_KEY / DB 密碼 / Redis 密碼等，支援自動寫入 `.env.production` | ✅ |
| SEC-5 | `docker-compose.prod.yml` 重寫：移除 `--reload`、移除 `.:/code` volume mount、改用 pgvector 正確映像 | ✅ |
| SEC-6 | 生產環境 Redis 加入 `--requirepass` + `maxmemory` + AOF 持久化 | ✅ |
| SEC-7 | PostgreSQL 密碼改用 `:?` 語法強制必填檢查 | ✅ |
| SEC-8 | 所有容器加入 `healthcheck` + `restart: always` + 資源限制 | ✅ |
| SEC-9 | 日誌輪替設定（json-file + max-size 50m + max-file 5） | ✅ |
| SEC-10 | 新增 `uploads_data` named volume，取代 `.:/code` 掛載 | ✅ |
| SEC-11 | Celery worker 加入 `--max-tasks-per-child=200` 防記憶體洩漏 | ✅ |
| SEC-12 | `.env.production.example` 完整模板，含所有必填欄位標註 + 生成密鑰指令 | ✅ |
| SEC-13 | `docker-compose.production.yml`（override 版本）同步更新 | ✅ |
| SEC-14 | README.md 新增「生產環境部署」章節，含 5 步驟詳細說明 + 安全檢查清單 | ✅ |
| SEC-15 | 環境變數章節重構，依類別分組，標註必填項目與安全警告 | ✅ |

### Phase 7 任務清單（對話體驗升級 — 15/15 完成）

| 項目 | 說明 | 優先級 | 狀態 |
|------|------|--------|------|
| T7-0 | Orchestrator 重構：retrieve_context、stream_answer、contextualize_query 三階段分離 | P0 | ✅ |
| T7-1 | SSE 串流後端 + 前端 ReadableStream 解析器（status/sources/token/suggestions/done/error 事件） | P0 | ✅ |
| T7-2 | 多輪對話上下文：歷史訊息注入 + query contextualization（改寫查詢） | P0 | ✅ |
| T7-3 | Markdown 渲染器：react-markdown + remark-gfm（表格）+ rehype-highlight（程式碼高亮） | P1 | ✅ |
| T7-4 | 來源面板：可展開的參考來源顯示，區分 policy/law，含相似度評分與摘要 | P1 | ✅ |
| T7-5 | 使用者回饋系統：資料模型 + API 端點 + 前端 FeedbackButtons（👍👎） | P1 | ✅ |
| T7-6 | 後續建議：LLM 解析生成 3 個追問建議 + 前端點擊自動填入 | P2 | ✅ |
| T7-9 | 行動版響應式：漢堡選單 + 側邊欄覆蓋層 + 觸控友善 UI | P2 | ✅ |
| T7-11 | 對話匯出：Markdown 格式匯出，含時間戳、來源、評分 | P2 | ✅ |
| T7-12 | RAG 儀表板：對話量、延遲 P50/P95、回饋統計、每日趨勢圖表（Recharts） | P1 | ✅ |
| T7-13 | 對話搜尋：關鍵字檢索歷史對話，顯示摘要與時間 | P2 | ✅ |
| T7-14 | 打字指示器：AI 思考中的動畫效果 | P3 | ✅ |
| T7-X | 來源資料結構修復：backend 與 frontend ChatSource 型別對齊（policy/law + title/snippet） | P0 | ✅ |
| T7-Y | 搜尋欄位修復：search API 返回 snippet 欄位而非 content | P0 | ✅ |
| T7-Z | SSE 錯誤處理修復：錯誤事件觸發時中止訊息提交，避免空白對話 | P0 | ✅ |

### Phase 6 任務清單（AI 引擎升級 — 7/7 完成）

| 項目 | 說明 | 優先級 | 狀態 |
|------|------|--------|------|
| AI-1 | LlamaParse 整合：10 種格式智慧解析 + 品質降級機制 | P0 | ✅ |
| AI-2 | PPT/PPTX 解析支援（LlamaParse + python-pptx 降級） | P0 | ✅ |
| AI-3 | URL 網頁內容擷取（trafilatura） | P1 | ✅ |
| AI-4 | jieba 中文詞級分詞（取代逐字切分） | P0 | ✅ |
| AI-5 | HyDE 查詢擴展（僅語意/混合模式，不影響 BM25） | P1 | ✅ |
| AI-6 | LLM 答案生成（OpenAI GPT-4o-mini + Fallback 模板） | P0 | ✅ |
| AI-7 | Per-document Chunk 去重（SHA256 雜湊） | P2 | ✅ |

### Phase 5 任務清單（UX 流程全角色檢視 — 11/11 完成）

| 項目 | 說明 | 優先級 | 狀態 |
|------|------|--------|------|
| UX-1 | `CustomDomainsPage` — 自訂域名 CRUD + DNS 驗證引導 | P0 | ✅ |
| UX-2 | `RegionsPage` — 區域資訊 + 資料駐留合規顯示 | P0 | ✅ |
| UX-3 | `RoleGuard` 前端路由角色守衛，保護所有管理頁面 | P1 | ✅ |
| UX-4 | `MyUsagePage` — 所有角色個人用量統計 | P2 | ✅ |
| UX-5 | SSO 登入改 Email 自動識別 + 後端 discover 端點 | P2 | ✅ |
| UX-6 | 文件頁面新增部門篩選功能（前端 + 後端） | P2 | ✅ |
| UX-7 | 品牌設定新增即時側邊欄預覽 | P3 | ✅ |
| UX-8 | 訂閱升級改用 Modal 確認（方案對比 / 價格 / 功能差異） | P3 | ✅ |
| UX-9 | 後端權限統一為 DI — 19 端點改用 `Depends(require_admin)` | P3 | ✅ |
| UX-10 | 部門管理改為樹狀層級結構（可收合 + parent_id 選擇） | P3 | ✅ |
| UX-11 | UX 流程檢視報告文件（`docs/UX_FLOW_REVIEW.md`） | — | ✅ |

> 完整報告含 Mermaid 流程圖、角色可見性矩陣、問題盤點，請參閱 [docs/UX_FLOW_REVIEW.md](docs/UX_FLOW_REVIEW.md)。

### Phase 4 任務清單（22/22 完成）

| 任務 | 說明 | 狀態 |
|------|------|------|
| T4-1 | Docker 生產部署 + 環境分離 | ✅ |
| T4-2 | CI/CD Pipeline（GitHub Actions） | ✅ |
| T4-3 | 白標品牌系統（Logo / 色彩 / 名稱） | ✅ |
| T4-4 | Admin 前後台分離（獨立微服務） | ✅ |
| T4-5 | Admin 前端 SPA | ✅ |
| T4-6 | 自訂網域（CNAME 驗證） | ✅ |
| T4-7 | 訂閱方案管理 | ✅ |
| T4-8 | 安全稽核強化 | ✅ |
| T4-9 | 效能優化（連線池 + 快取） | ✅ |
| T4-10 | Nginx 反向代理閘道 | ✅ |
| T4-11 | 監控與告警（Prometheus + Grafana） | ✅ |
| T4-12 | 負載測試（Locust + k6） | ✅ |
| T4-13 | 文件撰寫（使用者手冊 + API 指南 + 維運 SOP） | ✅ |
| T4-14 | API 開發者整合指南 | ✅ |
| T4-15 | 資料庫索引優化 | ✅ |
| T4-18 | Celery 任務監控 | ✅ |
| T4-19 | 多區域部署架構 | ✅ |
| T4-20 | PostgreSQL 效能調優 | ✅ |
| T4-21 | Nginx 進階安全 Headers | ✅ |
| T4-22 | 多環境部署設定 | ✅ |

詳細任務清單與產品規格請參閱 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)。

---

## 文件索引

| 文件 | 說明 |
|------|------|
| [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | 完整產品規格書與開發計畫 |
| [docs/API_GUIDE.md](docs/API_GUIDE.md) | API 使用指南 |
| [docs/API_DEVELOPER_GUIDE.md](docs/API_DEVELOPER_GUIDE.md) | API 開發者整合指南（含 SDK 範例） |
| [docs/USER_MANUAL.md](docs/USER_MANUAL.md) | 使用者操作手冊 |
| [docs/OPS_SOP.md](docs/OPS_SOP.md) | 維運標準作業程序（SOP） |
| [docs/MULTI_REGION.md](docs/MULTI_REGION.md) | 多區域部署指南 |
| [docs/UX_FLOW_REVIEW.md](docs/UX_FLOW_REVIEW.md) | UX 流程全角色檢視報告（含 Mermaid 圖表） |
| [docs/PHASE7_UPGRADE_PROPOSAL.md](docs/PHASE7_UPGRADE_PROPOSAL.md) | Phase 7 升級提案（對話體驗升級） |
| [docs/RLS_ROLLOUT_PLAN.md](docs/RLS_ROLLOUT_PLAN.md) | Row-Level Security 分階段啟用計畫 |
| [docs/TENANT_ISOLATION_RISK_AUDIT.md](docs/TENANT_ISOLATION_RISK_AUDIT.md) | 租戶隔離風險稽核報告 |
| [docs/QUALITY_PERFORMANCE_REPORT.md](docs/QUALITY_PERFORMANCE_REPORT.md) | 品質效能評測報告 |
| [tests/load/README.md](tests/load/README.md) | 負載測試說明 |

---

## 授權

本專案為私有專案，未經授權不得複製或分發。
