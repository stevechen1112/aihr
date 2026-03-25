# UniHR SaaS — 前端

React 19 + TypeScript + Vite 建構的企業級多租戶 HR 管理前端。

## 技術棧

- **React 19.2** + **TypeScript 5.9**
- **Vite 7.2**（開發/建置工具）
- **TailwindCSS 4.1**（樣式）
- **React Router 7.6**（路由）
- **Recharts 2.15**（圖表）

## 開發

```bash
npm install
npm run dev        # 啟動開發伺服器 (http://localhost:3001)
npm run build      # 建置生產版本
npm run preview    # 預覽建置結果
```

## 路由架構

- 公開網站以 `/` 為主入口，承載品牌首頁、價格、FAQ、聯絡資訊、登入與註冊。
- 產品工作台統一放在 `/app/*`，所有需要登入的頁面都經過 `ProtectedRoute`。
- 舊版受保護路徑如 `/usage`、`/documents` 仍會轉址到 `/app/...`，再依登入狀態導向 `/login` 或實際頁面。

## E2E

```bash
npm run test:e2e
```

```bash
npm run test:e2e:public
```

```powershell
$env:E2E_BASE_URL="http://172.233.67.81"
npm run test:e2e -- auth.spec.ts
```

```powershell
$env:E2E_BASE_URL="http://172.233.67.81"
$env:E2E_USER_EMAIL="owner@aihr.app"
$env:E2E_USER_PASSWORD="Owner123!"
npm run test:e2e -- app.spec.ts
```

## 表面穩健性驗證

先建置前端，再用單一腳本檢查公開頁面、重導、未登入保護路由與 entry bundle 是否一致。

```bash
npm run build
npm run verify:surface -- --base-url http://127.0.0.1:4173 --dist-dir dist
```

```powershell
$env:FRONTEND_VERIFY_BASE_URL="http://172.233.67.81"
npm run verify:surface -- --dist-dir dist
```

如果 live 載入的 `index-*.js` / `index-*.css` 與本地 `dist/assets` 不一致，通常代表部署鏈路仍在送舊 bundle，而不是 React 程式碼本身失效。

## 頁面結構

| 路由 | 頁面 | 說明 |
|------|------|------|
| `/` | LandingPage | 公開首頁，含功能介紹、FAQ、聯絡資訊 |
| `/pricing` | PricingPage | 公開方案與價格 |
| `/login` | LoginPage | 登入 + SSO，自動銜接公開站導覽與 footer |
| `/signup` | SignupPage | 新租戶註冊頁，沿用公開站殼層 |
| `/privacy` | PrivacyPage | 隱私權政策 |
| `/terms` | TermsPage | 服務條款 |
| `/verify-email` | VerifyEmailPage | Email 驗證完成頁 |
| `/login/callback` | SSOCallbackPage | OAuth 2.0 回調處理 |
| `/accept-invite` | AcceptInvitePage | 邀請連結加入組織 |
| `/app` | ChatPage | 受保護工作台首頁，預設進入 AI 問答 |
| `/app/documents` | DocumentsPage | 文件管理 |
| `/app/my-usage` | MyUsagePage | 個人用量 |
| `/app/usage` | UsagePage | 租戶用量追蹤 |
| `/app/audit` | AuditLogsPage | 稽核紀錄 |
| `/app/departments` | DepartmentsPage | 部門管理 |
| `/app/company` | CompanyPage | 公司設定 |
| `/app/sso-settings` | SSOSettingsPage | SSO 設定 |
| `/app/branding` | BrandingPage | 品牌設定 |
| `/app/subscription` | SubscriptionPage | 訂閱方案 |
| `/app/custom-domains` | CustomDomainsPage | 自訂域名 |
| `/app/rag-dashboard` | RAGDashboardPage | RAG 儀表板 |
| `/app/quality-dashboard` | QualityDashboardPage | 品質儀表板 |
| `/app/regions` | RegionsPage | 區域資訊 |
| `/usage`, `/documents`, ... | Legacy redirects | 舊路由自動轉址到 `/app/*` |
