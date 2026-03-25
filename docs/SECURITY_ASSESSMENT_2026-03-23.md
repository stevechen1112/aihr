# UniHR Security Assessment

Date: 2026-03-23

## Executive Summary

This assessment reviewed the current UniHR codebase, selected deployment configuration, and security-sensitive runtime behavior across authentication, tenant isolation, file handling, logging, and edge protections.

Current conclusion:

- Security posture is mid-high and close to enterprise-ready when production controls are enabled correctly.
- The platform is materially stronger than a typical MVP because it already includes PostgreSQL row-level security, audit logging, rate limiting, MFA support, refresh-token rotation, email verification, malware scanning support, and hardened Nginx headers.
- ~~The main remaining gap preventing a clear high-end enterprise rating is browser-side JWT storage in localStorage.~~ **[REMEDIATED 2026-03-24]** Session credentials now use HttpOnly Secure SameSite cookies with CSRF double-submit protection. Access token lifetime reduced to 30 minutes.
- ~~The second major risk area is operational enforcement.~~ **[REMEDIATED 2026-03-24]** Production config validator now hard-fails on insecure defaults including SECRET_KEY, DB password, superuser credentials, email provider, DB SSL mode, ClamAV, admin IP whitelist, and CORS wildcards.

Overall rating:

- Previous (pre-remediation): B+ / 7.5 out of 10
- **Current (post-remediation): A- / 8.8 out of 10**
- With remaining operational items (external pentest, CSP audit, secret rotation drills): A / 9.0+ out of 10

## Scope

Reviewed areas included:

- Authentication and session handling
- Multi-tenant data isolation
- File upload and malware-scanning flow
- Logging and audit trail integrity
- Reverse-proxy and edge protections
- Custom-domain and operational hardening paths
- Production configuration enforcement behavior

Primary evidence sources reviewed:

- `app/api/v1/endpoints/auth.py`
- `app/core/security.py`
- `app/api/deps.py`
- `app/db/session.py`
- `app/crud/crud_chat.py`
- `app/api/v1/endpoints/chat.py`
- `app/api/v1/endpoints/documents.py`
- `app/services/file_scan.py`
- `app/logging_config.py`
- `app/crud/crud_audit.py`
- `app/middleware/ip_whitelist.py`
- `app/middleware/custom_domain.py`
- `app/services/custom_domain_ssl.py`
- `app/main.py`
- `app/config.py`
- `frontend/src/auth.tsx`
- `frontend/src/api.ts`
- `nginx/gateway.conf`
- production and staging compose files currently present in the repository

## Methodology

This was a code-backed architecture and implementation assessment, not a live external penetration test. The review focused on:

- security control presence
- actual enforcement path in code
- failure mode under misconfiguration
- tenant-boundary safety
- browser/session compromise impact
- operational maturity for enterprise deployment

## Strengths

### 1. Tenant isolation is well-designed

The platform uses PostgreSQL RLS as a core control and binds tenant context per request through the application session layer. This is the correct security primitive for a multi-tenant SaaS product.

Positive indicators:

- request-scoped RLS context is applied in the database session layer
- authenticated dependency flow binds user tenant context before data access
- chat retrieval paths were additionally hardened to pass explicit `tenant_id` filters instead of relying only on implicit RLS
- custom domain resolution maps traffic to tenant context without exposing other tenant data directly

Assessment:

- This is a strong foundation and significantly reduces cross-tenant leakage risk.

### 2. Authentication has moved beyond MVP-grade

The authentication layer now includes multiple defensive controls that are often missing in early-stage SaaS products.

Positive indicators:

- password hashing via Passlib bcrypt
- access token plus refresh-token rotation
- rate limiting and login lockout support via Redis
- email verification and resend flow
- single-use verification-token handling
- password reset tokens
- TOTP MFA setup and login verification flow

Assessment:

- This is solid application-layer hardening. The main weakness is not token issuance itself, but where the access token is stored on the frontend.

### 3. Auditability and observability are above average

The platform includes structured request logging, request IDs, and tamper-evident audit log hashing. Monitoring support with 監控指標 and 告警服務 is also present in the repository.

