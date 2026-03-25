# Linode ?�署?��?（無網�? / sslip.io ?��?�?

## 伺�??��?�?
- **主�?**: Linode
- **IP**: 172.237.11.179
- **SSH**: `ssh root@172.237.11.179`

## 網�??��?：sslip.io

?�於?��?沒�?�??網�?，�??�使??**sslip.io** ?��?來獲得可?��? hostname，實?�「網?��?流」�??��?

### 使用中的網域
- **使用者前台租戶站**: `https://app.172-237-11-179.sslip.io`
- **系統管理後台**: `https://admin.172-237-11-179.sslip.io`
- **後端 API**: `https://api.172-237-11-179.sslip.io`
- **Admin API**: `https://admin-api.172-237-11-179.sslip.io`
- **服務健康檢查**: `https://api.172-237-11-179.sslip.io/health`
- **租戶子網域**: `https://<tenant>.172-237-11-179.sslip.io`

### sslip.io ?��?
- `app.172-237-11-179.sslip.io` ?�自?�解?�到 `172.237.11.179`
- ?��?註�??�設�?DNS，�??�可??
- ?�援 Let's Encrypt SSL ?��?
- **?��? PoC?�測試、臨?��?線�??�正式網?��??��???*

---

## ?�署步�?

### 1. 準�? Linode VM

#### 1.1 建議規格
?��??��?�?
- **Linode 4GB**: 2 CPU / 4GB RAM / 80GB Storage
- 作業系統：Ubuntu 22.04 LTS ??24.04 LTS

#### 1.2 ?��??�伺?�器
```bash
# SSH ?�入
ssh root@172.237.11.179

# ?�新系統
apt update && apt upgrade -y

# 安�?必�?工具
apt install -y curl git vim ufw

# 設�??��?
timedatectl set-timezone Asia/Taipei
```

### 2. 安�? Docker & Docker Compose

```bash
# 安�? Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# ?�用 Docker ?��?
systemctl enable docker
systemctl start docker

# 驗�? Docker ?�本
docker --version

# Docker Compose 已內建在 Docker CLI（docker compose ?�令�?
docker compose version
```

### 3. 設�??�火??

```bash
# ?�許 SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# ?�用?�火?��?確�? SSH 已�?許�??��??��?
ufw --force enable

# 檢查?�??
ufw status
```

### 4. ?�署專�?

#### 4.1 Clone 專�?
```bash
cd /opt
git clone https://github.com/stevechen1112/aihr.git
cd aihr
```

#### 4.2 ?��??�產?��??�置
```bash
# ?��??��?密鑰?��?�?
python3 scripts/generate_secrets.py --output .env.production

# 編輯 .env.production，填?��?填�???
vim .env.production
```

#### 4.3 必填?��?變數
編輯 `.env.production`，至少填?�以下�??��?

```bash
# === ?��??�置 ===
APP_ENV=production
SECRET_KEY=<generate_secrets.py 已�???

# === 網�??�置（sslip.io�?==
BACKEND_CORS_ORIGINS=https://app.172-237-11-179.sslip.io,https://admin.172-237-11-179.sslip.io
FRONTEND_URL=https://app.172-237-11-179.sslip.io
ADMIN_FRONTEND_URL=https://admin.172-237-11-179.sslip.io

# === 資�?�?===
POSTGRES_SERVER=postgres
POSTGRES_USER=unihr
POSTGRES_PASSWORD=<generate_secrets.py 已�???
POSTGRES_DB=unihr

# === Redis ===
REDIS_HOST=redis
REDIS_PASSWORD=<generate_secrets.py 已�???
ADMIN_REDIS_PASSWORD=<generate_secrets.py 已�???

# === AI API Keys（�??�填寫�?�?key�?==
OPENAI_API_KEY=sk-proj-...
VOYAGE_API_KEY=pa-...

# === LlamaParse ===
LLAMA_CLOUD_API_KEY=llx-...

# === ?��?超�?管�???===
FIRST_SUPERUSER_EMAIL=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=<強隨機�?�?

# === �ʱ����� ===
�ʱ�����_PASSWORD=<generate_secrets.py 已�???
```

