# UniHR — 商業化缺口分析報告

> **文件版本**：v1.0 | **建立日期**：2026-03-06  
> **依據**：代碼實際掃描（187 個源碼檔案，24,277 行）+ 測試驗證結果（98.3%）

---

## 1. 前言：真實現況定位

本系統並非空殼 Demo，核心技術已達工程品質：

| 指標 | 數字 |
|------|------|
| 源碼規模 | 187 個檔案 / 24,277 行 |
| 核心服務行數 | `document_parser.py` 1,476 行、`chat_orchestrator.py` 1,056 行 |
| 最新測試通過率 | 169/172（98.3%） |
| 已實作端點 | 16 個 API 模組 / 50+ 端點 |
| 已實作前端頁面 | 15 個頁面（租戶端）+ 4 個（後台） |

**結論**：這是一個**功能完整的技術原型（Technical Prototype）**，距離可收費商業產品（Commercial Product）還有明確的缺口，集中在「商業變現基礎設施」與「維運可靠性」兩個面向。

---

## 2. 已完成 vs 缺失 — 快速對照表

| 功能域 | 目前狀態 | 商業化是否就緒 |
|--------|----------|---------------|
| AI 問答（RAG + SSE） | ✅ 實作完整，測試通過 | ✅ 就緒 |
| 多格式文件解析（23 種） | ✅ 實作完整，帶品質報告 | ✅ 就緒 |
| 多租戶資料隔離 | ✅ tenant_id + RLS 雙層 | ✅ 就緒 |
| 帳號認證（JWT + 五級角色） | ✅ 實作完整 | ✅ 就緒 |
| SSO（Google / Microsoft） | ✅ 真實 OAuth token exchange | ⚠️ 需填入生產 Client ID |
| 速率限制 + 稽核日誌 | ✅ 不可竄改稽核已完成 | ✅ 就緒 |
| 自訂域名（DNS TXT 驗證） | ✅ 真實 `dns.resolver` 驗證 | ⚠️ 缺 SSL 自動申請（Let's Encrypt） |
| 訂閱方案 / 升級 | ⚠️ UI + 方案矩陣完整，無收費 | ❌ 缺支付閘道（Stripe） |
| Email 通知 | ❌ 全無 SMTP / SendGrid 實作 | ❌ 缺 |
| 多區域部署 | ⚠️ 架構設計完整，實際單節點 | ❌ 缺真實基礎設施 |
| CI/CD | ✅ GitHub Actions 三條 pipeline | ⚠️ Deploy workflow 需配置 SSH secret |
| 監控告警 | ✅ 16 條規則配置完整 | ⚠️ 需接 Alertmanager → Slack/Email |
| GDPR / 個資法合規 | ⚠️ 架構支援，無法律文件 | ❌ 缺隱私權政策、條款、DPA |
| 客戶支援入口 | ❌ 不存在 | ❌ 缺 |

---

## 3. 缺口詳細說明

### 🔴 P0 — 商業化必需，目前完全缺失

#### 3.1 支付閘道（最關鍵缺口）

**現況**：`subscription.py` 有完整的方案矩陣（Free / Starter / Professional / Enterprise）、方案功能比對、`PLAN_MATRIX` 定義，以及 `/change-plan` 端點——但端點內部只更新 `tenants` 表的 `plan` 欄位，沒有任何真實收費動作。

```python
# 現況：upgrade 端點只做資料庫寫入
tenant.plan = new_plan  # 直接改，沒有 Stripe 確認
db.commit()
```

**需要補齊**：
- Stripe（或 TapPay / 藍新，台灣市場）客戶端整合
- Webhook 處理（`invoice.payment_succeeded`、`customer.subscription.deleted`）
- 信用卡輸入 UI（Stripe Elements 或 redirect to Stripe Checkout）
- 訂閱狀態同步（付款失敗 → 降級 → 通知）
- 發票 / 收據自動寄送

**工程估算**：2-3 週（含測試）

---

#### 3.2 Email 通知系統

**現況**：代碼庫中完全找不到 `smtp`、`sendgrid`、`smtplib`、`send_mail` 任何字串。系統無法寄任何電子郵件。

**需要補齊**的場景：
| 場景 | 重要性 |
|------|--------|
| 使用者註冊歡迎信 / Email 驗證 | 必須 |
| 密碼重設連結 | 必須 |
| 訂閱確認 / 帳單通知 | 必須 |
| 配額即將超額告警 | 重要 |
| 系統維護通知 | 重要 |
| 使用者邀請（Email 含邀請連結） | 重要 |

**建議技術選型**：
- 交易型郵件：SendGrid / AWS SES / Resend
- 模板引擎：Jinja2（已在依賴中）
- 佇列化：透過現有 Celery 發送，避免 API 阻塞

