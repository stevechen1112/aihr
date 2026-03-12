import urllib.request, urllib.parse, json, os, sys

BASE = os.getenv("AIHR_BASE_URL", "http://localhost:8000")
SU_EMAIL = os.getenv("AIHR_SUPERUSER_EMAIL", "admin@example.com")
SU_PASS = os.getenv("AIHR_SUPERUSER_PASS")
DEMO_EMAIL = os.getenv("AIHR_DEMO_EMAIL", "demo@example.com")
DEMO_PASS = os.getenv("AIHR_DEMO_PASS")
DEMO_NAME = os.getenv("AIHR_DEMO_NAME", "Demo User")
TENANT_KEYWORD = os.getenv("AIHR_TENANT_KEYWORD", "")

if not SU_PASS or not DEMO_PASS:
    print("ERROR: Set AIHR_SUPERUSER_PASS and AIHR_DEMO_PASS environment variables.")
    sys.exit(1)

# Superuser login
d = urllib.parse.urlencode({"username": SU_EMAIL, "password": SU_PASS}).encode()
r = urllib.request.urlopen(urllib.request.Request(
    BASE + "/api/v1/auth/login/access-token", data=d, method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=15)
su_token = json.loads(r.read())["access_token"]
print("SU login OK")

# Get tenant id
req = urllib.request.Request(BASE + "/api/v1/tenants/", headers={"Authorization": f"Bearer {su_token}"})
r = urllib.request.urlopen(req, timeout=10)
tenants = json.loads(r.read())
tlist = tenants if isinstance(tenants, list) else tenants.get("items", tenants.get("data", []))
if TENANT_KEYWORD:
    tenant = next((t for t in tlist if TENANT_KEYWORD in t.get("name", "")), None)
else:
    tenant = tlist[0] if tlist else None
if not tenant:
    print("ERROR: No matching tenant found. Set AIHR_TENANT_KEYWORD or check tenant list.")
    sys.exit(1)
print(f"Tenant: {tenant['name']} / {tenant['id']}")

# Create demo user
body = json.dumps({
    "email": DEMO_EMAIL,
    "password": DEMO_PASS,
    "full_name": DEMO_NAME,
    "tenant_id": tenant["id"],
    "role": "admin"
}).encode()
req = urllib.request.Request(
    BASE + "/api/v1/users/", data=body, method="POST",
    headers={"Authorization": f"Bearer {su_token}", "Content-Type": "application/json"})
try:
    r = urllib.request.urlopen(req, timeout=15)
    resp = json.loads(r.read())
    print(f"Created: {resp['email']} / role={resp['role']}")
except urllib.error.HTTPError as e:
    err = e.read().decode()
    if "already exists" in err:
        print("User already exists — OK")
    else:
        print(f"HTTP {e.code}: {err[:200]}")

# Verify login
d = urllib.parse.urlencode({"username": DEMO_EMAIL, "password": DEMO_PASS}).encode()
r = urllib.request.urlopen(urllib.request.Request(
    BASE + "/api/v1/auth/login/access-token", data=d, method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=15)
resp = json.loads(r.read())
print("Login test:", "OK" if resp.get("access_token") else "FAIL")
