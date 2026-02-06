"""Feature flag evaluation logic."""
import hashlib
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.feature_flag import FeatureFlag


def _tenant_bucket(tenant_id: UUID, flag_key: str) -> int:
    """Deterministic 0-99 bucket based on tenant_id + flag_key.
    Same tenant+flag always lands in the same bucket → consistent experience.
    """
    h = hashlib.sha256(f"{tenant_id}:{flag_key}".encode()).hexdigest()
    return int(h[:8], 16) % 100


def is_flag_enabled(
    db: Session,
    flag_key: str,
    tenant_id: Optional[UUID] = None,
) -> bool:
    """Evaluate whether a feature flag is active for the given context.

    Priority:
    1. Flag must exist and be globally enabled
    2. Environment check (if scoped)
    3. Tenant allow-list (instant yes)
    4. Percentage rollout (deterministic hash)
    """
    flag: Optional[FeatureFlag] = (
        db.query(FeatureFlag).filter(FeatureFlag.key == flag_key).first()
    )
    if not flag or not flag.enabled:
        return False

    # Environment scoping
    if flag.allowed_environments:
        if settings.APP_ENV not in flag.allowed_environments:
            return False

    # Tenant allow-list
    if tenant_id and flag.allowed_tenant_ids:
        if tenant_id in flag.allowed_tenant_ids:
            return True

    # Percentage rollout
    if flag.rollout_percentage >= 100:
        return True
    if flag.rollout_percentage <= 0:
        # Only allow-listed tenants pass (handled above)
        return False

    if tenant_id:
        bucket = _tenant_bucket(tenant_id, flag_key)
        return bucket < flag.rollout_percentage

    # No tenant context, use global percentage as probability
    return False


def get_all_flags(db: Session) -> list[dict]:
    """Return all feature flags with their current state."""
    flags = db.query(FeatureFlag).order_by(FeatureFlag.key).all()
    return [
        {
            "id": str(f.id),
            "key": f.key,
            "description": f.description,
            "enabled": f.enabled,
            "rollout_percentage": f.rollout_percentage,
            "allowed_tenant_ids": [str(t) for t in (f.allowed_tenant_ids or [])],
            "allowed_environments": f.allowed_environments or [],
            "metadata": f.metadata_ or {},
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in flags
    ]
