# Linode å¿«é€Ÿéƒ¨ç½????½ä»¤??

## ä¼ºæ??¨è?è¨?
- IP: `172.237.11.179`
- SSH: `ssh root@172.237.11.179`
- ç¶²å?: ä½¿ç”¨ `sslip.io` (ä¾? `app.172-237-11-179.sslip.io`)

---

## ä¸€?µéƒ¨ç½²ï??¨è–¦ï¼?

```bash
# SSH ?»å…¥ Linode
ssh root@172.237.11.179

# ?·è??¨ç½²?³æœ¬
cd /opt
git clone https://github.com/stevechen1112/aihr.git
cd aihr
bash scripts/deploy_linode.sh
```

?³æœ¬?ƒè‡ª?•ï?
1. ??æª¢æŸ¥å¿…è?å·¥å…·ï¼ˆDocker, Git, Pythonï¼?
2. ??Clone/?´æ–°å°ˆæ?
3. ???Ÿæ??°å??ç½®ï¼?env.productionï¼?
4. ???ç½® sslip.io ç¶²å?
5. ???Ÿå? Docker ?å?
6. ???å??–è??™åº«

**?€è¦æ??•å¡«?¥ç??…ç›®**ï¼?
- `OPENAI_API_KEY`
- `VOYAGE_API_KEY`
- `LLAMAPARSE_API_KEY`
- `FIRST_SUPERUSER_EMAIL`
- `FIRST_SUPERUSER_PASSWORD`

---

## é©—è??¨ç½²

```bash
# ?·è?é©—è??³æœ¬
bash scripts/verify_deployment.sh
```

é©—è??…ç›®ï¼?
- Docker ?å??€??
- API ?¥åº·æª¢æŸ¥
- ?ç«¯ä»‹é¢å­˜å?
- DNS è§??
- è³‡æ?åº«é€??

---

## å­˜å?ç¶²å?ï¼ˆå?æ¬¡éƒ¨ç½?HTTPï¼?

| ?å? | ç¶²å? |
|-----|-----|
| ä½¿ç”¨?…ä???| http://app.172-237-11-179.sslip.io |
| ç³»çµ±?¹ä???| http://admin.172-237-11-179.sslip.io |
| API ?‡ä»¶ | http://api.172-237-11-179.sslip.io/docs |
| ºÊ±±­¶­± | http://ºÊ±±­¶­±.172-237-11-179.sslip.io |

---

## ?‹å??¨ç½²æ­¥é?ï¼ˆè©³ç´°ç?ï¼?

### 1. ä¼ºæ??¨å?å§‹å?

```bash
# SSH ?»å…¥
ssh root@172.237.11.179

# ?´æ–°ç³»çµ±
apt update && apt upgrade -y

# å®‰è?å¿…è?å·¥å…·
apt install -y curl git vim ufw

# è¨­å??‚å?
timedatectl set-timezone Asia/Taipei
```

### 2. å®‰è? Docker

```bash
# å®‰è? Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# ?Ÿç”¨?å?
systemctl enable docker
systemctl start docker

# é©—è?
docker --version
docker compose version
```

### 3. è¨­å??²ç«??

```bash
# ?è¨±å¿…è?ç«¯å£
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS

# ?Ÿç”¨?²ç«??
ufw --force enable

# æª¢æŸ¥?€??
ufw status
```

### 4. Clone å°ˆæ?

```bash
cd /opt
git clone https://github.com/stevechen1112/aihr.git
cd aihr
```

### 5. ?Ÿæ??°å??ç½®

```bash
# ?Ÿæ?å¯†é‘°?‡å?ç¢?
python3 scripts/generate_secrets.py --output .env.production

# ç·¨è¼¯?ç½®æª?
vim .env.production
```

**å¿…å¡«?…ç›®**ï¼?
```bash
# API Keys
OPENAI_API_KEY=sk-proj-...
VOYAGE_API_KEY=pa-...
LLAMAPARSE_API_KEY=llx-...

# è¶…ç?ç®¡ç???
FIRST_SUPERUSER_EMAIL=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=<å¼·éš¨æ©Ÿå?ç¢?

# ç¶²å??ç½®ï¼ˆsslip.ioï¼?
BACKEND_CORS_ORIGINS=http://app.172-237-11-179.sslip.io,http://admin.172-237-11-179.sslip.io
FRONTEND_URL=http://app.172-237-11-179.sslip.io
ADMIN_FRONTEND_URL=http://admin.172-237-11-179.sslip.io
```

