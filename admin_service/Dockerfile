# ===========================================================================
# UniHR Admin Service Dockerfile（T4-18）
# ===========================================================================
# 獨立 Admin API 微服務 — 只含管理端 API，不含前端

FROM python:3.11-slim AS builder

WORKDIR /app

# 系統依賴
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Production stage ---
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system app && \
    adduser --system --ingroup app app

COPY --from=builder /install /usr/local

# 複製應用程式碼（需要 app/ 和 admin_service/）
COPY app/ ./app/
COPY admin_service/ ./admin_service/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN chown -R app:app /app
USER app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "admin_service.main:app", \
     "--host", "0.0.0.0", "--port", "8001", \
     "--workers", "2", "--access-log"]
