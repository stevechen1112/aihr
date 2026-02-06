"""
Admin Service 資料庫 Session（T4-18）
======================================

可獨立設定指向 Read Replica，避免管理端查詢影響客戶端效能。

環境變數：
  - ADMIN_DB_HOST: Read Replica 位址（預設同主 DB）
  - ADMIN_DB_PORT: Read Replica 埠號
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 如果有獨立的 Read Replica 就用它，否則 fallback 到主 DB
ADMIN_DB_HOST = os.getenv("ADMIN_DB_HOST", settings.POSTGRES_SERVER)
ADMIN_DB_PORT = os.getenv("ADMIN_DB_PORT", "5432")

admin_engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{ADMIN_DB_HOST}:{ADMIN_DB_PORT}/{settings.POSTGRES_DB}",
    pool_pre_ping=True,
    pool_size=5,          # Admin 查詢量較低
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

AdminSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=admin_engine
)