### 6. ?ç½® Gateway (ä½¿ç”¨ sslip.io)

```bash
# ä½¿ç”¨ sslip.io ?ˆæœ¬??gateway ?ç½®
cp nginx/gateway.conf.sslip nginx/gateway.conf

# ?–è€…ç›´?¥åœ¨ docker-compose.prod.yml ä¸­ä¿®??volumes:
# - ./nginx/gateway.conf.sslip:/etc/nginx/conf.d/default.conf:ro
```

### 7. ?Ÿå??å?

```bash
# ?Ÿå??€?‰æ???
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# ?¥ç??€??
docker compose -f docker-compose.prod.yml ps

# ?¥ç??¥è?
docker compose -f docker-compose.prod.yml logs -f
```

### 8. ?å??–è??™åº«

```bash
# ?·è?è³‡æ?åº«é·ç§?
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# ?µå»º?å?ç§Ÿæˆ¶?‡è?ç´šç®¡?†å“¡
docker compose -f docker-compose.prod.yml exec web python scripts/initial_data.py
```

---

## ?ç½® SSLï¼ˆè? HTTP è®Šæ? HTTPSï¼?

### 1. ?œæ­¢ Gatewayï¼ˆè? Certbot ä½¿ç”¨ 80 portï¼?

```bash
docker compose -f docker-compose.prod.yml stop gateway
```

### 2. å®‰è? Certbot

```bash
apt install -y certbot python3-certbot-nginx
```

### 3. ?–å??‘è?ï¼ˆä?æ¬¡ç”³è«‹å??‹ç¶²?Ÿï?

```bash
certbot certonly --standalone \
  -d app.172-237-11-179.sslip.io \
  -d admin.172-237-11-179.sslip.io \
  -d api.172-237-11-179.sslip.io \
  -d admin-api.172-237-11-179.sslip.io \
  -d ºÊ±±­¶­±.172-237-11-179.sslip.io \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

?‘è?ä½ç½®ï¼?
- `/etc/letsencrypt/live/app.172-237-11-179.sslip.io/fullchain.pem`
- `/etc/letsencrypt/live/app.172-237-11-179.sslip.io/privkey.pem`

### 4. ?Ÿç”¨ HTTPSï¼ˆç·¨è¼?gateway.confï¼?

ç·¨è¼¯ `nginx/gateway.conf.sslip`ï¼Œå?æ¶ˆæ???SSL ?¸é?è¨»è§£ï¼?

```nginx
# å°‡æ???server ??listen ?¹ç‚ºï¼?
listen 443 ssl http2;
ssl_certificate     /etc/letsencrypt/live/app.172-237-11-179.sslip.io/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/app.172-237-11-179.sslip.io/privkey.pem;
ssl_protocols       TLSv1.2 TLSv1.3;
ssl_ciphers         HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;

# ?Ÿç”¨åº•éƒ¨??HTTP ??HTTPS redirect
```

### 5. ?å? Gateway

```bash
docker compose -f docker-compose.prod.yml up -d gateway
```

### 6. è¨­å??ªå?çºŒæ?

```bash
# æ¸¬è©¦çºŒæ?
certbot renew --dry-run

# ? å…¥ cronï¼ˆæ?å¤©å???3 é»æª¢?¥ï?
echo "0 3 * * * certbot renew --quiet && docker compose -f /opt/aihr/docker-compose.prod.yml restart gateway" | crontab -
```

---

## å¸¸ç”¨?‡ä»¤

### ?¥ç??¥è?
```bash
# ?€?‰æ???
docker compose -f docker-compose.prod.yml logs -f

# ?¹å??å?
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f gateway
```

### ?å??å?
```bash
# ?å??¹å??å?
docker compose -f docker-compose.prod.yml restart web

# ?å??€?‰æ???
docker compose -f docker-compose.prod.yml restart
```

### ?´æ–°ç¨‹å?ç¢?
```bash
cd /opt/aihr
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### ?™ä»½è³‡æ?åº?
```bash
# ?‹å??™ä»½
bash scripts/backup.sh

# è¨­å?æ¯æ—¥?ªå??™ä»½ï¼ˆå???2 é»ï?
echo "0 2 * * * cd /opt/aihr && bash scripts/backup.sh" | crontab -e
```

