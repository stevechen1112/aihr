# UniHR 多區域部署與資料合規文件（T4-19）

## 1. 概述

UniHR 支援多區域部署，確保客戶資料落地在其要求的地理區域。每個區域擁有獨立的：

- **PostgreSQL 資料庫** — 租戶資料、使用者資料、對話記錄完全隔離
- **Redis 快取** — Session、Rate Limit、暫存資料
- **Pinecone 向量索引** — 知識庫向量資料
- **Celery Worker** — 文件處理佇列

## 2. 支援區域

| 區域代碼 | 名稱 | 機房位置 | 適用法規 |
|---------|------|----------|---------|
| `ap` | 亞太區（台灣） | GCP asia-east1 (彰化) | 台灣個資法 (PDPA) |
| `us` | 美國 | GCP us-east1 (南卡羅萊納) | SOC 2 Type II |
| `eu` | 歐洲 | GCP europe-west1 (法蘭克福) | GDPR |
| `jp` | 日本 | GCP asia-northeast1 (東京) | APPI |

## 3. 資料流說明

### 3.1 不跨區域的資料
以下資料 **永遠不離開** 所屬區域：

- 租戶基本資料 (tenants)
- 使用者帳號與密碼雜湊 (users)
- 上傳文件與切片 (documents, document_chunks)
- 對話記錄與訊息 (conversations, messages)
- 稽核日誌 (audit_logs)
- 用量記錄 (usage_records)
- SSO 設定 (tenant_sso_configs)
- 向量嵌入 (Pinecone index)

### 3.2 跨區域共用的資料
以下資料為 **平台級管理**，僅存在於主控區域：

- Feature Flags（全域功能開關）
- 平台管理員帳號（Superuser）
- 訂閱方案定義

### 3.3 API 呼叫路由

```
使用者 → CDN / API Gateway
           │
           ├── 識別 Tenant Region
           │
           ├── ap: api-ap.unihr.com → AP 區域服務群
           ├── us: api-us.unihr.com → US 區域服務群
           ├── eu: api-eu.unihr.com → EU 區域服務群
           └── jp: api-jp.unihr.com → JP 區域服務群
```

若請求到達錯誤區域，系統會回傳 `421 Misdirected Request` 並指引至正確端點。

## 4. 部署架構

### 4.1 單區域部署（預設）

適用於初期或僅服務台灣客戶的場景：

```bash
docker compose -f docker-compose.prod.yml up -d
```

所有服務共用同一組基礎設施，`MULTI_REGION_ENABLED=false`。

### 4.2 多區域部署

啟用多區域後，每個區域獨立部署：

```bash
# 亞太區
REGION=ap docker compose -f docker-compose.region.yml up -d

# 美國區
REGION=us docker compose -f docker-compose.region.yml up -d

# 歐洲區
REGION=eu docker compose -f docker-compose.region.yml up -d
```

### 4.3 Admin 管理平台

Admin 管理平台為全域聚合視圖，需要連接各區域資料庫（唯讀）：

```bash
docker compose -f docker-compose.prod.yml up -d admin-api admin-frontend
```

## 5. 租戶區域遷移 SOP

當客戶要求變更資料儲存區域時：

1. **評估影響** — 確認停機時間、資料量
2. **資料匯出** — 從原區域匯出租戶所有資料
3. **更新區域** — 呼叫 `PUT /api/v1/regions/tenants/{id}/region`
4. **資料匯入** — 匯入新區域資料庫
5. **向量遷移** — 將 Pinecone 向量從原區域 index 遷移至新區域
6. **DNS 更新** — 更新自訂域名（若有）指向新區域
7. **驗證** — 確認所有功能正常運作
8. **原區域清除** — 確認無誤後刪除原區域資料

## 6. GDPR 合規措施（EU 區域）

| 要求 | 實施方式 |
|------|---------|
| 資料最小化 | 僅收集業務必要欄位 |
| 目的限制 | 資料僅用於 HR 問答服務 |
| 儲存限制 | 對話記錄可設定自動清除期限 |
| 資料可攜 | 提供完整資料匯出 API |
| 被遺忘權 | 提供租戶/使用者資料完全刪除功能 |
| 資料不出境 | EU 區域所有資料儲存在 europe-west1 |
| 加密傳輸 | 所有 API 強制 TLS 1.2+ |
| 靜態加密 | PostgreSQL 磁碟加密、Pinecone 服務端加密 |

## 7. 監控與告警

每個區域獨立的監控堆疊：
- Prometheus（區域內指標收集）
- Grafana（區域 Dashboard）

跨區域聚合：
- Admin Dashboard 可查看所有區域的概覽統計
