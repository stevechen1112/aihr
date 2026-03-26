# Deploy script - rebuild frontend + backend on production
$ErrorActionPreference = "Continue"

Write-Host "=== Step 1: Check git state ==="
ssh -o BatchMode=yes -o ConnectTimeout=30 root@172.233.67.81 "cd /opt/aihr; git log --oneline -1"

Write-Host "`n=== Step 2: Build frontend (no-cache) ==="
ssh -o BatchMode=yes -o ConnectTimeout=60 -o ServerAliveInterval=30 -o ServerAliveCountMax=30 root@172.233.67.81 "cd /opt/aihr && docker compose -f docker-compose.prod.yml --env-file .env.production build --no-cache frontend 2>&1 | tail -5 && echo FRONTEND_BUILD_OK"

Write-Host "`n=== Step 3: Build backend ==="
ssh -o BatchMode=yes -o ConnectTimeout=60 -o ServerAliveInterval=30 -o ServerAliveCountMax=30 root@172.233.67.81 "cd /opt/aihr && docker compose -f docker-compose.prod.yml --env-file .env.production build web worker 2>&1 | tail -5 && echo BACKEND_BUILD_OK"

Write-Host "`n=== Step 4: Recreate containers ==="
ssh -o BatchMode=yes -o ConnectTimeout=30 -o ServerAliveInterval=30 root@172.233.67.81 "cd /opt/aihr && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --force-recreate frontend gateway web worker && echo UP_DONE"

Write-Host "`n=== Step 5: Wait and check ==="
Start-Sleep -Seconds 10
ssh -o BatchMode=yes -o ConnectTimeout=30 root@172.233.67.81 "docker ps --format 'table {{.Names}}\t{{.Status}}' && echo '---BUNDLE---' && docker exec aihr-frontend-1 ls /usr/share/nginx/html/assets/ 2>/dev/null && echo '---HEALTH---' && curl -sS http://localhost:80/health 2>/dev/null || echo 'health_check_na'"

Write-Host "`n=== DEPLOY COMPLETE ==="
