# UniHR Security Whitepaper

> Version 1.0 ??Last updated: 2025

## 1. Executive Summary

UniHR is a multi-tenant SaaS platform providing AI-powered HR knowledge management for Taiwan enterprises. This document describes the security architecture, data protection measures, and compliance posture of the platform.

## 2. Architecture Overview

| Layer          | Technology                                                   |
| -------------- | ------------------------------------------------------------ |
| Frontend       | React + TypeScript, served via Nginx with CSP headers        |
| API Gateway    | Nginx ??rate limiting, TLS termination, security headers     |
| Backend        | Python / FastAPI, OAuth2 Bearer JWT authentication           |
| Task Queue     | Celery + Redis (broker & result backend)                     |
| Database       | PostgreSQL 16 with Row-Level Security (RLS)                  |
| Vector Store   | Pinecone (managed) for semantic search embeddings            |
| Object Storage | Cloudflare R2 (S3-compatible, encrypted at rest)             |
| LLM            | Google Gemini (generation), Voyage AI (embeddings)           |
| Email          | SendGrid transactional email                                 |
| Monitoring     | ¦Û¬ãºÊ±±»P§iÄµ                          |
| Container      | Docker Compose (dev/staging/production)                      |

## 3. Authentication & Authorization

### 3.1 Password Security

- Passwords hashed with **bcrypt** (`passlib.context.CryptContext`).
- Default superuser password is flagged with a runtime warning if unchanged.
- Password reset tokens are short-lived JWTs (30-minute expiry).

### 3.2 JWT Token Architecture

| Token Type    | Algorithm | Lifetime       | Purpose                  |
| ------------- | --------- | -------------- | ------------------------ |
| Access Token  | HS256     | 8 hours        | API authentication       |
| Refresh Token | HS256     | 30 days        | Token rotation with JTI  |
| Reset Token   | HS256     | 30 minutes     | Password reset           |
| Invite Token  | HS256     | 7 days         | Tenant invitation        |
| MFA Setup     | HS256     | Configurable   | 2FA enrollment           |
| MFA Login     | HS256     | Configurable   | 2FA challenge            |

- Refresh tokens include a unique `jti` (JWT ID) for revocation tracking.
- All tokens are validated against `SECRET_KEY` which must be a secure random string in production.

### 3.3 Multi-Factor Authentication (MFA)

- TOTP-based 2FA using RFC 6238 (compatible with Google Authenticator, Authy).
- Pure-Python implementation ??no dependency on `pyotp` runtime.
- Configurable TOTP window (default Â±1 interval for clock skew tolerance).
- Admin 2FA for platform admin panel with separate enforcement.

### 3.4 Single Sign-On (SSO)

- Google OAuth 2.0 and Microsoft OAuth 2.0 supported.
- Per-tenant SSO configuration with signed OAuth state tokens.
- Email domain auto-discovery for SSO provider routing.
- PKCE (code verifier) support for token exchange.

### 3.5 Role-Based Access Control (RBAC)

| Role       | Scope                                     |
| ---------- | ----------------------------------------- |
| superuser  | Platform-wide admin, bypasses RLS         |
| owner      | Tenant owner ??billing, user management   |
| admin      | Tenant admin ??user & document management |
| employee   | Standard user ??chat, document viewing    |

## 4. Tenant Isolation

### 4.1 Database-Level Isolation

- **Row-Level Security (RLS):** PostgreSQL RLS policies enforce tenant isolation at the database query level.
- `app.tenant_id` session variable is set on every authenticated request via `apply_rls_context()`.
- Superusers bypass RLS (`app.bypass_rls = 1`).
- All tables with tenant data include a `tenant_id` foreign key with an index.

### 4.2 Application-Level Isolation

- Every CRUD operation filters by `tenant_id` in the WHERE clause.
- Department CRUD operations pass `tenant_id` at the query level (not post-fetch validation).
- API dependencies automatically bind `tenant_id` from the authenticated user's JWT.

### 4.3 Isolation Levels

| Level      | Description                                            |
| ---------- | ------------------------------------------------------ |
| standard   | Shared infrastructure, logical isolation via RLS       |
| enhanced   | Encrypted data at rest per tenant                      |
| dedicated  | Independent encryption keys (Enterprise tier)          |

- Per-tenant `TenantSecurityConfig` stores isolation level, IP whitelist, MFA requirement, and data retention policy.

## 5. Network & Transport Security

### 5.1 TLS Configuration

- **TLS 1.2+ enforced** ??weak protocols disabled.
- Cipher suite: `HIGH:!aNULL:!MD5`.
- HSTS header: `max-age=63072000; includeSubDomains; preload`.
- SSL session caching: shared 10m, timeout 1 day.
- Database connections enforce `POSTGRES_SSL_MODE=require` in production.

### 5.2 Security Headers

| Header                    | Value                                                 |
| ------------------------- | ----------------------------------------------------- |
| X-Frame-Options           | DENY                                                  |
| X-Content-Type-Options    | nosniff                                               |
| Strict-Transport-Security | max-age=63072000; includeSubDomains; preload          |
| Content-Security-Policy   | default-src 'self'; script-src 'self' 'unsafe-inline' |
| Referrer-Policy           | strict-origin-when-cross-origin                       |

### 5.3 Rate Limiting

Multi-layer rate limiting using Redis sliding window:

| Scope             | Limit              | Window |
| ----------------- | ------------------ | ------ |
| Global per IP     | 200 requests       | 1 min  |
| Per user          | 60 requests        | 1 min  |
| Per tenant        | 300 requests       | 1 min  |
| Chat per user     | 20 requests        | 1 min  |
| Auth endpoints    | 10 requests        | 1 min  |
| Admin endpoints   | 30 requests        | 1 min  |

