import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Enum, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Tenant(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, index=True, nullable=False)
    plan = Column(String, default="free")  # free, pro, enterprise
    status = Column(String, default="active")  # active, suspended
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Quota 配額欄位 ──
    max_users = Column(Integer, nullable=True, default=None)            # null = 無限制
    max_documents = Column(Integer, nullable=True, default=None)
    max_storage_mb = Column(Integer, nullable=True, default=None)
    monthly_query_limit = Column(Integer, nullable=True, default=None)  # 每月查詢次數上限
    monthly_token_limit = Column(Integer, nullable=True, default=None)  # 每月 token 上限
    quota_alert_threshold = Column(Float, default=0.8)                  # 配額告警閾值 (0~1)
    quota_alert_email = Column(String, nullable=True)                   # 告警通知信箱

    # ── White-label Branding (T4-3) ──
    brand_name = Column(String(100), nullable=True)                     # 自訂品牌名稱
    brand_logo_url = Column(String(500), nullable=True)                 # Logo URL
    brand_primary_color = Column(String(7), nullable=True)              # 主色（如 #2563eb）
    brand_secondary_color = Column(String(7), nullable=True)            # 輔色
    brand_favicon_url = Column(String(500), nullable=True)              # Favicon URL
    custom_domain = Column(String(255), nullable=True, unique=True)     # 自訂域名

    # Relationships
    users = relationship("User", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")
    conversations = relationship("Conversation", back_populates="tenant")
    audit_logs = relationship("AuditLog", back_populates="tenant")
    usage_records = relationship("UsageRecord", back_populates="tenant")
    departments = relationship("Department", back_populates="tenant")
    feature_permissions = relationship("FeaturePermission", back_populates="tenant")
    sso_configs = relationship("TenantSSOConfig", back_populates="tenant", cascade="all, delete-orphan")
