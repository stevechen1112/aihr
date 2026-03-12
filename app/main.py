from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.api import api_router
from app.api.v2.api import api_v2_router
from app.middleware.versioning import APIVersionMiddleware, API_VERSIONS
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.ip_whitelist import AdminIPWhitelistMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.metrics import PrometheusMiddleware, metrics_endpoint, set_app_info
from app.middleware.custom_domain import CustomDomainMiddleware
from app.logging_config import setup_logging
import logging

# ── Initialize structured logging ──
setup_logging()
logger = logging.getLogger(__name__)


def _ensure_pinecone_index():
    """
    啟動時確認 Pinecone 索引存在，若不存在則自動建立。
    絕對不會修改或刪除任何現有索引。
    """
    api_key = getattr(settings, "PINECONE_API_KEY", "")
    index_name = getattr(settings, "PINECONE_INDEX_NAME", "aihr-vectors")
    dimension = getattr(settings, "EMBEDDING_DIMENSION", 1024)
    if not api_key:
        logger.warning("PINECONE_API_KEY 未設定，跳過索引檢查")
        return
    try:
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=api_key)
        existing = [idx.name for idx in pc.list_indexes()]
        if index_name in existing:
            logger.info(f"Pinecone 索引 '{index_name}' 已存在，跳過建立")
        else:
            logger.info(f"Pinecone 索引 '{index_name}' 不存在，自動建立（dimension={dimension}）")
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Pinecone 索引 '{index_name}' 建立成功")
    except Exception as e:
        logger.warning(f"Pinecone 索引檢查/建立失敗（不影響啟動）: {e}")


def _ensure_r2_bucket():
    """
    啟動時確認 R2 bucket 存在，若不存在則自動建立。
    絕對不會修改或刪除任何現有 bucket。
    """
    endpoint = getattr(settings, "R2_ENDPOINT", "")
    access_key = getattr(settings, "R2_ACCESS_KEY_ID", "")
    secret_key = getattr(settings, "R2_SECRET_ACCESS_KEY", "")
    bucket = getattr(settings, "R2_BUCKET", "aihr-uploads")
    if not all([endpoint, access_key, secret_key]):
        logger.warning("R2 憑證未完整設定，跳過 bucket 檢查")
        return
    try:
        import boto3
        from botocore.exceptions import ClientError
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
        if bucket in existing:
            logger.info(f"R2 bucket '{bucket}' 已存在，跳過建立")
        else:
            logger.info(f"R2 bucket '{bucket}' 不存在，自動建立")
            s3.create_bucket(Bucket=bucket)
            logger.info(f"R2 bucket '{bucket}' 建立成功")
    except Exception as e:
        logger.warning(f"R2 bucket 檢查/建立失敗（不影響啟動）: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_pinecone_index()
    _ensure_r2_bucket()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins
cors_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8000"]
if settings.BACKEND_CORS_ORIGINS:
    if isinstance(settings.BACKEND_CORS_ORIGINS, str):
        cors_origins.extend([origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",") if origin.strip()])
    else:
        cors_origins.extend([str(origin) for origin in settings.BACKEND_CORS_ORIGINS])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API versioning middleware – adds deprecation headers to v1 responses
app.add_middleware(APIVersionMiddleware)

# Admin API IP whitelist (T4-4) – blocks non-whitelisted IPs from admin endpoints
app.add_middleware(AdminIPWhitelistMiddleware)

# Request logging middleware (T4-12) – request ID, timing, context
app.add_middleware(RequestLoggingMiddleware)

# Prometheus metrics middleware (T4-11) – request count, latency, in-progress
app.add_middleware(PrometheusMiddleware)

# Custom domain resolution middleware (T4-6) – resolves tenant from Host header
app.add_middleware(CustomDomainMiddleware)

# Rate limiting middleware (only in non-development or when explicitly enabled)
if settings.RATE_LIMIT_ENABLED and not settings.is_development:
    app.add_middleware(RateLimitMiddleware)

# Mount API v1 & v2
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_v2_router, prefix="/api/v2")

@app.get("/")
def root():
    return {"message": "Welcome to UniHR SaaS API", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok", "env": settings.APP_ENV}

# Prometheus metrics endpoint (T4-11)
app.add_route("/metrics", metrics_endpoint)
set_app_info(version="1.0.0", env=settings.APP_ENV)

@app.get("/api/versions")
def api_versions():
    """Return supported API versions and their status."""
    return API_VERSIONS