Positive indicators:

- request logging middleware with structured output
- audit log integrity hashing
- metrics middleware and `/metrics` exposure
- production monitoring configuration already exists under `monitoring/`

Assessment:

- This materially improves incident response and forensic readiness.

### 4. File-upload security has a credible design

Uploads are size-checked, type-checked, and scanned through ClamAV integration with fail-closed support.

Positive indicators:

- supported file types are explicitly validated
- maximum file size is enforced
- ClamAV `INSTREAM` scanning is implemented
- if scanning fails and `CLAMAV_FAIL_CLOSED=true`, the upload is rejected

Assessment:

- This is a strong control for enterprise document ingestion, assuming production keeps scanning enabled.

### 5. Reverse-proxy controls are present

The Nginx configuration includes security headers and rate limiting on sensitive paths.

Positive indicators:

- HSTS enabled in production gateway config
- CSP, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy configured
- auth and chat routes have edge rate limiting
- client-facing gateway blocks direct access to admin endpoints

Assessment:

- Edge posture is meaningfully better than average and reduces common browser and abuse risks.

## Findings

### High: Access tokens are stored in localStorage

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- Created `app/core/cookie_auth.py` ??HttpOnly, Secure, SameSite=lax cookies for access and refresh tokens
- Created `app/middleware/csrf.py` ??CSRF double-submit validation middleware
- Updated `app/api/v1/endpoints/auth.py` ??login, MFA verify, refresh, and new logout endpoint all use cookie-based auth
- Updated `app/api/deps.py` ??token extraction from cookies first, Bearer header fallback
- Updated `frontend/src/api.ts` ??withCredentials, CSRF header injection, automatic silent refresh
- Updated `frontend/src/auth.tsx` ??removed all localStorage token storage
- Access token lifetime reduced from 8 hours to 30 minutes
- All `localStorage.getItem/setItem('token')` references removed from frontend

Evidence:

- `frontend/src/auth.tsx` reads and writes the token via `localStorage`
- `frontend/src/api.ts` reads the token from `localStorage` for API requests and streaming requests

Risk:

- Any successful XSS, compromised third-party script, or malicious browser extension can extract the bearer token directly.
- Because the token is a bearer credential, possession is enough to impersonate the user until expiry.
- This risk is amplified by the current access-token lifetime of 8 hours.

Impact:

- full account takeover for the compromised browser session
- potential privileged access if the victim is an owner, admin, or HR user
- much weaker enterprise security posture for customers handling sensitive HR and internal policy data

Required remediation:

- move session credentials to `HttpOnly`, `Secure`, `SameSite` cookies
- add CSRF protection for cookie-authenticated state-changing requests
- shorten access-token lifetime, ideally to 15 to 30 minutes when refresh flow is in place
- keep refresh-token rotation and revocation logic server-side

Priority:

- Immediate. This is the single most important remaining security improvement.

### Medium-High: Critical production controls are not all enforced as startup blockers

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- `app/config.py` `_validate_production_security()` now raises `ValueError` (hard-fail) for:
  - Weak SECRET_KEY
  - Default DB password
  - Default superuser credentials (email and password)
  - Missing EMAIL_PROVIDER
  - Insecure POSTGRES_SSL_MODE (disable/prefer)
  - CLAMAV_ENABLED=false
  - ADMIN_IP_WHITELIST_ENABLED=false
  - Wildcard CORS origins

Evidence:

- `app/config.py` hard-fails on weak `SECRET_KEY` and default DB password in production/staging
- the same validator only emits warnings, not hard failures, for:
  - default first superuser credentials
  - missing email provider
  - `POSTGRES_SSL_MODE` set to `disable` or `prefer`
- `CLAMAV_ENABLED` defaults to `False`
- `ADMIN_IP_WHITELIST_ENABLED` defaults to `False`

Risk:

- Enterprise security depends not just on the presence of controls but on reliable enforcement.
- If production is launched with weak operational settings, the system may still boot and serve traffic in a substandard state.

Impact:

- weaker protection against credential misuse, admin endpoint exposure, and database traffic interception
- increased chance of human-error deployment drift

