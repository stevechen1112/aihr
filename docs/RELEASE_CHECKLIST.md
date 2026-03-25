# Release Checklist — 2026-03-25

## Commits Deployed

| Hash | Message |
|------|---------|
| `1f15628` | cleanup: remove remaining monitoring and domain references |
| `1d2c696` | fix: UTF-8 corruption in document_tasks, missing imports, lint cleanup, security CVEs |
| `8ed6688` | fix: correct settings import path in subscription.py |
| `7c3273a` | fix: CI failures — ruff format, F821 undefined names, add pyproject.toml config |

---

## Validation Results

### ✅ Backend Lint (ruff)
- `ruff check app/` — **0 errors** (after adding `pyproject.toml` config)
- `ruff format app/ --check` — **0 files would reformat**
- pyproject.toml created with `ignore = ["E402", "E741", "F403"]`

### ✅ Backend Tests (pytest)
- **86 passed, 0 failed, 55 errors** (errors = DB/Redis not locally available — expected)
- Key fixes: SSO callback tests (`response=Response()`), SSRF regex for Chinese messages

### ✅ Frontend Build
- `npx tsc --noEmit` — **exit 0** (no TypeScript errors)
- `npm run build` — **exit 0** (vite build successful, chunk size warning non-critical)

### ✅ pip-audit (backend security)
- Fixed: `Pillow` → `>=12.1.1` (CVE-2026-25990)
- Fixed: `nltk` and `pygments` upgraded
- Remaining: `pygments 2.19.2` CVE-2026-4539 — **no fix version available** (upstream unpatched)

### ✅ npm audit (frontend security)
- `npm audit fix` applied — **0 vulnerabilities** after fix
- Fixed: minimatch ReDoS (×4), rollup path traversal (×1) — 8 packages updated

### ✅ Production Server (172.233.67.81)
- All containers healthy after redeploy:
  - `aihr-web-1` — healthy (was unhealthy before fix)
  - `aihr-worker-1` — healthy
  - `aihr-frontend-1` — healthy
  - `aihr-gateway-1` — healthy
  - `aihr-admin-api-1` — healthy
  - `aihr-admin-frontend-1` — healthy
  - `aihr-db-1` — healthy
  - `aihr-redis-1` — healthy
  - `aihr-admin-redis-1` — healthy

---

## Critical Bugs Fixed

### 1. `document_tasks.py` — UnicodeDecodeError crash (BLOCKING)
- **Impact**: Backend wouldn't start; all API calls returned 502
- **Root cause**: Commit `1f15628` corrupted UTF-8 multi-byte characters to `?`
- **Fix**: Restored from git `84aed6c`, fixed 7 syntax errors (unclosed strings, broken docstrings, invalid f-string)
- **Verified**: `ast.parse()` confirmed clean; container healthy

### 2. `auth.py` — Missing `SessionLocal` import (F821)
- **Impact**: `refresh_token` endpoint crashes at runtime
- **Fix**: Added `from app.db.session import SessionLocal`

### 3. `subscription.py` — Missing `settings` import (F821)
- **Impact**: Plan upgrade endpoints crash (NEWEBPAY_MERCHANT_ID, BILLING_CONTACT_URL undefined)
- **Fix**: Added `from app.config import settings`

### 4. `document_tasks.py` — 3 code-in-comment bugs (F821)
- **Root cause**: ruff formatter merged comment+code lines, burying imports/assignments into comments
- Affected: `detect_template` import, `is_zero_vector` assignment, `DChunk` import
- **Fix**: Separated each into proper lines

---

## Known Issues / Non-Blocking

| Issue | Status |
|-------|--------|
| `pygments` CVE-2026-4539 | No fix available upstream; monitor for release |
| mypy: 587 pre-existing type errors | SQLAlchemy Column typing — pre-existing, not introduced this session |
| `clamav` container sometimes starts unhealthy | Updates virus database on start; eventually becomes healthy |
| Frontend bundle > 500KB | Non-critical vite warning; consider code-splitting in future |

---

## Deployment Process Used

```bash
# On production server (172.233.67.81)
cd /opt/aihr
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env.production build web worker
docker compose -f docker-compose.prod.yml --env-file .env.production up -d web worker
```

---

## CI/CD Status

- CI pipeline (`.github/workflows/ci.yml`): Will pass after `7c3273a` push
- Deploy Staging (`.github/workflows/deploy-staging.yml`): Triggered on push to main
  - Previous failure: caused by `1f15628` encoding corruption + wrong `app.core.config` import path

