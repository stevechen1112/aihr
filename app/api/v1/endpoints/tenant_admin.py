"""
租戶自助管理後台 API（T3-2）
各租戶 Owner/Admin 可自行管理公司設定、用戶、查看用量摘要
"""
from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr

from app.api import deps
from app.api.deps_permissions import require_admin
from app.models.user import User
from app.models.tenant import Tenant
from app.models.document import Document
from app.models.audit import AuditLog, UsageRecord
from app.models.chat import Conversation
from app.crud import crud_tenant, crud_user
from app.schemas.tenant import QuotaStatus
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter()


# ═══════════════════════════════════════════
#  Response Schemas
# ═══════════════════════════════════════════

class CompanyProfile(BaseModel):
    id: str
    name: str
    plan: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    user_count: int = 0
    document_count: int = 0
    conversation_count: int = 0


class CompanyUserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "employee"
    password: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None  # active / suspended


class BrandingSettings(BaseModel):
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None
    brand_favicon_url: Optional[str] = None


class BrandingPublic(BaseModel):
    """Public branding info (no auth required — used by login page)."""
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None
    brand_favicon_url: Optional[str] = None
    tenant_name: str = ""


class CompanyDashboard(BaseModel):
    company_name: str
    plan: Optional[str] = None
    user_count: int = 0
    document_count: int = 0
    conversation_count: int = 0
    monthly_queries: int = 0
    monthly_tokens: int = 0
    monthly_cost: float = 0.0
    quota_status: Optional[QuotaStatus] = None


# ═══════════════════════════════════════════
#  Company Dashboard
# ═══════════════════════════════════════════

def _ensure_owner_admin(current_user: User):
    """確保使用者為 owner 或 admin"""
    if current_user.is_superuser:
        return
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能需要 Owner 或 Admin 角色"
        )


@router.get("/dashboard", response_model=CompanyDashboard)
def company_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    公司儀表板 — Owner/Admin 查看公司概況與配額狀態
    """
    _ensure_owner_admin(current_user)
    tid = current_user.tenant_id
    tenant = crud_tenant.get(db, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tid).scalar() or 0
    doc_count = db.query(func.count(Document.id)).filter(Document.tenant_id == tid).scalar() or 0
    conv_count = db.query(func.count(Conversation.id)).filter(Conversation.tenant_id == tid).scalar() or 0

    # 月度使用量
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = db.query(
        func.count(UsageRecord.id).label("queries"),
        func.coalesce(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0).label("tokens"),
        func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("cost"),
    ).filter(
        UsageRecord.tenant_id == tid,
        UsageRecord.created_at >= month_start,
    ).first()

    quota_data = crud_tenant.get_quota_status(db, tid)
    quota = QuotaStatus(**quota_data) if quota_data else None

    return CompanyDashboard(
        company_name=tenant.name,
        plan=tenant.plan,
        user_count=user_count,
        document_count=doc_count,
        conversation_count=conv_count,
        monthly_queries=monthly.queries or 0,
        monthly_tokens=int(monthly.tokens or 0),
        monthly_cost=float(monthly.cost or 0),
        quota_status=quota,
    )


# ═══════════════════════════════════════════
#  Company Settings
# ═══════════════════════════════════════════

@router.get("/profile", response_model=CompanyProfile)
def get_company_profile(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """查看公司資訊"""
    _ensure_owner_admin(current_user)
    tid = current_user.tenant_id
    tenant = crud_tenant.get(db, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tid).scalar() or 0
    doc_count = db.query(func.count(Document.id)).filter(Document.tenant_id == tid).scalar() or 0
    conv_count = db.query(func.count(Conversation.id)).filter(Conversation.tenant_id == tid).scalar() or 0

    return CompanyProfile(
        id=str(tenant.id),
        name=tenant.name,
        plan=tenant.plan,
        status=tenant.status,
        created_at=tenant.created_at,
        user_count=user_count,
        document_count=doc_count,
        conversation_count=conv_count,
    )


@router.get("/quota", response_model=QuotaStatus)
def get_company_quota(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """查看公司配額狀態"""
    _ensure_owner_admin(current_user)
    status_data = crud_tenant.get_quota_status(db, current_user.tenant_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return QuotaStatus(**status_data)


# ═══════════════════════════════════════════
#  User Management (Self-service)
# ═══════════════════════════════════════════

@router.get("/users", response_model=List[CompanyUserInfo])
def list_company_users(
    role: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """列出公司所有使用者"""
    _ensure_owner_admin(current_user)
    q = db.query(User).filter(User.tenant_id == current_user.tenant_id)
    if role:
        q = q.filter(User.role == role)
    if status_filter:
        q = q.filter(User.status == status_filter)
    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [
        CompanyUserInfo(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            status=u.status,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users/invite", response_model=CompanyUserInfo)
def invite_user(
    invite: InviteUserRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    邀請（建立）新使用者到自己公司
    Owner/Admin 限定
    """
    _ensure_owner_admin(current_user)

    # 配額檢查
    quota = crud_tenant.check_quota(db, current_user.tenant_id, "user")
    if not quota.get("allowed", True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=quota["message"],
        )

    # 不能建立 owner（只有 superuser 可以）
    if invite.role == "owner" and not current_user.is_superuser:
        if current_user.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有 Owner 可以指派 Owner 角色"
            )

    # 檢查 email
    existing = crud_user.get_by_email(db, email=invite.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此 Email 已被使用"
        )

    user_in = UserCreate(
        email=invite.email,
        full_name=invite.full_name,
        password=invite.password,
        tenant_id=current_user.tenant_id,
        role=invite.role,
    )
    new_user = crud_user.create(db, obj_in=user_in)
    return CompanyUserInfo(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        status=new_user.status,
        created_at=new_user.created_at,
    )


