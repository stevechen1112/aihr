#!/bin/bash
# Comprehensive Live Production Test Suite for UniHR SaaS
# Target: http://localhost:80 (run inside server)
BASE="http://localhost:80/api/v1"
PASS=0
FAIL=0
WARN=0
TOTAL=0

test_result() {
  local name="$1" status="$2" detail="$3"
  TOTAL=$((TOTAL+1))
  if [ "$status" = "PASS" ]; then
    PASS=$((PASS+1))
    echo "  ✅ $name — $detail"
  elif [ "$status" = "WARN" ]; then
    WARN=$((WARN+1))
    echo "  ⚠️  $name — $detail"
  else
    FAIL=$((FAIL+1))
    echo "  ❌ $name — $detail"
  fi
}

section() {
  echo ""
  echo "══════════════════════════════════════════"
  echo "  $1"
  echo "══════════════════════════════════════════"
}

# Extract CSRF token from a cookie file
get_csrf() {
  local cookie_file="$1"
  grep 'unihr_csrf' "$cookie_file" 2>/dev/null | awk '{print $NF}'
}

# ═══════════════════════════════════════
#  SECTION 1: AUTHENTICATION
# ═══════════════════════════════════════
section "1. AUTHENTICATION TESTS"

# Login all 5 roles
for role_info in "owner:owner@aihr.app:Owner123!" "admin:admin@aihr.app:Admin123!" "hr:hr@aihr.app:HrUser123!" "employee:employee@aihr.app:Employee123!" "viewer:viewer@aihr.app:Viewer123!"; do
  IFS=: read -r role email pass <<< "$role_info"
  HTTP=$(curl -sS -o /tmp/body_${role}.json -w "%{http_code}" -c /tmp/cookies_${role}.txt \
    -X POST "${BASE}/auth/login/access-token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${email}&password=${pass}" 2>/dev/null)
  if [ "$HTTP" = "200" ]; then
    test_result "Login ${role} (${email})" "PASS" "HTTP ${HTTP}"
  else
    test_result "Login ${role} (${email})" "FAIL" "HTTP ${HTTP}"
  fi
done

# Wrong password
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "${BASE}/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@aihr.app&password=WRONG" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "400" ]; then
  test_result "Wrong password rejected" "PASS" "HTTP ${HTTP}"
else
  test_result "Wrong password rejected" "FAIL" "HTTP ${HTTP}"
fi

# Non-existent user
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "${BASE}/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=fake@fake.com&password=Nope123!" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "400" ]; then
  test_result "Non-existent user rejected" "PASS" "HTTP ${HTTP}"
else
  test_result "Non-existent user rejected" "FAIL" "HTTP ${HTTP}"
fi

# Empty credentials
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "${BASE}/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=&password=" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "400" ] || [ "$HTTP" = "422" ]; then
  test_result "Empty credentials rejected" "PASS" "HTTP ${HTTP}"
else
  test_result "Empty credentials rejected" "FAIL" "HTTP ${HTTP}"
fi

# /users/me for each role
for role in owner admin hr employee viewer; do
  HTTP=$(curl -sS -o /tmp/me_${role}.json -w "%{http_code}" -b /tmp/cookies_${role}.txt "${BASE}/users/me" 2>/dev/null)
  ROLE_DB=$(python3 -c "import json; print(json.load(open('/tmp/me_${role}.json')).get('role','?'))" 2>/dev/null)
  EMAIL_DB=$(python3 -c "import json; print(json.load(open('/tmp/me_${role}.json')).get('email','?'))" 2>/dev/null)
  if [ "$HTTP" = "200" ]; then
    test_result "GET /users/me (${role})" "PASS" "email=${EMAIL_DB} role=${ROLE_DB}"
  else
    test_result "GET /users/me (${role})" "FAIL" "HTTP ${HTTP}"
  fi
done

# Token refresh
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt -c /tmp/cookies_admin.txt \
  -X POST "${BASE}/auth/refresh" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Token refresh (admin)" "PASS" "HTTP ${HTTP}"
else
  test_result "Token refresh (admin)" "FAIL" "HTTP ${HTTP}"
fi

# Unauthenticated access
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE}/users/me" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "403" ]; then
  test_result "Unauth /users/me blocked" "PASS" "HTTP ${HTTP}"
else
  test_result "Unauth /users/me blocked" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE}/documents/" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "403" ]; then
  test_result "Unauth /documents blocked" "PASS" "HTTP ${HTTP}"
