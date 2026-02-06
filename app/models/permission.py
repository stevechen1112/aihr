import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Department(Base):
    """部門"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="departments")
    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
    users = relationship("User", back_populates="department")
    documents = relationship("Document", back_populates="department")


class FeaturePermission(Base):
    """
    租戶功能開關 — 控制每個租戶可使用的模組
    每個 record 代表一個 tenant + feature + role 的權限配置
    """
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    feature = Column(String, nullable=False, index=True)        # chat, documents, audit, kb, user_mgmt, departments
    role = Column(String, nullable=True)                         # null = all roles; specific role override
    allowed = Column(Boolean, default=True)
    config = Column(JSON, default={})                            # extra config, e.g. max_uploads, max_queries_per_day

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="feature_permissions")