- **Abuse detection:** automatic 10-minute IP block after 100+ requests in 60 seconds.
- Nginx `limit_req_zone` provides an additional layer of rate limiting at the gateway.

## 6. Data Protection

### 6.1 Encryption

- **At rest:** Cloudflare R2 provides server-side encryption. PostgreSQL supports TDE for enhanced/dedicated tenants.
- **In transit:** All communication encrypted via TLS 1.2+. Database connections use SSL.
- **Secrets:** Production secrets managed via environment variables. Insecure default keys are detected and flagged at startup.

### 6.2 File Upload Security

- **ClamAV malware scanning:** all uploaded files scanned before processing.
- Configurable `CLAMAV_FAIL_CLOSED=True` ??files rejected if scanner is unavailable.
- Maximum file size: 50 MB.
- Files stored in Cloudflare R2 with tenant-scoped paths.

### 6.3 LLM Security

- **Prompt injection guard:** configurable block patterns for injection attempts (e.g. "ignore previous instructions", "system prompt", "è¶Šæ?").
- **Sensitive data filter (input):** blocks PII patterns (ID numbers, credit cards, passwords, OTP).
- **Sensitive data filter (output):** strips API keys, tokens, system prompts from LLM responses.
- **Guardrail toggle:** `LLM_GUARDRAIL_ENABLED` for runtime control.
- Tenant documents are scoped ??RAG retrieval only returns chunks belonging to the requesting tenant.

## 7. Audit & Compliance

### 7.1 Audit Logging

- All significant operations logged with `AuditLog` model (user, action, resource, IP, timestamp).
- Usage tracking via `UsageRecord` with token counts and cost estimation.
- **Retention:** configurable, default 7 years (`AUDIT_RETENTION_YEARS=7`) per Taiwan labor law.
- Export available in CSV and PDF formats (Pro+ feature).

### 7.2 Data Processing Agreement (DPA)

Sub-processors with data handling scope:

| Sub-processor     | Purpose                 | Data Location |
| ----------------- | ----------------------- | ------------- |
| Linode (Akamai)   | Compute & hosting       | Asia-Pacific  |
| Cloudflare R2     | Object storage          | Global CDN    |
| Pinecone          | Vector search           | AWS us-east   |
| Google Gemini     | LLM generation          | US            |
| Voyage AI         | Embedding generation    | US            |
| LlamaParse        | Document parsing        | US            |
| SendGrid          | Transactional email     | US            |

### 7.3 Data Retention & Deletion

- Per-tenant configurable data retention (default 365 days).
- Data deletion SOP documented in `DATA_DELETION_SOP.md`.
- Backup/restore drill documented in `BACKUP_RESTORE_DRILL.md`.

## 8. Infrastructure Security

### 8.1 Container Security

- Multi-stage Docker builds minimize image size and attack surface.
- Non-root container execution where possible.
- Celery workers configured with:
  - `max_tasks_per_child=100` (prevent memory leaks)
  - `max_memory_per_child_kb=524288` (512 MB cap)
  - `task_soft_time_limit=300s`, `task_time_limit=360s`
  - Late acknowledgment (`task_acks_late=True`)

### 8.2 Monitoring & Alerting

- **ºÊ±±«ü¼Ð:** metrics collection from backend, Celery, PostgreSQL, Redis, Nginx.
- **ºÊ±±­¶­±:** dashboards for system health, API performance, resource utilization.
- **§iÄµªA°È:** 30+ alert rules across categories:
  - Backend: high error rates, slow response times
  - Security: auth failures, abuse detection
  - Infrastructure: disk, memory, CPU thresholds
  - Celery: task failures, queue depth
- Alerting channels: SMTP email + Slack webhook.

### 8.3 Backup & Recovery

- Full PostgreSQL backups via `pg_dumpall`.
- Point-in-time recovery supported.
- Backup verification script (`verify_backup.sh`).
- Restore drill documented and tested.

## 9. Application Security Controls

### 9.1 Input Validation

- Pydantic models validate all API inputs with strict typing.
- SQL injection prevented by SQLAlchemy ORM parameterized queries.
- File type and size validation on uploads.

### 9.2 CORS Policy

- `BACKEND_CORS_ORIGINS` configured per environment.
- Credentials support enabled only for whitelisted origins.

### 9.3 Admin Endpoint Isolation

- Admin API routes (`/api/v1/admin/`, `/api/v1/analytics/`) blocked at the Nginx gateway level for client-facing domains.
- Admin microservice runs on a separate port (8001) with service token authentication.
- Optional IP whitelist support for admin domain.

## 10. Incident Response

- ºÊ±±­¶­±»P§iÄµªA°È provide real-time detection of anomalies.
- Abuse detection automatically blocks offending IPs for 10 minutes.
- Audit logs provide forensic trail for investigations.
- Operations SOP documented in `OPS_SOP.md`.

## 11. Compliance Summary

| Framework       | Status                                                  |
| --------------- | ------------------------------------------------------- |
| Taiwan PDPA     | Compliant ??DPA, data deletion SOP, audit retention     |
| OWASP Top 10    | Addressed ??injection, auth, access control, headers    |
| SOC 2 Type II   | Readiness ??audit logs, access control, monitoring      |
| GDPR (reference)| Partial ??DPA sub-processors, data export, deletion     |

---

*This document is maintained by the UniHR security team and reviewed quarterly.*