**工程估算**：1-1.5 週

---

#### 3.3 法律與合規文件

**現況**：系統完全沒有任何法律文件，但系統處理員工個人資料（姓名、薪資、健康資訊）。

**必須備齊**：
- **隱私權政策**（Privacy Policy）— 符合個人資料保護法（個資法）要求
- **服務條款**（Terms of Service）— 明定使用者與平台責任
- **資料處理協議**（DPA, Data Processing Agreement）— 企業客戶簽署
- **Cookie 政策**（若前端落地頁有追蹤）
- **資料刪除申請流程** — 使用者帳號刪除 + 向量資料清除 + 稽核保留

> ⚠️ 若系統處理的是歐盟使用者資料（已有 GDPR 區域 `eu` 的架構），DPA 是法律義務，不是選項。

**估算**：法律顧問 + 工程實作 2-4 週

---

### 🟡 P1 — 可上線但需盡快補足

#### 3.4 密碼重設流程

**現況**：沒有 `/auth/forgot-password`、`/auth/reset-password` 端點，前端也沒有對應頁面。使用者忘記密碼只能靠管理員介入（資料庫直接修改）。

**工程估算**：3-5 天

---

#### 3.5 SSL 自動申請（自訂域名完整性）

**現況**：自訂域名的 DNS TXT 驗證已實作（使用 `dns.resolver`），但 `ssl_provisioned` 欄位永遠為 `false`。沒有整合 Let's Encrypt / Certbot 或 Nginx 動態憑證。

```python
# custom_domains.py：ssl_provisioned 從未被設為 True
ssl_provisioned: bool = False  # 永遠 false
```

**需要補齊**：
- 驗證通過後自動觸發 Certbot / ACME 憑證申請
- Nginx 動態配置更新（重載不停機）
- 憑證到期自動更新

**工程估算**：1-2 週

---

#### 3.6 使用者邀請流程

**現況**：管理員可在後台新增帳號，但沒有「邀請 Email」功能。新使用者需要管理員告知帳密。

**需要補齊**：
- 邀請 Email 含一次性 Token 連結
- 首次登入設定密碼頁面
- 邀請連結有效期（建議 72 小時）

**工程估算**：3-5 天（依賴 Email 系統建好）

---

#### 3.7 監控告警通知渠道

**現況**：`alert_rules.yml` 有 16 條完整告警規則，但 `prometheus.yml` 沒有配置 Alertmanager，告警觸發後只在 Grafana UI 顯示，不會主動通知任何人。

**需要補齊**：
```yaml
# prometheus.yml 需加入
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```
- Alertmanager 容器加入 `docker-compose.prod.yml`
- Slack webhook 或 Email 告警路由設定
- On-call 輪班設定（PagerDuty / OpsGenie，進階）

**工程估算**：2-3 天

---

#### 3.8 CI/CD 部署 Secret 配置

**現況**：`.github/workflows/deploy-production.yml` 存在，但 GitHub Repository Secrets 需要手動配置（`SSH_PRIVATE_KEY`、`DEPLOY_HOST`、`ENV_PRODUCTION_B64` 等），目前 workflow 未驗證能否真正觸發遠端部署。

**需要補齊**：
- 在 GitHub Repo → Settings → Secrets 設定所有必要 secret
- 跑一次完整的 staging → production 部署流程驗證
- 加入 Rollback 機制（版本標籤 + 快速回滾命令）

**工程估算**：1 天設定 + 1 天驗證

---

### 🟢 P2 — 商業成熟度提升

#### 3.9 多區域真實基礎設施

**現況**：`region.py` 有完整的 `RegionConfig` 資料結構（含 `db_host`、`redis_host`、`api_endpoint` 等欄位），但所有值都指向預設的 `db`、`redis`（Docker 內部 DNS），實際上只有一台節點。

**若要真正支援多區域**：
- 為每個區域（ap/us/eu/jp）開通獨立 VPS + DB + Redis
- 設定跨區域路由邏輯（依租戶 `region` 欄位路由請求）
- 資料駐留驗證（確認資料不跨區）

**工程 + 基礎設施估算**：4-6 週 + 月費 ~$200-500/區域

---

#### 3.10 客戶支援與 Onboarding

**現況**：完全沒有。

**建議最小可行方案**：
- 嵌入式客服（Crisp / Intercom 免費方案）— 1 天
- 說明文件站（GitBook / Notion Public）— 3 天
- Onboarding Checklist（前端引導流程）— 1 週

---

#### 3.11 使用量帳單明細

**現況**：`/usage` 頁面有視覺化圖表，但沒有可下載的帳單明細（PDF 發票格式）。企業採購通常要求正式發票。

**需要補齊**：
- 每月帳單 PDF 生成（`reportlab` 或 `weasyprint`）
- 帳單歷史頁面
- 公司抬頭 / 統一編號填寫