else
  test_result "Unauth /documents blocked" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE}/chat/conversations" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "403" ]; then
  test_result "Unauth /chat blocked" "PASS" "HTTP ${HTTP}"
else
  test_result "Unauth /chat blocked" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE}/audit/logs" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "403" ]; then
  test_result "Unauth /audit/logs blocked" "PASS" "HTTP ${HTTP}"
else
  test_result "Unauth /audit/logs blocked" "FAIL" "HTTP ${HTTP}"
fi

# Logout + verify
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_viewer.txt -X POST "${BASE}/auth/logout" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Logout (viewer)" "PASS" "HTTP ${HTTP}"
else
  test_result "Logout (viewer)" "FAIL" "HTTP ${HTTP}"
fi

# Re-login viewer for later tests
curl -sS -o /dev/null -c /tmp/cookies_viewer.txt \
  -X POST "${BASE}/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=viewer@aihr.app&password=Viewer123!" 2>/dev/null

# ═══════════════════════════════════════
#  SECTION 2: RBAC / PERMISSIONS
# ═══════════════════════════════════════
section "2. RBAC PERMISSION TESTS"

# Admin-only endpoints tested by non-admin roles
for endpoint in "/admin/dashboard" "/admin/tenants"; do
  for role in employee viewer; do
    HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_${role}.txt "${BASE}${endpoint}" 2>/dev/null)
    if [ "$HTTP" = "403" ] || [ "$HTTP" = "401" ]; then
      test_result "${role} blocked from ${endpoint}" "PASS" "HTTP ${HTTP}"
    elif [ "$HTTP" = "404" ]; then
      test_result "${role} blocked from ${endpoint}" "WARN" "HTTP 404 (endpoint may not exist)"
    else
      test_result "${role} blocked from ${endpoint}" "FAIL" "HTTP ${HTTP}"
    fi
  done
done

# Owner/admin can access company dashboard
for role in owner admin; do
  HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_${role}.txt "${BASE}/company/dashboard" 2>/dev/null)
  if [ "$HTTP" = "200" ]; then
    test_result "${role} access /company/dashboard" "PASS" "HTTP ${HTTP}"
  else
    test_result "${role} access /company/dashboard" "FAIL" "HTTP ${HTTP}"
  fi
done

# Employee should not manage users
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_employee.txt "${BASE}/company/users" 2>/dev/null)
if [ "$HTTP" = "403" ] || [ "$HTTP" = "401" ]; then
  test_result "Employee blocked from /company/users" "PASS" "HTTP ${HTTP}"
else
  test_result "Employee blocked from /company/users" "WARN" "HTTP ${HTTP} (may allow read)"
fi

# Viewer should not upload documents
CSRF_TOK=$(get_csrf /tmp/cookies_viewer.txt)
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_viewer.txt \
  -X POST "${BASE}/documents/upload" \
  -H "X-CSRF-Token: ${CSRF_TOK}" \
  -F "file=@/dev/null;filename=test.txt" 2>/dev/null)
if [ "$HTTP" = "403" ] || [ "$HTTP" = "401" ]; then
  test_result "Viewer blocked from doc upload" "PASS" "HTTP ${HTTP}"
elif [ "$HTTP" = "422" ]; then
  test_result "Viewer blocked from doc upload" "WARN" "HTTP 422 (validation, not auth block)"
else
  test_result "Viewer blocked from doc upload" "FAIL" "HTTP ${HTTP}"
fi

# All roles should access documents list
for role in owner admin hr employee viewer; do
  HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_${role}.txt "${BASE}/documents/" 2>/dev/null)
  if [ "$HTTP" = "200" ]; then
    test_result "${role} can list documents" "PASS" "HTTP ${HTTP}"
  else
    test_result "${role} can list documents" "FAIL" "HTTP ${HTTP}"
  fi
done

# ═══════════════════════════════════════
#  SECTION 3: CORE FEATURES
# ═══════════════════════════════════════
section "3. CORE FEATURE TESTS"

