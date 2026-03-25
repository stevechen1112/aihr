"""
資料庫 Session 與連線池設定（T4-15 調優）
==========================================

連線池參數說明：
- pool_size: 常駐連線數（預設 10，適合 4-worker uvicorn）
- max_overflow: 超額連線數（尖峰時最多 pool_size + max_overflow）
- pool_timeout: 等待連線的最大秒數
- pool_recycle: 連線回收週期（避免 PostgreSQL idle connection 被斷）
- pool_pre_ping: 使用前檢測連線是否存活
"""

import logging
import time
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

logger = logging.getLogger("unihr.db")

# ---------------------------------------------------------------------------
# 連線池調參
# ---------------------------------------------------------------------------
POOL_SIZE = int(getattr(settings, "DB_POOL_SIZE", 10))
MAX_OVERFLOW = int(getattr(settings, "DB_MAX_OVERFLOW", 20))
POOL_TIMEOUT = int(getattr(settings, "DB_POOL_TIMEOUT", 30))
POOL_RECYCLE = int(getattr(settings, "DB_POOL_RECYCLE", 1800))  # 30 分鐘

# Slow query 門檻（毫秒）
SLOW_QUERY_THRESHOLD_MS = int(getattr(settings, "SLOW_QUERY_THRESHOLD_MS", 500))

# ---------------------------------------------------------------------------
# SSL 設定
# ---------------------------------------------------------------------------
_ssl_mode = getattr(settings, "POSTGRES_SSL_MODE", "prefer")
_connect_args: dict = {}
if _ssl_mode and _ssl_mode != "disable":
    _connect_args["sslmode"] = _ssl_mode
    _ssl_root_cert = getattr(settings, "POSTGRES_SSL_ROOT_CERT", None)
    if _ssl_root_cert:
        _connect_args["sslrootcert"] = _ssl_root_cert

_connect_timeout = int(getattr(settings, "DB_CONNECT_TIMEOUT_SECONDS", 5))
if _connect_timeout > 0:
    _connect_args["connect_timeout"] = _connect_timeout

engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}",
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    # 開發環境可開啟 echo
    echo=getattr(settings, "DB_ECHO", False),
    connect_args=_connect_args,
)


# ---------------------------------------------------------------------------
# Slow Query 監控（T4-15）
# ---------------------------------------------------------------------------
@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """記錄查詢開始時間"""
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """檢測慢查詢並記錄"""
    total_ms = (time.perf_counter() - conn.info["query_start_time"].pop()) * 1000

    if total_ms >= SLOW_QUERY_THRESHOLD_MS:
        # 截斷過長的 SQL 避免日誌爆量
        stmt_preview = statement[:500] + "..." if len(statement) > 500 else statement
        logger.warning(
            "🐢 Slow query detected",
            extra={
                "duration_ms": round(total_ms, 2),
                "statement": stmt_preview,
                "threshold_ms": SLOW_QUERY_THRESHOLD_MS,
            },
        )


# ---------------------------------------------------------------------------
# 連線池狀態監控
# ---------------------------------------------------------------------------
@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_conn, connection_rec, connection_proxy):
    """連線取出時記錄池使用狀況"""
    pool = engine.pool
    logger.debug(
        "DB pool checkout",
        extra={
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        },
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def apply_rls_context(
    db,
    tenant_id: Optional[Union[UUID, str]] = None,
    bypass: bool = False,
):
    """Apply PostgreSQL RLS session variables to an existing DB session."""
    if not getattr(settings, "RLS_ENFORCEMENT_ENABLED", False):
        return db

    tenant_id_str = str(tenant_id) if tenant_id is not None else ""
    bypass_value = "1" if bypass else "0"
    db.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id_str},
    )
    db.execute(
        text("SELECT set_config('app.bypass_rls', :bypass, true)"),
        {"bypass": bypass_value},
    )
    return db


def create_session(
    tenant_id: Optional[Union[UUID, str]] = None,
    bypass: bool = False,
):
    """Create a DB session with optional RLS context preconfigured."""
    db = SessionLocal()
    return apply_rls_context(db, tenant_id=tenant_id, bypass=bypass)


# ---------------------------------------------------------------------------
# 讀寫分離準備（Read Replica）
# ---------------------------------------------------------------------------
# 當啟用 Read Replica 時，取消下方註解並設定 DB_READ_REPLICA_SERVER
#
# READ_REPLICA_SERVER = getattr(settings, "DB_READ_REPLICA_SERVER", None)
# if READ_REPLICA_SERVER:
#     read_engine = create_engine(
#         f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
#         f"@{READ_REPLICA_SERVER}/{settings.POSTGRES_DB}",
#         pool_pre_ping=True,
#         pool_size=POOL_SIZE,
#         max_overflow=MAX_OVERFLOW,
#         pool_timeout=POOL_TIMEOUT,
#         pool_recycle=POOL_RECYCLE,
#     )
#     ReadSessionLocal = sessionmaker(
#         autocommit=False, autoflush=False, bind=read_engine
#     )
# else:
#     ReadSessionLocal = SessionLocal  # fallback to primary


def get_pool_status() -> dict:
    """取得連線池狀態（供 /admin/system/health 使用）"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": MAX_OVERFLOW,
        "pool_timeout": POOL_TIMEOUT,
        "pool_recycle": POOL_RECYCLE,
    }
