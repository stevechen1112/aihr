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
- 每家公司擁有獨立的空間、資料庫記錄與向量索引（Pinecone per-tenant namespace）
- Row-Level Security + 中間層隔離，確保企業間資料零交叉
- 租戶配額管理（儲存空間、文件數量、每月查詢次數、Token 用量上限）

### 帳號與權限
- 五級角色：`superadmin` → `owner` → `admin` → `employee` → `viewer`
- JWT 認證 + SSO（Google / Microsoft OAuth 2.0）
- 三層速率限制（IP / 使用者 / 租戶）

### 企業知識庫
- 文件上傳 → 解析 → 切片 → 向量化 → 存入 Pinecone，全流程背景處理（Celery）
- 支援 **19 種檔案格式**（詳見[文件處理引擎](#文件處理引擎)）
- 品質報告系統：每份文件自動評估解析品質（excellent / good / fair / poor / failed）

### AI 問答（Orchestrator）
- 混合檢索：語意搜尋 + BM25 關鍵字 + RRF 融合 + Voyage Rerank
- 同時查詢公司知識庫與 Core 勞動法，合併回答並標註來源
- 對話歷史保存，支援多輪追問

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
│  │  │Semantic+BM25 │  │ 19 Formats   │  │Enforcement│  │    │
│  │  │ +RRF+Rerank  │  │ +OCR+Tables  │  │ +Alerts   │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └───────────┘  │    │
│  └─────────│─────────────────│─────────────────────────┘    │
└────────────│─────────────────│──────────────────────────────┘
             │                 │
     ┌───────▼───────┐  ┌─────▼──────┐
     │   Pinecone    │  │   Celery   │
     │  Vector DB    │  │   Worker   │
     │(per-tenant)   │  │ (bg tasks) │
     └───────────────┘  └─────┬──────┘
                              │
┌─────────────┐  ┌────────────▼──┐  ┌────────────┐
│ PostgreSQL  │  │    Redis      │  │ Voyage AI  │
│   15        │  │ 7 (queue+     │  │ Embedding  │
│ (primary DB)│  │    cache)     │  │ + Rerank   │
└─────────────┘  └───────────────┘  └────────────┘
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
| 向量資料庫 | Pinecone | 3.1.0 |
| Embedding 模型 | Voyage AI (`voyage-law-2`, 1024 維) | 0.2.1 |
| LLM | OpenAI GPT | 1.12.0 |
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

### 基礎設施

| 類別 | 技術 |
|------|------|
| 容器化 | Docker + Docker Compose（5 容器：web / frontend / db / redis / worker） |
| 部署 | 支援 Development / Staging / Production 三環境 |
| API 版本管理 | v1 (穩定) + v2 (新功能)，含 Deprecation Header |

---

## 文件處理引擎

自建多格式解析引擎（**非** LlamaIndex / LangChain），直接調用底層解析庫，精簡可控。

### 支援格式（19 種）

| 階段 | 格式 | 解析庫 | 特殊能力 |
|------|------|--------|----------|
| Phase 0 | PDF（文字型） | `pypdf` | 基礎文字提取 |
| Phase 0 | DOCX | `python-docx` | 標題層級 + 表格提取 |
| Phase 0 | DOC | `antiword` / `LibreOffice` | 舊格式降級處理 |
| Phase 0 | TXT | stdlib + `chardet` | 6 種編碼自動偵測 + BOM 清除 |
| Phase 1 | PDF（掃描型） | `pytesseract` + `pdf2image` | 中英文 OCR |
| Phase 1 | PDF（表格） | `pdfplumber` | 結構化表格提取 |
| Phase 1 | Excel（.xlsx/.xls） | `openpyxl` | 多工作表解析 |
| Phase 1 | CSV | stdlib | 自動分隔符號偵測 |
| Phase 1 | HTML | `BeautifulSoup` + `lxml` | script/style/nav 清除、XSS 防護 |
| Phase 1 | Markdown | stdlib | 標題結構保留 |
| Phase 2 | RTF | `striprtf` | RTF 控制碼清除 |
| Phase 2 | JSON | stdlib | 結構化資料 → 可讀文字 |
| Phase 2 | 圖片（JPG/PNG/TIFF/BMP） | `pytesseract` + `Pillow` | OCR + 辨識信心度 |

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
| `semantic` | Pinecone 向量餘弦相似度 | 語意理解、概念匹配 |
| `keyword` | BM25Okapi 關鍵字匹配 | 精確詞彙、編號、法條查詢 |
| `hybrid`（預設） | 語意 + BM25 + RRF 融合 | 通用場景，兼顧語意與關鍵字 |

### 管線流程

```
查詢 → ┬─ 語意檢索 (Pinecone + Voyage Embedding)
       └─ BM25 關鍵字檢索 (PostgreSQL chunks)
              ↓
       RRF 融合排序 (score = Σ 1/(k + rank), k=60)
              ↓
       Voyage Rerank-2 重排序
              ↓
       相似度閾值過濾
              ↓
       結果（含 content / score / source / metadata）
```

### 特色

- **中英文混合分詞器**：中文逐字切分 + 英文按空格分詞，支援 `NT$850,000` 等格式
- **Voyage Rerank**：使用 `rerank-2` 模型對候選結果重新排序
- **Redis 查詢快取**：SHA256 cache key，5 分鐘 TTL，文件變更時自動失效
- **批次搜尋**：`batch_search()` 支援多查詢並行
- **Graceful Degradation**：Redis / BM25 不可用時自動降級

---

## 多租戶隔離

| 層級 | 隔離方式 |
|------|----------|
| 資料庫 | 所有表含 `tenant_id`，JOIN/WHERE 強制過濾 |
| 向量資料庫 | Pinecone 每租戶獨立 index（`tenant-{id}-kb`） |
| 檔案儲存 | 上傳目錄以 `tenant_id` 分隔 |
| API | 中間層從 JWT token 提取 `tenant_id`，注入所有查詢 |
| 快取 | Redis cache key 包含 `tenant_id`，不可跨租戶讀取 |

---

## 前端頁面

| 頁面 | 路徑 | 說明 |
|------|------|------|
| 登入 | `/login` | JWT 登入 + Google / Microsoft SSO |
| SSO 回調 | `/login/callback` | OAuth 2.0 回調處理 |
| AI 問答 | `/chat` | 對話式介面，即時串流回答 |
| 知識庫管理 | `/documents` | 拖放上傳、狀態追蹤、格式偵測 |
| 公司設定 | `/company` | 租戶基本資訊、SSO 設定 |
| 部門管理 | `/departments` | 部門 CRUD |
| 員工管理 | `/admin` | 使用者帳號管理、角色指派 |
| 用量統計 | `/usage` | Token / 查詢 / 儲存用量圖表 |
| 配額管理 | `/admin/quota` | 租戶配額設定與告警（超級管理員） |
| 分析儀表板 | `/analytics` | 使用趨勢、熱門問題、部門統計 |
| 稽核日誌 | `/audit` | 操作紀錄查詢、篩選、匯出 |
| SSO 設定 | `/admin/sso` | Google / Microsoft OAuth 設定 |

---

## API 端點

### v1 API（`/api/v1`）

| 模組 | 路由 | 功能 |
|------|------|------|
| Auth | `/auth/login`, `/auth/register` | JWT 登入 / 註冊 |
| SSO | `/sso/google`, `/sso/microsoft` | OAuth 2.0 SSO |
| Chat | `/chat/send`, `/chat/history` | AI 問答與歷史 |
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

---

## 快速開始

### 前置需求

- Docker & Docker Compose
- Node.js 18+（前端開發用）
- Python 3.11+（後端開發用）

### 一鍵啟動（Docker）

```bash
# 1. 複製環境變數
cp .env.example .env
# 編輯 .env 填入 API keys（OPENAI / VOYAGE / PINECONE）

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
```

---

## 環境變數

| 變數 | 說明 | 必填 | 預設 |
|------|------|------|------|
| `SECRET_KEY` | JWT 簽名密鑰 | ✅ | — |
| `OPENAI_API_KEY` | OpenAI API Key | ✅ | — |
| `VOYAGE_API_KEY` | Voyage AI（Embedding + Rerank） | ✅ | — |
| `PINECONE_API_KEY` | Pinecone 向量資料庫 | ✅ | — |
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

完整列表參見 [.env.example](.env.example)。

---

## 常用指令

```bash
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
make staging            # 啟動 Staging 環境
make prod               # 啟動 Production 環境
```

---

## 測試

### 後端單元測試

```bash
# 執行全部測試（52 項 Phase 1-3 測試）
python -m pytest tests/ -v

# 文件引擎測試（90 項）
python tests/test_document_engine.py

# 文件引擎 Benchmark（62 項，含效能基準）
python tests/benchmark_document_engine.py
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
│   │   │   └── tenant_admin.py    #   租戶管理員
│   │   └── v2/                    # v2 API
│   ├── models/                    # SQLAlchemy 模型
│   │   ├── tenant.py              #   租戶 + 配額
│   │   ├── user.py                #   使用者
│   │   ├── document.py            #   文件 + 切片
│   │   ├── chat.py                #   對話 + 訊息
│   │   ├── audit.py               #   稽核記錄
│   │   ├── permission.py          #   權限
│   │   ├── sso_config.py          #   SSO 設定
│   │   └── feature_flag.py        #   功能開關
│   ├── schemas/                   # Pydantic Schemas
│   ├── crud/                      # 資料存取層
│   ├── services/                  # 核心業務邏輯
│   │   ├── document_parser.py     #   多格式解析引擎（~950 行）
│   │   ├── kb_retrieval.py        #   進階檢索引擎（~470 行）
│   │   ├── chat_orchestrator.py   #   問答協調器
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
├── frontend/
│   └── src/
│       ├── App.tsx                # 路由設定
│       ├── api.ts                 # API 客戶端
│       ├── auth.tsx               # 認證 Context
│       ├── types.ts               # TypeScript 型別
│       ├── components/
│       │   └── Layout.tsx         # 側邊欄導覽 Layout
│       └── pages/                 # 頁面元件（12 頁）
│           ├── LoginPage.tsx
│           ├── ChatPage.tsx
│           ├── DocumentsPage.tsx
│           ├── CompanyPage.tsx
│           ├── AdminPage.tsx
│           ├── AdminQuotaPage.tsx
│           ├── AnalyticsPage.tsx
│           ├── AuditLogsPage.tsx
│           ├── DepartmentsPage.tsx
│           ├── UsagePage.tsx
│           ├── SSOSettingsPage.tsx
│           └── SSOCallbackPage.tsx
├── tests/                         # 測試套件
├── scripts/                       # 工具腳本
│   ├── create_tables.py           #   資料表建立
│   ├── create_test_users.py       #   測試帳號建立
│   └── initial_data.py            #   初始化資料
├── docs/                          # 專案文件
│   ├── PROJECT_PLAN.md            #   完整產品規格書（1278 行）
│   ├── API_GUIDE.md               #   API 使用指南
│   ├── PHASE2_TEST_REPORT.md      #   Phase 2 測試報告
│   └── PHASE3_TEST_REPORT.md      #   Phase 3 測試報告
├── docker-compose.yml             # 開發環境（5 容器）
├── docker-compose.staging.yml     # Staging 覆蓋
├── docker-compose.production.yml  # Production 覆蓋
├── Dockerfile                     # 後端映像
├── Makefile                       # 常用指令
└── requirements.txt               # Python 依賴
```

---

## 開發計畫

| 階段 | 內容 | 狀態 |
|------|------|------|
| Phase 1 | 基礎建設：多租戶 + 認證 + 文件管線 + AI 問答 | ✅ 完成 |
| Phase 2 | 安全強化：SSO + 速率限制 + API 版本 + 功能旗標 | ✅ 完成 |
| Phase 3 | 管理功能：配額 + 分析 + 前端頁面 | ✅ 完成 |
| Phase 3+ | 文件引擎升級：19 格式 + 進階檢索 + 混合搜尋 | ✅ 完成 |
| Phase 4 | 生產部署：CI/CD + 監控 + 負載測試 | 🔜 規劃中 |

詳細任務清單與產品規格請參閱 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)。

---

## 授權

本專案為私有專案，未經授權不得複製或分發。
