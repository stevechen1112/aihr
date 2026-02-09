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
- [目錄結構](#目錄結構)
- [開發計畫](#開發計畫)
- [授權](#授權)

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
| 容器化 | Docker + Docker Compose（5 容器：web / frontend / db / redis / worker） |
| 部署 | 支援 Development / Staging / Production 三環境 |
| API 版本管理 | v1 (穩定) + v2 (新功能)，含 Deprecation Header |

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

| 容器 | 說明 | Port |
|------|------|------|
| `web` | FastAPI 後端（Gunicorn + Uvicorn workers） | 8000 |
| `db` | PostgreSQL 15（含調優設定） | 5432 |
| `redis` | Redis 7（含持久化） | 6379 |
| `worker` | Celery 背景任務 Worker | — |
| `frontend` | React SPA（Nginx 靜態服務） | 80 |
| `admin-api` | Admin 微服務 | 8001 |
| `admin-frontend` | Admin 前端 SPA | 80 |
| `admin-redis` | Admin 獨立 Redis | 6380 |
| `nginx` | 反向代理閘道（多域名路由） | 80/443 |
| `prometheus` | 監控指標收集 | 9090 |
| `grafana` | 監控儀錶板 | 3000 |
| `alertmanager` | 告警推送 | 9093 |

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

- **Prometheus**：每 15 秒抓取 `/metrics` 端點
- **Grafana**：預配置資料來源與儀錶板（自動 provisioning）
- **Alertmanager**：自訂告警規則（CPU、記憶體、回應時間、錯誤率）

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
# 編輯 .env 填入 API keys（OPENAI / VOYAGE）

# 2. 啟動所有服務
make dev

# 3. 初始化資料庫
make migrate

# 4. 建立預設管理員帳號
docker-compose exec web python scripts/create_tables.py
docker-compose exec web python scripts/initial_data.py
```

啟動後：
- **後端 API**：http://localhost:8000
- **API 文件**：http://localhost:8000/docs
- **前端介面**：http://localhost:3001
- **Admin API**：http://localhost:8001
- **Admin 文件**：http://localhost:8001/docs

### 生產環境啟動

```bash
# 1. 複製生產用環境變數
cp .env.production.example .env

# 2. 啟動生產環境（12 容器）
make prod

# 3. 執行資料庫遷移
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head
```

生產環境入口：
- **前台**：https://app.unihr.com
- **後台**：https://admin.unihr.com
- **監控**：https://grafana.unihr.com

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

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `SECRET_KEY` | JWT 簽名密鑰 | ✅ | — |
| `OPENAI_API_KEY` | OpenAI API Key | ✅ | — |
| `OPENAI_MODEL` | OpenAI 模型名稱 | — | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | LLM 生成溫度 | — | `0.3` |
| `OPENAI_MAX_TOKENS` | LLM 最大輸出 Token | — | `1500` |
| `VOYAGE_API_KEY` | Voyage AI（Embedding + Rerank） | ✅ | — |
| `LLAMAPARSE_API_KEY` | LlamaParse 文件解析 API Key | — | — |
| `LLAMAPARSE_ENABLED` | 啟用 LlamaParse 解析 | — | `true` |
| `EMBEDDING_DIMENSION` | 向量維度 | — | `1024` |
| `POSTGRES_SERVER` | PostgreSQL 主機 | — | `localhost` |
| `POSTGRES_USER` | 資料庫使用者 | — | `postgres` |
| `POSTGRES_PASSWORD` | 資料庫密碼 | — | `postgres` |
| `POSTGRES_DB` | 資料庫名稱 | — | `unihr_saas` |
| `REDIS_HOST` | Redis 主機 | — | `localhost` |
| `CORE_API_URL` | Core 勞動法 API 位址 | — | `http://localhost:5000` |
| `GOOGLE_CLIENT_ID` | Google SSO | — | — |
| `MICROSOFT_CLIENT_ID` | Microsoft SSO | — | — |
| `RETRIEVAL_MODE` | 檢索模式 | — | `hybrid` |
| `RETRIEVAL_RERANK` | 啟用重排序 | — | `true` |
| `ADMIN_SERVICE_TOKEN` | Admin 微服務 Token | ✅（生產） | — |
| `ADMIN_REDIS_PASSWORD` | Admin Redis 密碼 | ✅（生產） | — |
| `DEPLOY_REGION` | 部署區域代碼 | — | `ap` |
| `GRAFANA_ADMIN_PASSWORD` | Grafana 管理員密碼 | — | `admin` |

完整列表參見 [.env.example](.env.example)、[.env.production.example](.env.production.example)。

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

# === 部署 ===
make staging            # 啟動 Staging 環境
make prod               # 啟動 Production 環境（12 容器）
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
| `tests/load/locustfile.py` | HTTP 負載測試 | — |
| `tests/load/k6_load_test.js` | k6 效能測試 | — |

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
│       └── t7_5_feedback.py       # ★ Phase 7: chat_feedbacks 表（評分+分類+意見）
├── scripts/                       # 工具腳本
│   ├── create_tables.py           #   資料表建立
│   ├── create_test_users.py       #   測試帳號建立
│   └── initial_data.py            #   初始化資料
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
│   └── PHASE7_UPGRADE_PROPOSAL.md # ★ Phase 7 升級提案（對話體驗升級）
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
| [tests/load/README.md](tests/load/README.md) | 負載測試說明 |

---

## 授權

本專案為私有專案，未經授權不得複製或分發。