**工程估算**：3-5 天

---

#### 3.12 效能基準測試驗證

**現況**：`tests/test_load.py`（Locust）腳本已建立，但尚未在真實負載下執行並記錄結果。README 列出的效能指標無實測數據支撐。

**執行步驟**：
```bash
locust -f tests/test_load.py --host http://localhost:8002 \
  --headless -u 50 -r 5 -t 300s \
  --html test-data/test-results/load_report.html
```

---

## 4. 缺口優先級與工程時程估算

```
優先級  工作項目                    工程工時     依賴
P0-1   支付閘道（Stripe）           2-3 週       —
P0-2   Email 通知系統               1-1.5 週     —
P0-3   隱私權政策 + 服務條款        2-4 週       法務
P1-4   密碼重設流程                 3-5 天       Email
P1-5   SSL 自動申請                 1-2 週       —
P1-6   使用者邀請流程               3-5 天       Email
P1-7   Alertmanager 告警通知        2-3 天       —
P1-8   CI/CD Secret + 驗證部署     1-2 天       —
P2-9   多區域真實基礎設施           4-6 週       預算
P2-10  客戶支援 / Onboarding        1 週         —
P2-11  帳單明細 PDF                 3-5 天       —
P2-12  負載測試實測                 1 天         —
```

**最快可收費 MVP 時程**（完成 P0 + P1）：
- 樂觀估算：6-8 週（2 位工程師）
- 保守估算：10-12 週（1 位工程師）

---

## 5. 技術債與風險清單

| 項目 | 風險程度 | 說明 |
|------|----------|------|
| SSO Client ID 為空 | 🔴 高 | Google/Microsoft SSO 未填入真實 Client ID，無法測試 |
| LlamaParse 免費額度 | 🟡 中 | 每月 1,000 頁免費，商業使用需付費計畫（$3/千頁） |
| Voyage AI 免費額度 | 🟡 中 | 前 100M tokens 免費，商業使用需升級 |
| OpenAI 費用控制 | 🟡 中 | 未設定 API 用量上限，高流量時費用不可控 |
| RLS 未完全啟用 | 🟡 中 | `RLS_ENFORCEMENT_ENABLED=False`，目前仍靠應用層隔離 |
| 上傳檔案無病毒掃描 | 🟡 中 | 允許任何格式上傳，未整合 ClamAV |
| 管理員帳號無 2FA | 🟡 中 | Superadmin 帳號僅密碼保護 |
| 向量資料無加密靜態 | 🟠 中低 | PostgreSQL 資料落地未加密 |
| Docker image 非固定版本 | 🟢 低 | `FROM python:3.13-slim`（非 `3.13.1-slim`），可能因上游更新破版 |

---

## 6. 各目標市場可交付現況

### 🎯 目標 A：單一租戶自架（Internal Tool）
**現況即可交付** — 一家公司自己用，把 HR 文件上傳進去，開放員工問答。

所需額外工作：僅需配置 `.env.production`（30 分鐘）

---

### 🎯 目標 B：POC / 付費試用（Pilot 客戶，1-3 家）
**2-3 週後可交付** — 補上 Email 通知 + 密碼重設 + Alertmanager，就能服務少量付費客戶（手動開票）。

---

### 🎯 目標 C：自助訂閱 SaaS（Self-serve，目標月費 NT$2,000-10,000/租戶）
**6-10 週後可交付** — 需支付閘道 + Email + 法律文件 + SSL 自動申請。

---

### 🎯 目標 D：企業級合規銷售（Enterprise，年約百萬台幣+）
**3-6 個月後可交付** — 需 GDPR DPA、SOC 2 評估、2FA、多區域真實部署、SLA 保證、企業帳單流程。

---

## 7. 建議下一步行動

依「最快產生商業價值」排序：

```
Week 1-2  ▸ Email 系統（SendGrid）
           ▸ 密碼重設流程
           ▸ Alertmanager 告警通知
           ▸ 負載測試實測並記錄結果

Week 3-5  ▸ Stripe 支付整合（或手動開票 + Stripe Payment Link 權宜方案）
           ▸ 法律文件起草（請法務協助，工程設定隱私頁 + 條款頁）
           ▸ CI/CD Secret 配置 + 完整部署驗證

Week 6-8  ▸ SSL 自訂域名自動申請
           ▸ 使用者邀請流程
           ▸ 客戶支援嵌入 + Onboarding 引導

Month 3+  ▸ 多區域真實基礎設施（視業務需求）
           ▸ SOC 2 / ISO 27001 評估（視企業客戶要求）
           ▸ 2FA（TOTP / WebAuthn）
```

---

*本文件依代碼實際掃描撰寫，所有「缺失」的判斷均基於源碼確認，非推測。*
