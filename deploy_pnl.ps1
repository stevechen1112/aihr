$ErrorActionPreference = "Continue"
$logFile = "C:\Users\User\Desktop\aihr\deploy_pnl_log.txt"
$SSH = "ssh"
$REMOTE = "root@172.233.67.81"
$SSHOPTS = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=60", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=30")

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    "$ts - $msg" | Tee-Object -FilePath $logFile -Append
}

function RemoteRun($cmd) {
    & $SSH @SSHOPTS $REMOTE $cmd 2>&1
}

Log "=== P&L Dashboard Deploy ==="

Log "Step 1: Check git state"
$r = RemoteRun "cd /opt/aihr && git log --oneline -1"
Log "Git: $r"

Log "Step 2: Build admin-frontend"
$r = RemoteRun "cd /opt/aihr && docker compose -f docker-compose.prod.yml --env-file .env.production build admin-frontend 2>&1 | tail -5 && echo ADMIN_FE_BUILD_OK"
Log "Admin-FE build: $r"

Log "Step 3: Build web + admin-api (for analytics.py changes)"
$r = RemoteRun "cd /opt/aihr && docker compose -f docker-compose.prod.yml --env-file .env.production build web admin-api 2>&1 | tail -5 && echo WEB_ADMIN_BUILD_OK"
Log "Web+Admin build: $r"

Log "Step 4: Recreate containers"
$r = RemoteRun "cd /opt/aihr && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --force-recreate admin-frontend admin-api web gateway && echo RECREATE_DONE"
Log "Recreate: $r"

Log "Step 5: Wait 15s then check"
Start-Sleep -Seconds 15
$r = RemoteRun "docker ps --format 'table {{.Names}}\t{{.Status}}'"
Log "Containers: $r"

Log "=== DEPLOY COMPLETE ==="