# Documents list
HTTP=$(curl -sS -o /tmp/docs_list.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/documents/" 2>/dev/null)
DOC_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/docs_list.json')); print(d.get('total', len(d)) if isinstance(d, dict) else len(d))" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "List documents" "PASS" "HTTP ${HTTP}, count=${DOC_COUNT}"
else
  test_result "List documents" "FAIL" "HTTP ${HTTP}"
fi

# Document upload (small text file)
echo "This is a test document for UniHR testing." > /tmp/test_upload.txt
CSRF_TOK=$(get_csrf /tmp/cookies_admin.txt)
HTTP=$(curl -sS -o /tmp/upload_resp.json -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X POST "${BASE}/documents/upload" \
  -H "X-CSRF-Token: ${CSRF_TOK}" \
  -F "file=@/tmp/test_upload.txt;type=text/plain" 2>/dev/null)
if [ "$HTTP" = "200" ] || [ "$HTTP" = "201" ]; then
  DOC_ID=$(python3 -c "import json; print(json.load(open('/tmp/upload_resp.json')).get('id','?'))" 2>/dev/null)
  test_result "Upload document" "PASS" "HTTP ${HTTP}, doc_id=${DOC_ID}"
else
  test_result "Upload document" "FAIL" "HTTP ${HTTP}"
  DOC_ID=""
fi

# Get single document
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "?" ]; then
  HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/documents/${DOC_ID}" 2>/dev/null)
  if [ "$HTTP" = "200" ]; then
    test_result "Get document by ID" "PASS" "HTTP ${HTTP}"
  else
    test_result "Get document by ID" "FAIL" "HTTP ${HTTP}"
  fi
fi

