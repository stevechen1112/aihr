from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.permission import Department, FeaturePermission
from app.schemas.permission import (
    DepartmentCreate, DepartmentUpdate,
    FeaturePermissionCreate, FeaturePermissionUpdate,
)


# ═══════════════════════════════════════════
#  Department CRUD
# ═══════════════════════════════════════════

def create_department(
    db: Session, *, tenant_id: UUID, obj_in: DepartmentCreate
) -> Department:
    db_obj = Department(
        tenant_id=tenant_id,
        name=obj_in.name,
        description=obj_in.description,
        parent_id=obj_in.parent_id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_department(db: Session, *, department_id: UUID) -> Optional[Department]:
    return db.query(Department).filter(Department.id == department_id).first()


def get_departments_by_tenant(
    db: Session, *, tenant_id: UUID, include_inactive: bool = False
) -> List[Department]:
    q = db.query(Department).filter(Department.tenant_id == tenant_id)
    if not include_inactive:
        q = q.filter(Department.is_active == True)
    return q.order_by(Department.name).all()


def update_department(
    db: Session, *, department_id: UUID, obj_in: DepartmentUpdate
) -> Optional[Department]:
    dept = get_department(db, department_id=department_id)
    if not dept:
        return None
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept


def delete_department(db: Session, *, department_id: UUID) -> bool:
    dept = get_department(db, department_id=department_id)
    if not dept:
        return False
    # Soft delete — set inactive
    dept.is_active = False
    db.commit()
    return True


# ═══════════════════════════════════════════
#  Feature Permission CRUD
# ═══════════════════════════════════════════

def get_feature_permissions(
    db: Session, *, tenant_id: UUID
) -> List[FeaturePermission]:
    return (
        db.query(FeaturePermission)
        .filter(FeaturePermission.tenant_id == tenant_id)
        .order_by(FeaturePermission.feature, FeaturePermission.role)
        .all()
    )


def get_feature_permission(
    db: Session, *, tenant_id: UUID, feature: str, role: Optional[str] = None
) -> Optional[FeaturePermission]:
    q = db.query(FeaturePermission).filter(
        FeaturePermission.tenant_id == tenant_id,
        FeaturePermission.feature == feature,
    )
    if role:
        q = q.filter(FeaturePermission.role == role)
    else:
        q = q.filter(FeaturePermission.role.is_(None))
    return q.first()


def set_feature_permission(
    db: Session, *, tenant_id: UUID, obj_in: FeaturePermissionCreate
) -> FeaturePermission:
    existing = get_feature_permission(
        db, tenant_id=tenant_id, feature=obj_in.feature, role=obj_in.role
    )
    if existing:
        existing.allowed = obj_in.allowed
        existing.config = obj_in.config or {}
        db.commit()
        db.refresh(existing)
        return existing
    db_obj = FeaturePermission(
        tenant_id=tenant_id,
        feature=obj_in.feature,
        role=obj_in.role,
        allowed=obj_in.allowed,
        config=obj_in.config or {},
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def is_feature_allowed(
    db: Session, *, tenant_id: UUID, feature: str, role: str
) -> bool:
    """
    檢查功能是否對特定角色開放。
    優先順序：
      1. role-specific 設定
      2. tenant-level 通用設定 (role=None)
      3. 預設 True (未設定 = 允許)
    """
    # Check role-specific first
    perm = get_feature_permission(db, tenant_id=tenant_id, feature=feature, role=role)
    if perm:
        return perm.allowed
    # Fallback to tenant-level
    perm = get_feature_permission(db, tenant_id=tenant_id, feature=feature, role=None)
    if perm:
        return perm.allowed
    # Default: allowed
    return True
