"""
高資安隔離方案（T3-3）
支援 tenant-per-account 隔離等級：
  - standard：共享基礎設施，邏輯隔離（預設）
  - enhanced：獨立 Pinecone namespace，加密靜態資料
  - dedicated：獨立 Pinecone index，獨立加密金鑰
"""
import uuid
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.base_class import Base


# ═══════════════════════════════════════════
#  Model
# ═══════════════════════════════════════════

class TenantSecurityConfig(Base):
    """租戶安全組態"""
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True, index=True)

    isolation_level = Column(String, default="standard")  # standard, enhanced, dedicated
    pinecone_index_name = Column(String, nullable=True)    # dedicated: 獨立 index
    pinecone_namespace = Column(String, nullable=True)     # enhanced: 獨立 namespace
    encryption_key_id = Column(String, nullable=True)      # dedicated: 獨立加密金鑰 ID
    data_retention_days = Column(String, default="365")     # 資料保留天數
    ip_whitelist = Column(String, nullable=True)            # IP 白名單 (逗號分隔)
    require_mfa = Column(Boolean, default=False)            # 是否要求 MFA
    audit_log_export_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ═══════════════════════════════════════════
#  Schemas
# ═══════════════════════════════════════════

class SecurityConfigResponse(BaseModel):
    tenant_id: str
    isolation_level: str = "standard"
    pinecone_index_name: Optional[str] = None
    pinecone_namespace: Optional[str] = None
    encryption_key_id: Optional[str] = None
    data_retention_days: str = "365"
    ip_whitelist: Optional[str] = None
    require_mfa: bool = False
    audit_log_export_enabled: bool = True


class SecurityConfigUpdate(BaseModel):
    isolation_level: Optional[str] = None
    pinecone_index_name: Optional[str] = None
    pinecone_namespace: Optional[str] = None
    encryption_key_id: Optional[str] = None
    data_retention_days: Optional[str] = None
    ip_whitelist: Optional[str] = None
    require_mfa: Optional[bool] = None
    audit_log_export_enabled: Optional[bool] = None


# ═══════════════════════════════════════════
#  CRUD
# ═══════════════════════════════════════════

def get_security_config(db: Session, tenant_id) -> Optional[TenantSecurityConfig]:
    return (
        db.query(TenantSecurityConfig)
        .filter(TenantSecurityConfig.tenant_id == tenant_id)
        .first()
    )


def create_or_update_security_config(
    db: Session, tenant_id, data: SecurityConfigUpdate
) -> TenantSecurityConfig:
    config = get_security_config(db, tenant_id)
    if not config:
        config = TenantSecurityConfig(tenant_id=tenant_id)
        db.add(config)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config


def get_isolation_params(db: Session, tenant_id) -> dict:
    """
    取得租戶的隔離參數，供 KnowledgeBaseRetriever 等服務使用。
    回傳 {"index_name": ..., "namespace": ..., "isolation_level": ...}
    """
    config = get_security_config(db, tenant_id)
    if not config:
        # 預設 standard 隔離
        return {
            "isolation_level": "standard",
            "index_name": None,
            "namespace": str(tenant_id),
        }

    return {
        "isolation_level": config.isolation_level,
        "index_name": config.pinecone_index_name,
        "namespace": config.pinecone_namespace or str(tenant_id),
    }
