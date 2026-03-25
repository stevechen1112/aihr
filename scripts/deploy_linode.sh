#!/bin/bash
# ========================================================
# UniHR SaaS ??Linode å¿«é€Ÿéƒ¨ç½²è…³??# ========================================================
# IP: 172.237.11.179
# ä½¿ç”¨ sslip.io ?¨æ?ç¶²å?
# ========================================================

set -e  # ?‡åˆ°?¯èª¤ç«‹å³?œæ­¢

echo "========================================="
echo "UniHR SaaS - Linode ?¨ç½²?‹å?"
echo "========================================="

# é¡è‰²å®šç¾©
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. æª¢æŸ¥å¿…è?å·¥å…·
echo -e "${YELLOW}[1/8] æª¢æŸ¥å¿…è?å·¥å…·...${NC}"
for cmd in docker git python3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}?¯èª¤: $cmd ?ªå?è£?{NC}"
        exit 1
    fi
done
echo -e "${GREEN}??å¿…è?å·¥å…·å·²å?è£?{NC}"

# 2. Clone ?–æ›´?°å?æ¡?echo -e "${YELLOW}[2/8] ä¸‹è?å°ˆæ?...${NC}"
if [ -d "/opt/aihr" ]; then
    echo "å°ˆæ?å·²å??¨ï??´æ–°ä¸?.."
    cd /opt/aihr
    git pull
else
    echo "Clone å°ˆæ?..."
    cd /opt
    git clone https://github.com/stevechen1112/aihr.git
    cd /opt/aihr
fi
echo -e "${GREEN}??å°ˆæ?å·²æ???{NC}"

# 3. ?Ÿæ??°å??ç½®
echo -e "${YELLOW}[3/8] ?Ÿæ??°å??ç½®...${NC}"
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}è­¦å?: .env.production å·²å??¨ï??™ä»½??.env.production.backup${NC}"
    cp .env.production .env.production.backup
fi

python3 scripts/generate_secrets.py --output .env.production
echo -e "${GREEN}???°å??ç½®å·²ç???{NC}"

# 4. ?´æ–° .env.production ä½¿ç”¨ sslip.io ç¶²å?
echo -e "${YELLOW}[4/8] ?ç½® sslip.io ç¶²å?...${NC}"
IP="172.237.11.179"
DOMAIN="172-237-11-179.sslip.io"

# ?´æ–° CORS
sed -i "s|BACKEND_CORS_ORIGINS=.*|BACKEND_CORS_ORIGINS=http://app.${DOMAIN},http://admin.${DOMAIN}|g" .env.production

# æ·»å? Frontend URLsï¼ˆå??œä?å­˜åœ¨ï¼?if ! grep -q "FRONTEND_URL=" .env.production; then
    echo "FRONTEND_URL=http://app.${DOMAIN}" >> .env.production
fi
if ! grep -q "ADMIN_FRONTEND_URL=" .env.production; then
    echo "ADMIN_FRONTEND_URL=http://admin.${DOMAIN}" >> .env.production
fi

echo -e "${GREEN}??ç¶²å??ç½®å®Œæ?${NC}"
echo -e "${YELLOW}ä½¿ç”¨ç¶²å?:${NC}"
echo -e "  - ä½¿ç”¨?…ä??? http://app.${DOMAIN}"
echo -e "  - ç³»çµ±?¹ä??? http://admin.${DOMAIN}"
echo -e "  - API: http://api.${DOMAIN}"
echo -e "  - ºÊ±±­¶­±: http://ºÊ±±­¶­±.${DOMAIN}"

# 5. ?‹å??ç½®?ç¤º
echo -e "${YELLOW}[5/8] è«‹æ??•é?ç½®ä»¥ä¸‹å?å¡«é???..${NC}"
echo -e "${RED}è«‹ä½¿?¨ç·¨è¼¯å™¨?“é? .env.production ä¸¦å¡«?¥ï?${NC}"
echo "  1. OPENAI_API_KEY"
echo "  2. VOYAGE_API_KEY"
echo "  3. LLAMAPARSE_API_KEY (å¦‚æ?ä½¿ç”¨)"
echo "  4. FIRST_SUPERUSER_EMAIL"
echo "  5. FIRST_SUPERUSER_PASSWORD"
echo ""
echo -e "${YELLOW}??Enter ç¹¼ç?ï¼ˆå??ç·¨è¼¯å?ï¼?..${NC}"
read

# 6. ?ç½® Gatewayï¼ˆä½¿??sslip.io ?ˆæœ¬ï¼?echo -e "${YELLOW}[6/8] ?ç½® Nginx Gateway...${NC}"
if [ -f "nginx/gateway.conf.sslip" ]; then
    cp nginx/gateway.conf.sslip nginx/gateway.conf.active
    echo -e "${GREEN}??Gateway ?ç½®å·²æ›´?°ï?HTTP æ¨¡å?ï¼ŒSSL å¾…é?ç½®ï?${NC}"
else
    echo -e "${YELLOW}è­¦å?: nginx/gateway.conf.sslip ä¸å??¨ï?ä½¿ç”¨?è¨­ gateway.conf${NC}"
    cp nginx/gateway.conf nginx/gateway.conf.active
fi

# 7. ?Ÿå??å?
echo -e "${YELLOW}[7/8] ?Ÿå? Docker ?å?...${NC}"
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

echo "ç­‰å??å??Ÿå?..."
sleep 15

# æª¢æŸ¥?å??€??docker compose -f docker-compose.prod.yml ps

# 8. ?å??–è??™åº«
echo -e "${YELLOW}[8/8] ?å??–è??™åº«...${NC}"
echo "?·è?è³‡æ?åº«é·ç§?.."
docker compose -f docker-compose.prod.yml exec -T web alembic upgrade head

echo "?µå»º?å?ç§Ÿæˆ¶?‡è?ç´šç®¡?†å“¡..."
docker compose -f docker-compose.prod.yml exec -T web python scripts/initial_data.py

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}???¨ç½²å®Œæ?ï¼?{NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}å­˜å?ç¶²å?ï¼ˆHTTPï¼‰ï?${NC}"
echo -e "  ä½¿ç”¨?…ä??? http://app.${DOMAIN}"
echo -e "  ç³»çµ±?¹ä??? http://admin.${DOMAIN}"
echo -e "  API ?‡ä»¶: http://api.${DOMAIN}/docs"
echo -e "  ºÊ±±­¶­±: http://ºÊ±±­¶­±.${DOMAIN}"
echo ""
echo -e "${YELLOW}ä¸‹ä?æ­¥ï??¯é¸ï¼‰ï?${NC}"
echo "  1. ?ç½® SSL ?‘è?ï¼ˆCertbot + Let's Encryptï¼?
echo "     è©³è?ï¼šdocs/LINODE_DEPLOYMENT.md Â§ 7"
echo "  2. IP ?½å??®ç®¡?†ä??¢ï?å»ºè­°?Ÿç”¨ï¼?
echo "  3. è¨­å??ªå??™ä»½ï¼ˆscripts/backup.shï¼?
echo ""
echo -e "${YELLOW}?¥ç??¥è?ï¼?{NC}"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo -e "${YELLOW}å¸¸ç”¨?‡ä»¤ï¼?{NC}"
echo "  ?å??å?: docker compose -f docker-compose.prod.yml restart"
echo "  ?œæ­¢?å?: docker compose -f docker-compose.prod.yml stop"
echo "  ?¥ç??€?? docker compose -f docker-compose.prod.yml ps"
echo ""
echo -e "${GREEN}?¨ç½²å®Œæ?ï¼?{NC}"
