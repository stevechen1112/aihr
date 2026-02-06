from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps_permissions import check_user_management_permission
from app.crud import crud_user, crud_tenant
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    獲取當前用戶資訊
    """
    return current_user


@router.post("/", response_model=UserSchema)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    建立新用戶
    - 權限：owner, admin
    - Superuser 可以為任何租戶建立用戶
    - 一般用戶只能為自己的租戶建立用戶
    """
    # 權限檢查
    check_user_management_permission(current_user)
    
    # 檢查權限
    if not current_user.is_superuser and user_in.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create user for this tenant"
        )
    
    # 配額檢查
    if not current_user.is_superuser:
        quota = crud_tenant.check_quota(db, user_in.tenant_id, "user")
        if not quota.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": quota["message"],
                    "resource": "user",
                    "current": quota.get("current"),
                    "limit": quota.get("limit"),
                },
            )
    
    # 檢查 email 是否已存在
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    user = crud_user.create(db, obj_in=user_in)
    return user
