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

## 頁面結構

| 路由 | 頁面 | 說明 |
|------|------|------|
| `/login` | LoginPage | 登入 + SSO |
| `/` | DashboardPage | 儀表板總覽 |
| `/chat` | ChatPage | AI 問答介面 |
| `/knowledge-base` | KnowledgeBasePage | 知識庫管理 |
| `/documents` | DocumentsPage | 文件管理 |
| `/users` | UsersPage | 使用者管理 |
| `/company` | CompanyPage | 公司設定 |
| `/admin` | AdminPage | 超管面板 |
| `/analytics` | AnalyticsPage | 分析報表 |
| `/audit-logs` | AuditLogsPage | 稽核紀錄 |
| `/departments` | DepartmentsPage | 部門管理 |
| `/usage` | UsagePage | 用量追蹤 |
