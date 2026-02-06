"""Feature flags for canary / gradual releases.

Provides a simple in-DB feature-flag system that allows:
- Global flags (on/off for everyone)
- Percentage-based rollout (e.g. 10 % of tenants)
- Tenant-allowlist (specific tenants get the feature early)
- Environment scoping (only in staging / production)
"""

import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.db.base_class import Base


class FeatureFlag(Base):
    """Platform-wide feature flag for canary releases."""
    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    key = Column(String, unique=True, nullable=False, index=True)      # e.g. "new_chat_ui", "rag_v2"
    description = Column(String, default="")
    enabled = Column(Boolean, default=False)                           # global kill switch
    rollout_percentage = Column(Integer, default=0)                    # 0-100
    allowed_tenant_ids = Column(ARRAY(UUID(as_uuid=True)), default=list) # explicit allow-list
    allowed_environments = Column(ARRAY(String), default=list)           # ["staging", "production"]
    metadata_ = Column("metadata", JSONB, default=dict)                # arbitrary config

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