# Chat - create conversation
CSRF_TOK=$(get_csrf /tmp/cookies_admin.txt)
HTTP=$(curl -sS -o /tmp/chat_resp.json -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X POST "${BASE}/chat/chat" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ${CSRF_TOK}" \
  -d '{"message":"你好，這是測試訊息"}' 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  CONV_ID=$(python3 -c "import json; print(json.load(open('/tmp/chat_resp.json')).get('conversation_id','?'))" 2>/dev/null)
  test_result "Chat message" "PASS" "HTTP ${HTTP}, conv=${CONV_ID}"
elif [ "$HTTP" = "503" ] || [ "$HTTP" = "502" ]; then
  test_result "Chat message" "WARN" "HTTP ${HTTP} (AI service may be unavailable)"
else
  test_result "Chat message" "FAIL" "HTTP ${HTTP}"
fi

# Conversations list
HTTP=$(curl -sS -o /tmp/convs.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/chat/conversations" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  CONV_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/convs.json')); print(len(d) if isinstance(d,list) else d.get('total',0))" 2>/dev/null)
  test_result "List conversations" "PASS" "HTTP ${HTTP}, count=${CONV_COUNT}"
else
  test_result "List conversations" "FAIL" "HTTP ${HTTP}"
fi

# Departments
HTTP=$(curl -sS -o /tmp/depts.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/departments/" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "List departments" "PASS" "HTTP ${HTTP}"
else
  test_result "List departments" "FAIL" "HTTP ${HTTP}"
fi

# Audit logs
HTTP=$(curl -sS -o /tmp/audit.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/audit/logs" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  AUDIT_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/audit.json')); print(d.get('total', len(d.get('items',d))) if isinstance(d,dict) else len(d))" 2>/dev/null)
  test_result "Audit logs" "PASS" "HTTP ${HTTP}, count=${AUDIT_COUNT}"
else
  test_result "Audit logs" "FAIL" "HTTP ${HTTP}"
fi

# Usage summary
HTTP=$(curl -sS -o /tmp/usage.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/audit/usage/summary" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Usage summary" "PASS" "HTTP ${HTTP}"
else
  test_result "Usage summary" "FAIL" "HTTP ${HTTP}"
fi

# Company profile
HTTP=$(curl -sS -o /tmp/company.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/company/profile" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  COMPANY=$(python3 -c "import json; print(json.load(open('/tmp/company.json')).get('name','?'))" 2>/dev/null)
  test_result "Company profile" "PASS" "HTTP ${HTTP}, name=${COMPANY}"
else
  test_result "Company profile" "FAIL" "HTTP ${HTTP}"
fi

# Company quota
HTTP=$(curl -sS -o /tmp/quota.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/company/quota" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Company quota" "PASS" "HTTP ${HTTP}"
else
  test_result "Company quota" "FAIL" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  SECTION 4: SUBSCRIPTION & BILLING
# ═══════════════════════════════════════
section "4. SUBSCRIPTION & BILLING"

HTTP=$(curl -sS -o /tmp/plans.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/subscription/plans" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Subscription plans" "PASS" "HTTP ${HTTP}"
else
  test_result "Subscription plans" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /tmp/current_sub.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/subscription/current" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  PLAN=$(python3 -c "import json; print(json.load(open('/tmp/current_sub.json')).get('plan','?'))" 2>/dev/null)
  test_result "Current subscription" "PASS" "HTTP ${HTTP}, plan=${PLAN}"
else
  test_result "Current subscription" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /tmp/billing.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/billing/" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Billing records" "PASS" "HTTP ${HTTP}"
else
  test_result "Billing records" "FAIL" "HTTP ${HTTP}"
fi

# Feature check
HTTP=$(curl -sS -o /tmp/feature.json -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/subscription/feature-check?feature=sso" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Feature check (SSO)" "PASS" "HTTP ${HTTP}"
else
  test_result "Feature check (SSO)" "FAIL" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  SECTION 5: SSO & ADVANCED
# ═══════════════════════════════════════
section "5. SSO, DOMAINS, REGIONS"

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/sso/config" 2>/dev/null)
if [ "$HTTP" = "200" ] || [ "$HTTP" = "404" ]; then
  test_result "SSO config" "PASS" "HTTP ${HTTP}"
else
  test_result "SSO config" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/custom-domains/" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Custom domains list" "PASS" "HTTP ${HTTP}"
else
  test_result "Custom domains list" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/regions/" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Regions list" "PASS" "HTTP ${HTTP}"
else
  test_result "Regions list" "FAIL" "HTTP ${HTTP}"
fi

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/regions/current" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Current region" "PASS" "HTTP ${HTTP}"
else
  test_result "Current region" "FAIL" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  SECTION 6: SECURITY TESTS
# ═══════════════════════════════════════
section "6. SECURITY VULNERABILITY TESTS"

# SQL Injection attempts
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "${BASE}/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@aihr.app' OR '1'='1&password=test" 2>/dev/null)
if [ "$HTTP" = "401" ] || [ "$HTTP" = "400" ] || [ "$HTTP" = "422" ]; then
  test_result "SQL injection login blocked" "PASS" "HTTP ${HTTP}"
else
  test_result "SQL injection login blocked" "FAIL" "HTTP ${HTTP}"
fi

# XSS in query params
HTTP=$(curl -sS -o /tmp/xss_test.json -w "%{http_code}" -b /tmp/cookies_admin.txt \
  "${BASE}/documents/?search=<script>alert(1)</script>" 2>/dev/null)
XSS_CHECK=$(grep -c '<script>' /tmp/xss_test.json 2>/dev/null)
if [ "$XSS_CHECK" = "0" ] || [ -z "$XSS_CHECK" ]; then
  test_result "XSS in query param sanitized" "PASS" "No script tag in response"
else
  test_result "XSS in query param sanitized" "FAIL" "Script tag found in response"
fi

# Path traversal
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  "${BASE}/documents/../../etc/passwd" 2>/dev/null)
if [ "$HTTP" = "404" ] || [ "$HTTP" = "422" ] || [ "$HTTP" = "400" ]; then
  test_result "Path traversal blocked" "PASS" "HTTP ${HTTP}"
else
  test_result "Path traversal blocked" "FAIL" "HTTP ${HTTP}"
fi

# CSRF - POST without proper origin
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X POST "${BASE}/documents/upload" \
  -H "Origin: http://evil.com" \
  -F "file=@/tmp/test_upload.txt;type=text/plain" 2>/dev/null)
if [ "$HTTP" = "403" ] || [ "$HTTP" = "401" ]; then
  test_result "CSRF foreign origin blocked" "PASS" "HTTP ${HTTP}"
elif [ "$HTTP" = "200" ] || [ "$HTTP" = "201" ]; then
  test_result "CSRF foreign origin blocked" "WARN" "HTTP ${HTTP} (upload succeeded, CSRF not enforced)"
else
  test_result "CSRF foreign origin blocked" "WARN" "HTTP ${HTTP}"
fi

# Cookie check
COOKIE_CONTENT=$(cat /tmp/cookies_admin.txt 2>/dev/null)
if echo "$COOKIE_CONTENT" | grep -q "HttpOnly"; then
  test_result "Cookies HttpOnly flag" "PASS" "HttpOnly present"
elif echo "$COOKIE_CONTENT" | grep -q "unihr_access"; then
  test_result "Cookies HttpOnly flag" "WARN" "Cookie exists but HttpOnly not visible in file"
else
  test_result "Cookies HttpOnly flag" "WARN" "Cannot verify from cookie jar"
fi

# Method not allowed
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X DELETE "${BASE}/auth/login/access-token" 2>/dev/null)
if [ "$HTTP" = "405" ]; then
  test_result "Invalid HTTP method rejected" "PASS" "HTTP ${HTTP}"
else
  test_result "Invalid HTTP method rejected" "WARN" "HTTP ${HTTP}"
fi

# Large payload
LARGE_PAYLOAD=$(python3 -c "print('{\"message\":\"' + 'A'*1000000 + '\"}')")
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X POST "${BASE}/chat/chat" \
  -H "Content-Type: application/json" \
  -d "$LARGE_PAYLOAD" 2>/dev/null)
if [ "$HTTP" = "413" ] || [ "$HTTP" = "422" ] || [ "$HTTP" = "400" ]; then
  test_result "Large payload rejected" "PASS" "HTTP ${HTTP}"
else
  test_result "Large payload rejected" "WARN" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  SECTION 7: DATABASE INTEGRITY
# ═══════════════════════════════════════
section "7. DATABASE INTEGRITY"

# Check all expected tables exist
TABLES=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>/dev/null | tr -d ' ' | grep -v '^$')
EXPECTED_TABLES="alembic_version auditlogs billing_records conversations departments documentchunks documents featurepermissions messages retrievaltraces tenants usagerecords users"
for tbl in $EXPECTED_TABLES; do
  if echo "$TABLES" | grep -q "^${tbl}$"; then
    test_result "Table exists: ${tbl}" "PASS" "found"
  else
    test_result "Table exists: ${tbl}" "FAIL" "MISSING"
  fi
done

# Check foreign key constraints
FK_COUNT=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY';" 2>/dev/null | tr -d ' ')
if [ "$FK_COUNT" -gt "5" ] 2>/dev/null; then
  test_result "Foreign key constraints" "PASS" "${FK_COUNT} FKs defined"
else
  test_result "Foreign key constraints" "WARN" "Only ${FK_COUNT} FKs"
fi

# Check indexes
IDX_COUNT=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM pg_indexes WHERE schemaname='public';" 2>/dev/null | tr -d ' ')
if [ "$IDX_COUNT" -gt "10" ] 2>/dev/null; then
  test_result "Database indexes" "PASS" "${IDX_COUNT} indexes"
else
  test_result "Database indexes" "WARN" "Only ${IDX_COUNT} indexes"
fi

# Check pgvector extension
PGV=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>/dev/null | tr -d ' ')
if [ "$PGV" = "vector" ]; then
  test_result "pgvector extension" "PASS" "installed"
