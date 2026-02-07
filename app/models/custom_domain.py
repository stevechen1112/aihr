"""
Custom Domain Model (T4-6)

Tracks per-tenant custom domain records with DNS verification status.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class CustomDomain(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)

    # DNS Verification
    verification_token = Column(String(64), nullable=False)   # TXT record value
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # SSL status
    ssl_provisioned = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="custom_domains")