### æª¢æŸ¥?å??¥åº·?€??
```bash
# Docker ?å?
docker compose -f docker-compose.prod.yml ps

# PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a <REDIS_PASSWORD> ping
```

---

## ?‡æ??°æ­£å¼ç¶²??

?¶æ??™å¥½æ­??ç¶²å?ï¼ˆä?å¦?`yourdomain.com`ï¼‰æ?ï¼?

### 1. DNS è¨­å?
```
A     app.yourdomain.com       -> 172.237.11.179
A     admin.yourdomain.com     -> 172.237.11.179
A     api.yourdomain.com       -> 172.237.11.179
A     admin-api.yourdomain.com -> 172.237.11.179
A     ºÊ±±­¶­±.yourdomain.com   -> 172.237.11.179
A     *.yourdomain.com         -> 172.237.11.179  # wildcard
```

### 2. ?´æ–°?°å?è®Šæ•¸
ç·¨è¼¯ `.env.production`ï¼Œå…¨?Ÿæ›¿?›ï?
```bash
172-237-11-179.sslip.io ??yourdomain.com
```

### 3. ?´æ–° Nginx ?ç½®
ç·¨è¼¯ `nginx/gateway.conf`ï¼Œå…¨?Ÿæ›¿?›ï?
```bash
172-237-11-179.sslip.io ??yourdomain.com
```

### 4. ?æ–°?³è? SSL
```bash
certbot certonly --standalone \
  -d app.yourdomain.com \
  -d admin.yourdomain.com \
  -d api.yourdomain.com \
  -d admin-api.yourdomain.com \
  -d ºÊ±±­¶­±.yourdomain.com \
  --email your-email@example.com \
  --agree-tos
```

### 5. ?å??å?
```bash
docker compose -f docker-compose.prod.yml restart gateway
docker compose -f docker-compose.prod.yml restart web
```

---

## ?…é??’é™¤

### ?¡æ?å­˜å??å?
```bash
# æª¢æŸ¥?²ç«??
ufw status

# æª¢æŸ¥ Docker ?å?
docker compose -f docker-compose.prod.yml ps

# æª¢æŸ¥ Gateway ?¥è?
docker compose -f docker-compose.prod.yml logs gateway
```

### SSL ?‘è??–å?å¤±æ?
- ç¢ºè? 80 port ?ªè¢«ä½”ç”¨ï¼ˆGateway ?€?«å?ï¼?
- ç¢ºè? DNS å·²æ­£ç¢ºè§£?ï?`dig app.172-237-11-179.sslip.io`
- æª¢æŸ¥?²ç«?†æ˜¯?¦å?è¨?80 port

### è³‡æ?åº«é€???¯èª¤
```bash
# æª¢æŸ¥ PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# æª¢æŸ¥å¯†ç¢¼
grep POSTGRES_PASSWORD .env.production
```

### Worker ä»»å?ä¸åŸ·è¡?
```bash
# æª¢æŸ¥ Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a <REDIS_PASSWORD> ping

# æª¢æŸ¥ Worker ?¥è?
docker compose -f docker-compose.prod.yml logs worker

# ?å? Worker
docker compose -f docker-compose.prod.yml restart worker
```

---

## å®‰å…¨å»ºè­°

### 1. ?åˆ¶ SSH å­˜å?
```bash
# ?ªå?è¨±ç‰¹å®?IP SSH
ufw delete allow 22/tcp
ufw allow from <YOUR_IP> to any port 22
```

### 2. Admin ä»‹é¢ IP ?½å???
ç·¨è¼¯ `nginx/gateway.conf`ï¼Œåœ¨ admin server block ä¸­ï?
```nginx
# Optional: IP whitelist for admin
allow <YOUR_OFFICE_IP>;
deny all;
```

### 3. å®šæ??´æ–°ç³»çµ±
```bash
apt update && apt upgrade -y
```

### 4. ??§?°å¸¸å­˜å?
- ºÊ±±­¶­± ?¥ç? Nginx access logs
- å®šæ?æª¢æŸ¥ `docker compose logs`

---

## ?¯çµ¡?‡æ”¯??
- GitHub: https://github.com/stevechen1112/aihr
- è©³ç´°?‡ä»¶: [docs/LINODE_DEPLOYMENT.md](../docs/LINODE_DEPLOYMENT.md)