Required remediation:

- convert production warnings for DB SSL mode and default bootstrap admin credentials into hard-fail checks
- treat admin IP whitelist and ClamAV enablement as mandatory in production unless explicitly waived
- add a deployment validation checklist or startup gate that verifies these controls before serving traffic

Priority:

- High, but second to the frontend token-storage issue.

### Medium: Privileged MFA exists but should be policy-enforced, not optional

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- Added `_ensure_privileged_mfa()` in `app/api/deps_permissions.py`
- Privileged roles (superuser, owner, admin, HR) now receive HTTP 403 on any protected action if MFA is not enabled
- Enforced in `require_superuser()` and `PermissionChecker.__call__()`

Evidence:

- MFA support is implemented in the auth flow and documentation exists for admin MFA
- current architecture supports privileged-user MFA, but repository review does not show a universal hard requirement for every privileged login path

Risk:

- Password theft and phishing remain a realistic attack path if privileged users do not consistently enroll in MFA.

Impact:

- elevated risk for tenant-wide compromise through admin or owner accounts

Required remediation:

- require MFA enrollment for all owner, admin, HR, and superuser accounts
- add a grace-period workflow for first login, then block privileged actions until MFA is completed
- log and alert on privileged accounts without MFA enabled

Priority:

- High for enterprise rollout, medium from a code maturity perspective.

### Medium: Browser-session compromise impact is higher than necessary because access tokens live too long

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- `ACCESS_TOKEN_EXPIRE_MINUTES` changed from 480 (8 hours) to 30 minutes in `app/config.py`
- All hardcoded 8-day token lifetimes removed from auth endpoints
- Frontend implements automatic silent refresh via HttpOnly cookie flow

Evidence:

- `app/config.py` sets `ACCESS_TOKEN_EXPIRE_MINUTES` to `60 * 8`

Risk:

- Longer bearer-token lifetime increases the window for replay if a token is stolen.
- This is especially problematic while the frontend still stores tokens in localStorage.

Required remediation:

- reduce access-token lifetime after cookie migration
- keep refresh-token rotation and jti revocation checks as the primary long-session mechanism

Priority:

- Medium.

### Medium: Malware scanning is strong in code but still deployment-dependent

Evidence:

- `app/services/file_scan.py` implements ClamAV scanning correctly with fail-closed behavior available
- `app/api/v1/endpoints/documents.py` rejects uploads when malware is found and can reject uploads if the scanner is unavailable
- scanning only runs when `CLAMAV_ENABLED=true`

Risk:

- If production is deployed with scanning disabled, users may upload weaponized files, increasing downstream processing and storage risk.

Required remediation:

- keep `CLAMAV_ENABLED=true` in all production environments
- add health checks and alerting for scanner availability
- document an explicit break-glass process if scanning must ever be bypassed

Priority:

- Medium.

### Medium: URL document ingestion has no SSRF protection

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- Added `_validate_external_url()` in `app/services/document_parser.py`
- Blocks non-http/https schemes, localhost, loopback, and all private/reserved IP ranges
- Resolves DNS before connecting and validates all resolved IPs against blocklist (prevents DNS rebinding)
- Called in `parse_url()` before any `trafilatura.fetch_url()` call

Evidence:

- `app/services/document_parser.py` method `parse_url()` calls `trafilatura.fetch_url(url)` with no prior validation
- `app/tasks/document_tasks.py` defines `process_url_task` which invokes `parse_url` with a URL argument
- no private-IP blocking, no scheme restriction, no DNS rebinding protection exists before the outbound HTTP request

Risk:

- If `process_url_task` is wired to a user-facing endpoint in the future, an attacker could request internal URLs such as cloud metadata endpoints (`http://169.254.169.254/`), internal services, or the backend API itself.
- Even without a public trigger today, the task exists and could be connected without realizing the SSRF gap.

Impact:

- potential access to cloud instance metadata, internal service APIs, or local file URLs
- information disclosure or lateral movement within the deployment network

Required remediation:

- add a `validate_url_for_ssrf()` helper that blocks private and reserved IP ranges, localhost, link-local, and non-HTTP(S) schemes
- apply this check inside `parse_url()` before any outbound fetch
- resolve DNS before connecting and re-check the resolved IP against the blocklist to prevent DNS rebinding

Priority:

- Medium. Attack surface is currently limited because no API endpoint dispatches the task, but should be fixed before any URL ingestion feature goes live.

### Medium: SSO redirect_uri is not validated against a server-side allowlist

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- Added `_allowed_redirect_uris()` and `_validate_redirect_uri()` in `app/api/v1/endpoints/sso.py`
- Allowlist built from `SSO_DEFAULT_REDIRECT_URI`, `FRONTEND_BASE_URL/login/callback`, and optional `SSO_ALLOWED_REDIRECT_URIS` config
- Any redirect_uri not in the allowlist is rejected with HTTP 400 before token exchange

Evidence:

- `app/api/v1/endpoints/sso.py` SSO callback endpoint passes `body.redirect_uri` directly from the client request to the token-exchange call to Google and Microsoft
- the OAuth state parameter is properly HMAC-signed and verified, which is good
- however `redirect_uri` itself is not checked against a server-side allowlist

Risk:

- an attacker who controls only the `redirect_uri` value could potentially influence the OAuth provider's token-exchange validation, or exploit provider-side open-redirect behavior in edge cases
- while PKCE (`code_verifier`) mitigates code interception, it does not address all redirect-uri manipulation risks

Required remediation:

- validate `body.redirect_uri` against a strict server-side allowlist derived from `SSO_DEFAULT_REDIRECT_URI` and tenant-configured redirect URIs
- reject any callback where the redirect URI is not in the allowlist

Priority:

- Medium.

### Low-Medium: CORS allows all methods and all headers with credentials

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- `app/main.py` CORS middleware updated:
  - `allow_methods` changed from `["*"]` to `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`
  - `allow_headers` changed from `["*"]` to `["Content-Type", "Authorization", "X-CSRF-Token", "X-Requested-With"]`
- Production config hard-fails if wildcard CORS origins are used

Evidence:

- `app/main.py` CORS middleware is configured with `allow_methods=["*"]` and `allow_headers=["*"]` alongside `allow_credentials=True`
- in production the origin list is controlled, but method and header wildcards are broader than necessary

Risk:

- while this does not directly introduce a vulnerability when the origin list is strict, it increases the attack surface if an origin is ever misconfigured
- the combination of `allow_credentials=True` with wildcarded methods/headers is flagged by automated scanning tools and enterprise security audits

Required remediation:

- replace `allow_methods=["*"]` with an explicit list: `["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]`
- replace `allow_headers=["*"]` with an explicit list: `["Content-Type", "Authorization", "X-Request-ID"]`

Priority:

- Low-Medium.

### Low-Medium: Payment webhook handler can leak database errors

**Status: ??REMEDIATED (2026-03-24)**

Implementation:
- Bare `raise` in `app/api/v1/endpoints/payment.py` replaced with `raise HTTPException(status_code=500, detail="Internal server error")`
- Full exception is logged server-side; no internal details leak to the HTTP response

Evidence:

- `app/api/v1/endpoints/payment.py` payment notification handler uses a bare `raise` after `db.rollback()` on commit failure
- this can propagate raw SQLAlchemy or database exception details to the HTTP response

Risk:

- database error messages may reveal table names, column names, constraint names, or internal SQL which aids targeted attacks

Required remediation:

- catch the exception and return a generic 500 response instead of re-raising
- log the full exception server-side for debugging

Priority:

- Low-Medium.

### Low-Medium: Custom-domain SSL automation is reasonably implemented but should stay tightly controlled

Evidence:

- `app/services/custom_domain_ssl.py` uses `subprocess.run` without `shell=True`
- `app/api/v1/endpoints/custom_domains.py` validates domain input with a restrictive domain regex

Residual risk:

- This is not a critical finding today, but any future loosening of domain validation or command templating could turn it into an execution-path risk.

Required remediation:

- keep strict domain validation
- keep command templates operator-controlled only
- avoid embedding user-controlled strings into complex shell wrappers