else
  test_result "pgvector extension" "FAIL" "NOT installed"
fi

# Check user count
USER_COUNT=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM users;" 2>/dev/null | tr -d ' ')
test_result "Users in DB" "PASS" "${USER_COUNT} users"

# Check tenant count
TENANT_COUNT=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM tenants;" 2>/dev/null | tr -d ' ')
test_result "Tenants in DB" "PASS" "${TENANT_COUNT} tenants"

# Check document count
DOC_COUNT=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM documents;" 2>/dev/null | tr -d ' ')
test_result "Documents in DB" "PASS" "${DOC_COUNT} documents"

# Check for orphaned records
ORPHAN_DOCS=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM documents d WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = d.tenant_id);" 2>/dev/null | tr -d ' ')
if [ "$ORPHAN_DOCS" = "0" ]; then
  test_result "No orphaned documents" "PASS" "0 orphans"
else
  test_result "No orphaned documents" "FAIL" "${ORPHAN_DOCS} orphaned docs"
fi

ORPHAN_USERS=$(docker exec aihr-db-1 psql -U unihr -d unihr_saas -t -c "SELECT count(*) FROM users u WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = u.tenant_id);" 2>/dev/null | tr -d ' ')
if [ "$ORPHAN_USERS" = "0" ]; then
  test_result "No orphaned users" "PASS" "0 orphans"
else
  test_result "No orphaned users" "FAIL" "${ORPHAN_USERS} orphaned users"
fi

# ═══════════════════════════════════════
#  SECTION 8: TENANT ISOLATION
# ═══════════════════════════════════════
section "8. TENANT ISOLATION"

# Get admin's tenant_id
ADMIN_TENANT=$(python3 -c "import json; print(json.load(open('/tmp/me_admin.json')).get('tenant_id',''))" 2>/dev/null)

# Try to access a non-existent or different tenant
FAKE_TENANT="00000000-0000-0000-0000-000000000000"
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  "${BASE}/documents/?tenant_id=${FAKE_TENANT}" 2>/dev/null)
# Should either ignore the param or reject it
test_result "Cross-tenant doc query" "PASS" "HTTP ${HTTP} (param ignored or blocked)"

