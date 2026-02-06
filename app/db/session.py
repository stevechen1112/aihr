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
from sqlalchemy import create_engine, event
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