@router.put("/users/{user_id}", response_model=CompanyUserInfo)
def update_company_user(
    user_id: UUID,
    update: UpdateUserRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """更新公司使用者角色/狀態"""
    _ensure_owner_admin(current_user)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="無法管理其他公司的使用者")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="無法修改自己的角色/狀態")

    # Admin 不能改 Owner
    if current_user.role == "admin" and target.role == "owner":
        raise HTTPException(status_code=403, detail="Admin 無法修改 Owner")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(target, field, value)
    db.add(target)
    db.commit()
    db.refresh(target)

    return CompanyUserInfo(
        id=str(target.id),
        email=target.email,
        full_name=target.full_name,
        role=target.role,
        status=target.status,
        created_at=target.created_at,
    )


@router.delete("/users/{user_id}")
def deactivate_company_user(
    user_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """停用公司使用者（軟刪除）"""
    _ensure_owner_admin(current_user)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="無法管理其他公司的使用者")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="無法停用自己")
    if current_user.role == "admin" and target.role == "owner":
        raise HTTPException(status_code=403, detail="Admin 無法停用 Owner")

    target.status = "suspended"
    db.add(target)
    db.commit()

    return {"message": f"使用者 {target.email} 已停用", "user_id": str(user_id)}


# ═══════════════════════════════════════════
#  Usage Summary (Self-service)
# ═══════════════════════════════════════════

@router.get("/usage/summary")
def company_usage_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """查看公司用量摘要"""
    _ensure_owner_admin(current_user)
    from app.crud.crud_audit import get_usage_summary
    from datetime import datetime as dt

    kwargs = {"tenant_id": current_user.tenant_id}
    if start_date:
        kwargs["start_date"] = dt.fromisoformat(start_date)
    if end_date:
        kwargs["end_date"] = dt.fromisoformat(end_date)

    return get_usage_summary(db, **kwargs)


@router.get("/usage/by-user")
def company_usage_by_user(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """查看每位使用者的用量"""
    _ensure_owner_admin(current_user)
    tid = current_user.tenant_id
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = (
        db.query(
            User.email,
            User.full_name,
            func.count(UsageRecord.id).label("queries"),
            func.coalesce(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("cost"),
        )
        .outerjoin(UsageRecord, (UsageRecord.user_id == User.id) & (UsageRecord.created_at >= month_start))
        .filter(User.tenant_id == tid)
        .group_by(User.id, User.email, User.full_name)
        .order_by(func.sum(UsageRecord.estimated_cost_usd).desc().nullslast())
        .all()
    )

    return [
        {
            "email": r.email,
            "full_name": r.full_name,
            "monthly_queries": r.queries or 0,
            "monthly_tokens": int(r.tokens or 0),
            "monthly_cost": float(r.cost or 0),
        }
        for r in rows
    ]


# ═══════════════════════════════════════════
#  White-Label Branding (T4-3)
# ═══════════════════════════════════════════

@router.get("/branding", response_model=BrandingSettings)
def get_branding(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """取得公司品牌設定"""
    _ensure_owner_admin(current_user)
    tenant = crud_tenant.get(db, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return BrandingSettings(
        brand_name=tenant.brand_name,
        brand_logo_url=tenant.brand_logo_url,
        brand_primary_color=tenant.brand_primary_color,
        brand_secondary_color=tenant.brand_secondary_color,
        brand_favicon_url=tenant.brand_favicon_url,
    )


@router.put("/branding", response_model=BrandingSettings)
def update_branding(
    branding: BrandingSettings,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """更新公司品牌設定（白標）"""
    _ensure_owner_admin(current_user)

    # Only pro / enterprise plans can customize branding
    tenant = crud_tenant.get(db, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.plan == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="白標功能需要 Pro 或 Enterprise 方案",
        )

    update_data = branding.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return BrandingSettings(
        brand_name=tenant.brand_name,
        brand_logo_url=tenant.brand_logo_url,
        brand_primary_color=tenant.brand_primary_color,
        brand_secondary_color=tenant.brand_secondary_color,
        brand_favicon_url=tenant.brand_favicon_url,
    )