### 5. ?��??��?

```bash
# ?��??�?��??��?後台?��?�?
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# ?��??��??�??
docker compose -f docker-compose.prod.yml ps

# ?��??��?（可?��?
docker compose -f docker-compose.prod.yml logs -f web
```

### 6. ?��??��??�庫

```bash
# ?��?資�?庫遷�?
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# ?�建?��?租戶?��?級管?�員
docker compose -f docker-compose.prod.yml exec web python scripts/initial_data.py
```

### 7. 設�? SSL ?��?（Let's Encrypt�?

#### 7.1 安�? Certbot
```bash
apt install -y certbot python3-certbot-nginx
```

#### 7.2 ?�用 Gateway 以便?��??��?（HTTP-01 ?�戰�?
```bash
docker compose -f docker-compose.prod.yml stop gateway
```

#### 7.3 ?��??��?（�?網�?一次申請�?
```bash
certbot certonly --standalone \
  -d app.172-237-11-179.sslip.io \
  -d admin.172-237-11-179.sslip.io \
  -d api.172-237-11-179.sslip.io \
  -d admin-api.172-237-11-179.sslip.io \
  -d �ʱ�����.172-237-11-179.sslip.io \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

?��??��??�在�?
- `/etc/letsencrypt/live/app.172-237-11-179.sslip.io/fullchain.pem`
- `/etc/letsencrypt/live/app.172-237-11-179.sslip.io/privkey.pem`

#### 7.4 ?�新 gateway.conf 使用 SSL
編輯 `nginx/gateway.conf`，在每�?`server` block 中�??��?

```nginx
listen 443 ssl http2;
ssl_certificate /etc/letsencrypt/live/app.172-237-11-179.sslip.io/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/app.172-237-11-179.sslip.io/privkey.pem;

# SSL ?��?
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
```

#### 7.5 ?��??��???Gateway 容器
編輯 `docker-compose.prod.yml`，在 `gateway` ?��?中�??��?

```yaml
gateway:
  volumes:
    - ./nginx/gateway.conf:/etc/nginx/conf.d/default.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro  # ?��??��??��?
```

#### 7.6 ?��? Gateway
```bash
docker compose -f docker-compose.prod.yml up -d gateway
```

#### 7.7 設�??��?續�?
```bash
# 測試續�?
certbot renew --dry-run

# ?�入 cron（�?天�???3 點檢?��?
echo "0 3 * * * certbot renew --quiet && docker compose -f /opt/aihr/docker-compose.prod.yml restart gateway" | crontab -
```

---

## 驗�??�署

### 1. 檢查?��??�康?�??
```bash
docker compose -f docker-compose.prod.yml ps
```
?�?��??��?顯示 `Up (healthy)`??

### 2. 測試?�個�???

```bash
# API ?�康檢查
curl https://api.172-237-11-179.sslip.io/health

# 使用?��???
curl -I https://app.172-237-11-179.sslip.io

# 系統?��???
curl -I https://admin.172-237-11-179.sslip.io

# �ʱ�����
curl -I https://�ʱ�����.172-237-11-179.sslip.io
```

### 3. ?�覽?�測�?
- **使用?��???*: https://app.172-237-11-179.sslip.io
- **系統?��???*: https://admin.172-237-11-179.sslip.io
- **�ʱ�����**: https://�ʱ�����.172-237-11-179.sslip.io
  - ?�設帳�?: `admin`
  - 密碼: `.env.production` 中�? `�ʱ�����_PASSWORD`

---

## ?�常維�?

### ?��??��?
```bash
# ?�?��???
docker compose -f docker-compose.prod.yml logs -f

# ?��??��?
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f gateway
```

### ?��??��?
```bash
# ?��??��??��?
docker compose -f docker-compose.prod.yml restart web

# ?��??�?��???
docker compose -f docker-compose.prod.yml restart
```

### ?�新程�?�?
```bash
cd /opt/aihr
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### ?�份資�?�?
```bash
# ?��??�份
bash scripts/backup.sh

# 設�?每日?��??�份（�???2 點�?
echo "0 2 * * * cd /opt/aihr && bash scripts/backup.sh" | crontab -e
```