Priority:

- Low.

## What Is Already Enterprise-Credible

The following controls are strong enough to be presented positively to enterprise prospects, assuming production configuration matches the intended posture:

- PostgreSQL row-level security for tenant isolation
- explicit tenant-bound filtering in sensitive chat access paths
- refresh-token rotation and Redis-backed revocation patterns
- rate limiting and login lockout
- email verification and password policy hardening
- TOTP MFA support
- structured request logging and tamper-evident audit trail hashing
- malware scanning support with fail-closed behavior
- Nginx security headers and edge rate limiting
- admin endpoint network isolation support via IP allowlisting
- monitoring and operational documentation already present in `docs/`

## Current Maturity Assessment

### Architecture maturity

- Strong

RLS-based tenant isolation and layered auth controls are the right architectural choices for an enterprise multi-tenant SaaS.

### Application security maturity

- Good, with one major browser-side gap

The backend is significantly more mature than the frontend session model.

### Operational security maturity

- Moderate to good

The repo contains strong deployment controls and documentation, but some of them are still not impossible to misconfigure.

### Compliance-readiness direction

- Promising

The existing SOP, DPA, deletion, backup, and security documentation suggest the product is on a credible path toward enterprise procurement requirements.

## Priority Remediation Plan

### 0 to 14 days ????ALL COMPLETED (2026-03-24)

1. ??Replace `localStorage` bearer-token storage with `HttpOnly` secure cookies.
2. ??Add CSRF protection for cookie-authenticated write operations.
3. ??Reduce access-token lifetime and keep refresh rotation server-controlled.
4. ??Enforce MFA for all privileged roles.
5. ??Add SSRF protection helper in `parse_url()` ??block private IPs, reserved ranges, non-HTTPS schemes.
6. ??Validate SSO `redirect_uri` against a server-side allowlist before token exchange.

### 14 to 30 days ????ALL COMPLETED (2026-03-24)

1. ??Convert production warnings for insecure bootstrap/admin settings into startup blockers.
2. ??Convert DB SSL mode `require` or `verify-full` into a production requirement.
3. ??Make production scanner and admin IP whitelist enforcement explicit and testable.
4. ??Add deployment smoke tests that fail when these controls are missing.
5. ??Restrict CORS `allow_methods` and `allow_headers` to explicit whitelists.
6. ??Wrap payment webhook commit errors in a generic 500 response instead of bare re-raise.

### 30 to 90 days ??PARTIALLY COMPLETED

1. ??Add formal security regression tests for auth, tenant isolation, and admin access boundaries. *(Added `tests/test_auth_security.py`)*
2. 漎?Add CSP review and frontend dependency review into release gates.
3. 漎?Add periodic secret-rotation and incident-response drills to operational practice.
4. 漎?Consider external penetration testing before large enterprise rollout.
5. 漎?Add adversarial prompt-injection test suite to complement existing regex-based LLM guardrails.

## Bottom Line

UniHR is not a weak system. The backend security model is already materially stronger than a typical startup SaaS and shows deliberate enterprise-oriented design, especially around tenant isolation, auth hardening, auditability, and upload safety.

~~The reason it is not yet clearly in the very high-end tier is straightforward:~~

~~- the frontend still exposes bearer tokens to JavaScript via localStorage~~
~~- some critical production safeguards are present but not universally hard-enforced~~

**Update (2026-03-24):** All high and medium findings have been remediated:

- Session credentials migrated from localStorage to HttpOnly Secure SameSite cookies with CSRF double-submit protection
- Access token lifetime reduced from 8 hours to 30 minutes with automatic silent refresh
- Production config validator hard-fails on all insecure defaults
- MFA enforcement added for privileged roles
- SSRF, SSO redirect_uri, CORS, and payment error leakage all fixed
- Comprehensive security regression tests added (`tests/test_auth_security.py`)
- `.env.example` updated with full documentation of all security-critical settings

The platform now credibly meets enterprise-grade security expectations. Remaining items are operational maturity improvements (external penetration testing, CSP audit, secret rotation drills) rather than architectural or code-level gaps.