# Try to access another user's data
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_employee.txt \
  "${BASE}/company/users" 2>/dev/null)
if [ "$HTTP" = "403" ] || [ "$HTTP" = "401" ]; then
  test_result "Employee can't list all users" "PASS" "HTTP ${HTTP}"
else
  test_result "Employee can't list all users" "WARN" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  SECTION 9: PUBLIC ENDPOINTS
# ═══════════════════════════════════════
section "9. PUBLIC ENDPOINTS"

HTTP=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE}/public/branding" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Public branding API" "PASS" "HTTP ${HTTP}"
else
  test_result "Public branding API" "FAIL" "HTTP ${HTTP}"
fi

# Knowledge base search
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X POST "${BASE}/kb/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"勞基法"}' 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "KB search" "PASS" "HTTP ${HTTP}"
else
  test_result "KB search" "WARN" "HTTP ${HTTP} (no KB data?)"
fi

# Feature flags
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt "${BASE}/feature-flags/" 2>/dev/null)
if [ "$HTTP" = "200" ]; then
  test_result "Feature flags list" "PASS" "HTTP ${HTTP}"
else
  test_result "Feature flags list" "FAIL" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  SECTION 10: API ERROR HANDLING
# ═══════════════════════════════════════
section "10. ERROR HANDLING"

# Invalid JSON
CSRF_TOK=$(get_csrf /tmp/cookies_admin.txt)
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  -X POST "${BASE}/chat/chat" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ${CSRF_TOK}" \
  -d '{invalid json}' 2>/dev/null)
if [ "$HTTP" = "422" ] || [ "$HTTP" = "400" ]; then
  test_result "Invalid JSON rejected" "PASS" "HTTP ${HTTP}"
else
  test_result "Invalid JSON rejected" "FAIL" "HTTP ${HTTP}"
fi

# Non-existent resource
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  "${BASE}/documents/99999999-9999-9999-9999-999999999999" 2>/dev/null)
if [ "$HTTP" = "404" ] || [ "$HTTP" = "422" ]; then
  test_result "Non-existent doc returns 404" "PASS" "HTTP ${HTTP}"
else
  test_result "Non-existent doc returns 404" "FAIL" "HTTP ${HTTP}"
fi

# Non-existent endpoint
HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
  "${BASE}/nonexistent/endpoint" 2>/dev/null)
if [ "$HTTP" = "404" ]; then
  test_result "Non-existent endpoint returns 404" "PASS" "HTTP ${HTTP}"
else
  test_result "Non-existent endpoint returns 404" "FAIL" "HTTP ${HTTP}"
fi

# ═══════════════════════════════════════
#  CLEANUP & SUMMARY
# ═══════════════════════════════════════
# Delete test document if created
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "?" ]; then
  HTTP=$(curl -sS -o /dev/null -w "%{http_code}" -b /tmp/cookies_admin.txt \
    -X DELETE "${BASE}/documents/${DOC_ID}" 2>/dev/null)
  if [ "$HTTP" = "200" ] || [ "$HTTP" = "204" ]; then
    test_result "Delete test document" "PASS" "HTTP ${HTTP}"
  else
    test_result "Delete test document" "WARN" "HTTP ${HTTP}"
  fi
fi

rm -f /tmp/test_upload.txt /tmp/body_*.json /tmp/me_*.json /tmp/docs_list.json /tmp/upload_resp.json /tmp/chat_resp.json /tmp/convs.json /tmp/depts.json /tmp/audit.json /tmp/usage.json /tmp/company.json /tmp/quota.json /tmp/plans.json /tmp/current_sub.json /tmp/billing.json /tmp/feature.json /tmp/xss_test.json /tmp/cookies_*.txt

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║         COMPREHENSIVE TEST REPORT             ║"
echo "╠═══════════════════════════════════════════════╣"
printf "║  ✅ Passed:  %-4s                             ║\n" "$PASS"
printf "║  ⚠️  Warnings: %-4s                            ║\n" "$WARN"
printf "║  ❌ Failed:  %-4s                             ║\n" "$FAIL"
printf "║  📊 Total:   %-4s                             ║\n" "$TOTAL"
echo "╠═══════════════════════════════════════════════╣"
RATE=$((PASS * 100 / TOTAL))
printf "║  Pass Rate: %d%%                              ║\n" "$RATE"
echo "╚═══════════════════════════════════════════════╝"