---

## ?��??�正式網??

?��?準�?好正式網?��?例�? `yourdomain.com`）�?�?

### 1. DNS 設�?
?��???DNS ?��??�設定�?
```
A     app.yourdomain.com       -> 172.237.11.179
A     admin.yourdomain.com     -> 172.237.11.179
A     api.yourdomain.com       -> 172.237.11.179
A     admin-api.yourdomain.com -> 172.237.11.179
A     �ʱ�����.yourdomain.com   -> 172.237.11.179
A     *.yourdomain.com         -> 172.237.11.179  # wildcard for tenants
```

### 2. ?�新?��?變數
編輯 `.env.production`，�??�??`172-237-11-179.sslip.io` ?�為 `yourdomain.com`??

### 3. ?�新?��? SSL
```bash
certbot certonly --standalone \
  -d app.yourdomain.com \
  -d admin.yourdomain.com \
  -d api.yourdomain.com \
  -d admin-api.yourdomain.com \
  -d �ʱ�����.yourdomain.com \
  --email your-email@example.com \
  --agree-tos
```

### 4. ?�新 Nginx ?�置
編輯 `nginx/gateway.conf`，�??�??`server_name` �?`*.172-237-11-179.sslip.io` ?�為 `*.yourdomain.com`??

### 5. ?��??��?
```bash
docker compose -f docker-compose.prod.yml restart gateway
docker compose -f docker-compose.prod.yml restart web
```

---

## ?��??�除

### ?��? 1: ?��?存�??��?
```bash
# 檢查?�火??
ufw status

# 檢查 Docker ?��?
docker compose -f docker-compose.prod.yml ps

# 檢查 Gateway ?��?
docker compose -f docker-compose.prod.yml logs gateway
```

### ?��? 2: SSL ?��??��?失�?
- 確�? 80 port ?�被佔用（Gateway ?�?��?�?
- 確�? DNS 已正確解?��?`dig app.172-237-11-179.sslip.io` ?��???`172.237.11.179`�?
- 檢查?�火?�是?��?�?80 port

### ?��? 3: 資�?庫�???�誤
```bash
# 檢查 PostgreSQL ?�否�?��
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# 檢查密碼?�否�?��
grep POSTGRES_PASSWORD .env.production
```

### ?��? 4: Worker 任�?不執�?
```bash
# 檢查 Redis ???
docker compose -f docker-compose.prod.yml exec redis redis-cli -a <REDIS_PASSWORD> ping

# 檢查 Worker ?��?
docker compose -f docker-compose.prod.yml logs worker

# ?��? Worker
docker compose -f docker-compose.prod.yml restart worker
```

---

## ?�能調校（可?��?

### Linode 建議規格演�?
- **測試/小�?�?*: Linode 4GB (2 CPU / 4GB RAM)
- **中�?規模**: Linode 8GB (4 CPU / 8GB RAM)
- **大�?�?*: Linode 16GB (6 CPU / 16GB RAM) + ?�離資�?�?

### ?�慮使用 Linode 託管?��?
- **資�?�?*: Linode Managed Database (PostgreSQL)
- **?�件?��?**: Linode Object Storage（替�?��??uploads volume�?
- **負�?平衡**: Linode NodeBalancer（�??�用?��?�?

---

## 安全建議

1. **?�制 SSH 存�?**
   ```bash
   # ?��?許特�?IP SSH（�?如辦?�室 IP�?
   ufw delete allow 22/tcp
   ufw allow from <YOUR_IP> to any port 22
   ```

2. **定�??�新系統**
   ```bash
   apt update && apt upgrade -y
   ```

3. **??��?�常存�?**
   - �ʱ����� ?��? Nginx access logs
   - 定�?檢查 `docker compose logs`

4. **資�?庫�?份異?��???*
   - 將�?份�??�至 Linode Object Storage ?�其他雲端儲�?

---

## ?�絡?�支??
- GitHub: https://github.com/stevechen1112/aihr
- Issues: ??GitHub ?�交?��??��??�建�?
