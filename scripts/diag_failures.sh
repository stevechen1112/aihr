#!/bin/bash
# Check DB tables and recent errors
echo "=== DB TABLES ==="
docker exec aihr-db-1 psql -U unihr -d unihr_saas -c "\dt public.*"

echo ""
echo "=== RECENT WEB ERRORS ==="
cd /opt/aihr
docker compose -f docker-compose.prod.yml --env-file .env.production logs --tail=200 web 2>&1 | grep -iE "error|500|traceback|exception" | tail -30

echo ""
echo "=== TOKEN REFRESH TEST ==="
# Login first
RESP=$(curl -sS -c /tmp/diag_cookies.txt \
  -X POST "http://localhost:80/api/v1/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@aihr.app&password=Admin123!" 2>&1)
echo "Login: $RESP" | head -c 200
echo ""

# Try refresh
RESP=$(curl -sS -v -b /tmp/diag_cookies.txt -c /tmp/diag_cookies.txt \
  -X POST "http://localhost:80/api/v1/auth/refresh" 2>&1)
echo "Refresh: $RESP" | head -c 500
echo ""

# Try logout
RESP=$(curl -sS -v -b /tmp/diag_cookies.txt \
  -X POST "http://localhost:80/api/v1/auth/logout" 2>&1)
echo "Logout: $RESP" | head -c 500
echo ""

# Try company/dashboard 
echo "=== COMPANY DASHBOARD ==="
RESP=$(curl -sS -b /tmp/diag_cookies.txt "http://localhost:80/api/v1/company/dashboard" 2>&1)
echo "Dashboard: $RESP" | head -c 500
echo ""

# Try doc upload
echo "=== DOC UPLOAD ==="
echo "test content" > /tmp/diag_test.txt
RESP=$(curl -sS -b /tmp/diag_cookies.txt \
  -X POST "http://localhost:80/api/v1/documents/upload" \
  -F "file=@/tmp/diag_test.txt;type=text/plain" 2>&1)
echo "Upload: $RESP" | head -c 500
echo ""

# Try billing
echo "=== BILLING ==="
RESP=$(curl -sS -b /tmp/diag_cookies.txt "http://localhost:80/api/v1/billing/" 2>&1)
echo "Billing: $RESP" | head -c 500

rm -f /tmp/diag_cookies.txt /tmp/diag_test.txt
