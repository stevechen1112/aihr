"""Per-tenant SSO provider configuration."""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class TenantSSOConfig(Base):
    """Each tenant can enable one or more SSO providers (google / microsoft)."""
    __tablename__ = "tenant_sso_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_tenant_provider"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # "google" | "microsoft"
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    # optional: allowed email domains (JSON list), empty = any domain
    allowed_domains = Column(JSONB, default=list)
    auto_create_user = Column(Boolean, default=True)
    default_role = Column(String, default="employee")
    metadata_ = Column("metadata", JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="sso_configs")
