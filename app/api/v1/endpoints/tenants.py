from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_tenant
from app.models.user import User
from app.schemas.tenant import Tenant, TenantCreate, TenantUpdate

router = APIRouter()


@router.get("/", response_model=List[Tenant])
def read_tenants(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    獲取租戶列表（僅限 superuser）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    tenants = crud_tenant.get_multi(db, skip=skip, limit=limit)
    return tenants


@router.post("/", response_model=Tenant)
def create_tenant(
    *,
    db: Session = Depends(deps.get_db),
    tenant_in: TenantCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    建立新租戶（僅限 superuser）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    tenant = crud_tenant.get_by_name(db, name=tenant_in.name)
    if tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this name already exists"
        )
    tenant = crud_tenant.create(db, obj_in=tenant_in)
    return tenant


@router.get("/{tenant_id}", response_model=Tenant)
def read_tenant(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    根據 ID 獲取特定租戶
    """
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    # 非 superuser 只能查看自己的租戶
    if not current_user.is_superuser and tenant.id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return tenant


@router.put("/{tenant_id}", response_model=Tenant)
def update_tenant(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: UUID,
    tenant_in: TenantUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新租戶資訊（僅限 superuser）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    tenant = crud_tenant.update(db, db_obj=tenant, obj_in=tenant_in)
    return tenant
