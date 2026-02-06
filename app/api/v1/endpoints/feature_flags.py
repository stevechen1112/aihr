"""Feature Flag management API — Superuser only.

Endpoints:
- GET    /feature-flags           → list all flags
- POST   /feature-flags           → create flag
- GET    /feature-flags/{key}     → get single flag
- PUT    /feature-flags/{key}     → update flag
- DELETE /feature-flags/{key}     → delete flag
- GET    /feature-flags/{key}/evaluate?tenant_id=  → evaluate for a tenant
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps_permissions import require_superuser
from app.models.feature_flag import FeatureFlag as FeatureFlagModel
from app.models.user import User
from app.schemas.feature_flag import (
    FeatureFlag,
    FeatureFlagCreate,
    FeatureFlagUpdate,
    FeatureFlagEvaluation,
)
from app.services.feature_flags import is_flag_enabled, get_all_flags

router = APIRouter()


@router.get("/", response_model=List[dict])
def list_feature_flags(
    db: Session = Depends(deps.get_db),
    _: User = Depends(require_superuser),
) -> Any:
    return get_all_flags(db)


@router.post("/", response_model=FeatureFlag)
def create_feature_flag(
    body: FeatureFlagCreate,
    db: Session = Depends(deps.get_db),
    _: User = Depends(require_superuser),
) -> Any:
    existing = db.query(FeatureFlagModel).filter(FeatureFlagModel.key == body.key).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Flag '{body.key}' already exists")

    flag = FeatureFlagModel(
        key=body.key,
        description=body.description,
        enabled=body.enabled,
        rollout_percentage=body.rollout_percentage,
        allowed_tenant_ids=body.allowed_tenant_ids,
        allowed_environments=body.allowed_environments,
        metadata_=body.metadata,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


@router.get("/{key}", response_model=FeatureFlag)
def get_feature_flag(
    key: str,
    db: Session = Depends(deps.get_db),
    _: User = Depends(require_superuser),
) -> Any:
    flag = db.query(FeatureFlagModel).filter(FeatureFlagModel.key == key).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag


@router.put("/{key}", response_model=FeatureFlag)
def update_feature_flag(
    key: str,
    body: FeatureFlagUpdate,
    db: Session = Depends(deps.get_db),
    _: User = Depends(require_superuser),
) -> Any:
    flag = db.query(FeatureFlagModel).filter(FeatureFlagModel.key == key).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if k == "metadata":
            setattr(flag, "metadata_", v)
        else:
            setattr(flag, k, v)
    db.commit()
    db.refresh(flag)
    return flag


@router.delete("/{key}")
def delete_feature_flag(
    key: str,
    db: Session = Depends(deps.get_db),
    _: User = Depends(require_superuser),
) -> Any:
    flag = db.query(FeatureFlagModel).filter(FeatureFlagModel.key == key).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    db.delete(flag)
    db.commit()
    return {"ok": True}


@router.get("/{key}/evaluate", response_model=FeatureFlagEvaluation)
def evaluate_feature_flag(
    key: str,
    tenant_id: Optional[UUID] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Evaluate a flag for the current user's tenant (or a specific tenant for superusers)."""
    tid = tenant_id if (tenant_id and current_user.is_superuser) else current_user.tenant_id
    enabled = is_flag_enabled(db, key, tid)
    return FeatureFlagEvaluation(key=key, enabled=enabled)
