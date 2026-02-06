"""
平台管理後台 API（Superuser 專用）
提供跨租戶管理、平台統計、系統健康監控等功能
"""
from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text
from pydantic import BaseModel

from app.api import deps
from app.api.deps_permissions import require_superuser
from app.models.user import User
from app.models.tenant import Tenant
from app.models.document import Document
from app.models.audit import AuditLog, UsageRecord
from app.models.chat import Conversation
from app.crud import crud_tenant, crud_user
from app.schemas.tenant import TenantUpdate, QuotaUpdate, QuotaStatus, PLAN_QUOTAS
from app.services.quota_alerts import QuotaAlertService

router = APIRouter()


# ═══════════════════════════════════════════
#  Response Schemas
# ═══════════════════════════════════════════

class TenantSummary(BaseModel):
    id: str
    name: str
    plan: Optional[str]
    status: Optional[str]
    created_at: Optional[datetime]
    user_count: int = 0
    document_count: int = 0
    total_actions: int = 0
    total_cost: float = 0.0


class PlatformDashboard(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    active_users: int
    total_documents: int
    total_conversations: int
    total_actions: int
    total_cost: float
    # 近 7 天趨勢
    daily_actions: list  # [{date, count, cost}]
    top_tenants: list    # [{name, actions, cost}]


class TenantDetailStats(BaseModel):
    tenant_id: str
    tenant_name: str
    plan: Optional[str]
    status: Optional[str]
    created_at: Optional[datetime]
    user_count: int
    document_count: int
    conversation_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_pinecone_queries: int
    total_embedding_calls: int
    total_cost: float
    total_actions: int
    recent_actions: list    # last 10 audit logs
    users: list             # user list


class AdminUserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: Optional[str]
    status: Optional[str]
    tenant_id: str
    tenant_name: Optional[str]
    department_name: Optional[str]
    created_at: Optional[datetime]


class SystemHealth(BaseModel):
    status: str   # healthy / degraded
    database: str
    redis: str
    uptime_seconds: float
    python_version: str
    active_connections: int


# ═══════════════════════════════════════════
#  Platform Dashboard
# ═══════════════════════════════════════════

@router.get("/dashboard", response_model=PlatformDashboard)
def platform_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """平台總覽儀表板"""

    # Basic counts
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.status == "active").scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.status == "active").scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0

    # Usage aggregates
    usage_agg = db.query(
        func.count(UsageRecord.id).label("total_actions"),
        func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("total_cost"),
    ).first()
    total_actions = usage_agg.total_actions or 0
    total_cost = float(usage_agg.total_cost or 0)

    # Daily actions for last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_rows = (
        db.query(
            func.date(UsageRecord.created_at).label("date"),
            func.count(UsageRecord.id).label("count"),
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("cost"),
        )
        .filter(UsageRecord.created_at >= seven_days_ago)
        .group_by(func.date(UsageRecord.created_at))
        .order_by(func.date(UsageRecord.created_at))
        .all()
    )
    daily_actions = [
        {"date": str(r.date), "count": r.count, "cost": float(r.cost)}
        for r in daily_rows
    ]

    # Top 5 tenants by cost
    top_rows = (
        db.query(
            Tenant.name,
            func.count(UsageRecord.id).label("actions"),
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("cost"),
        )
        .join(UsageRecord, UsageRecord.tenant_id == Tenant.id)
        .group_by(Tenant.name)
        .order_by(func.sum(UsageRecord.estimated_cost_usd).desc())
        .limit(5)
        .all()
    )
    top_tenants = [
        {"name": r.name, "actions": r.actions, "cost": float(r.cost)}
        for r in top_rows
    ]

    return PlatformDashboard(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        total_users=total_users,
        active_users=active_users,
        total_documents=total_documents,
        total_conversations=total_conversations,
        total_actions=total_actions,
        total_cost=total_cost,
        daily_actions=daily_actions,
        top_tenants=top_tenants,
    )


# ═══════════════════════════════════════════
#  Tenant Management
# ═══════════════════════════════════════════

@router.get("/tenants", response_model=List[TenantSummary])
def list_all_tenants(
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """全租戶列表（含用量摘要）"""
    q = db.query(Tenant)
    if status:
        q = q.filter(Tenant.status == status)
    if search:
        q = q.filter(Tenant.name.ilike(f"%{search}%"))

    tenants = q.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for t in tenants:
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == t.id).scalar() or 0
        doc_count = db.query(func.count(Document.id)).filter(Document.tenant_id == t.id).scalar() or 0
        usage = db.query(
            func.count(UsageRecord.id).label("actions"),
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("cost"),
        ).filter(UsageRecord.tenant_id == t.id).first()

        result.append(TenantSummary(
            id=str(t.id),
            name=t.name,
            plan=t.plan,
            status=t.status,
            created_at=t.created_at,
            user_count=user_count,
            document_count=doc_count,
            total_actions=usage.actions or 0,
            total_cost=float(usage.cost or 0),
        ))
    return result


@router.get("/tenants/{tenant_id}/stats", response_model=TenantDetailStats)
def tenant_detail_stats(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """單租戶詳細統計"""
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0
    doc_count = db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0
    conv_count = db.query(func.count(Conversation.id)).filter(Conversation.tenant_id == tenant_id).scalar() or 0

    usage_agg = db.query(
        func.count(UsageRecord.id).label("total_actions"),
        func.coalesce(func.sum(UsageRecord.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(UsageRecord.output_tokens), 0).label("output_tokens"),
        func.coalesce(func.sum(UsageRecord.pinecone_queries), 0).label("pinecone_queries"),
        func.coalesce(func.sum(UsageRecord.embedding_calls), 0).label("embedding_calls"),
        func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0).label("total_cost"),
    ).filter(UsageRecord.tenant_id == tenant_id).first()

    # Recent audit logs
    recent_logs = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    recent_actions = [
        {
            "id": str(log.id),
            "action": log.action,
            "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_logs
    ]

    # User list
    users = db.query(User).filter(User.tenant_id == tenant_id).order_by(User.created_at).all()
    user_list = [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "status": u.status,
        }
        for u in users
    ]

    return TenantDetailStats(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        plan=tenant.plan,
        status=tenant.status,
        created_at=tenant.created_at,
        user_count=user_count,
        document_count=doc_count,
        conversation_count=conv_count,
        total_input_tokens=int(usage_agg.input_tokens or 0),
        total_output_tokens=int(usage_agg.output_tokens or 0),
        total_pinecone_queries=int(usage_agg.pinecone_queries or 0),
        total_embedding_calls=int(usage_agg.embedding_calls or 0),
        total_cost=float(usage_agg.total_cost or 0),
        total_actions=int(usage_agg.total_actions or 0),
        recent_actions=recent_actions,
        users=user_list,
    )


@router.put("/tenants/{tenant_id}")
def update_tenant_admin(
    tenant_id: UUID,
    tenant_in: TenantUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """調整租戶狀態/方案"""
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updated = crud_tenant.update(db, db_obj=tenant, obj_in=tenant_in)
    return {
        "id": str(updated.id),
        "name": updated.name,
        "plan": updated.plan,
        "status": updated.status,
    }


# ═══════════════════════════════════════════
#  Cross-tenant User Search
# ═══════════════════════════════════════════

@router.get("/users", response_model=List[AdminUserInfo])
def search_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """跨租戶用戶搜尋"""
    from app.models.permission import Department

    q = db.query(User)
    if search:
        q = q.filter(
            (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
        )
    if role:
        q = q.filter(User.role == role)
    if tenant_id:
        q = q.filter(User.tenant_id == tenant_id)

    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for u in users:
        tenant = db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
        dept = None
        if u.department_id:
            dept_obj = db.query(Department).filter(Department.id == u.department_id).first()
            dept = dept_obj.name if dept_obj else None

        result.append(AdminUserInfo(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            status=u.status,
            tenant_id=str(u.tenant_id),
            tenant_name=tenant.name if tenant else None,
            department_name=dept,
            created_at=u.created_at,
        ))
    return result


# ═══════════════════════════════════════════
#  System Health
# ═══════════════════════════════════════════

@router.get("/system/health", response_model=SystemHealth)
def system_health(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """系統健康狀態"""
    import sys
    import time
    import redis as redis_lib

    start = time.time()

    # Database check
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    # Redis check
    redis_status = "healthy"
    try:
        from app.config import settings
        r = redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        r.close()
    except Exception:
        redis_status = "unavailable"

    overall = "healthy" if db_status == "healthy" else "degraded"

    return SystemHealth(
        status=overall,
        database=db_status,
        redis=redis_status,
        uptime_seconds=round(time.time() - start, 3),
        python_version=sys.version.split()[0],
        active_connections=0,  # placeholder
    )


# ═══════════════════════════════════════════
#  Quota Management
# ═══════════════════════════════════════════

@router.get("/tenants/{tenant_id}/quota", response_model=QuotaStatus)
def get_tenant_quota(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """查看租戶配額狀態（含使用量與使用率）"""
    status_data = crud_tenant.get_quota_status(db, tenant_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return QuotaStatus(**status_data)


@router.put("/tenants/{tenant_id}/quota", response_model=QuotaStatus)
def update_tenant_quota(
    tenant_id: UUID,
    quota_in: QuotaUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """設定租戶配額"""
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = quota_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    status_data = crud_tenant.get_quota_status(db, tenant_id)
    return QuotaStatus(**status_data)


@router.post("/tenants/{tenant_id}/quota/apply-plan")
def apply_plan_quota(
    tenant_id: UUID,
    plan: str = Query(..., description="方案: free, pro, enterprise"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """套用方案預設配額至租戶"""
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if plan not in PLAN_QUOTAS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}")

    defaults = PLAN_QUOTAS[plan]
    tenant.plan = plan
    for field, value in defaults.items():
        setattr(tenant, field, value)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return {
        "message": f"已套用 {plan} 方案配額",
        "plan": plan,
        "quotas": defaults,
    }


@router.get("/tenants/{tenant_id}/alerts")
def get_tenant_alerts(
    tenant_id: UUID,
    alert_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """查詢租戶告警記錄"""
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    alerts = QuotaAlertService.get_alerts(
        db, tenant_id, alert_type=alert_type, limit=limit
    )
    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "resource": a.resource,
            "current_value": a.current_value,
            "limit_value": a.limit_value,
            "usage_ratio": a.usage_ratio,
            "message": a.message,
            "notified": a.notified,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/tenants/{tenant_id}/alerts/check")
def check_tenant_alerts(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """手動觸發租戶配額檢查並建立告警"""
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    new_alerts = QuotaAlertService.check_and_create_alerts(db, tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "new_alerts": len(new_alerts),
        "alerts": new_alerts,
    }


@router.get("/quota/plans")
def list_plan_quotas(
    current_user: User = Depends(require_superuser),
) -> Any:
    """列出所有方案預設配額"""
    return PLAN_QUOTAS


# ═══════════════════════════════════════════
#  Security Isolation Config
# ═══════════════════════════════════════════

@router.get("/tenants/{tenant_id}/security")
def get_tenant_security(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """查看租戶安全組態"""
    from app.services.security_isolation import (
        get_security_config, SecurityConfigResponse
    )
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    config = get_security_config(db, tenant_id)
    if not config:
        return SecurityConfigResponse(
            tenant_id=str(tenant_id),
            isolation_level="standard",
        )
    return SecurityConfigResponse(
        tenant_id=str(config.tenant_id),
        isolation_level=config.isolation_level,
        pinecone_index_name=config.pinecone_index_name,
        pinecone_namespace=config.pinecone_namespace,
        encryption_key_id=config.encryption_key_id,
        data_retention_days=config.data_retention_days,
        ip_whitelist=config.ip_whitelist,
        require_mfa=config.require_mfa,
        audit_log_export_enabled=config.audit_log_export_enabled,
    )


@router.put("/tenants/{tenant_id}/security")
def update_tenant_security(
    tenant_id: UUID,
    update_data: dict,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """更新租戶安全組態"""
    from app.services.security_isolation import (
        create_or_update_security_config,
        SecurityConfigUpdate,
        SecurityConfigResponse,
    )
    tenant = crud_tenant.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    valid_levels = {"standard", "enhanced", "dedicated"}
    if "isolation_level" in update_data and update_data["isolation_level"] not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid isolation level. Must be one of: {valid_levels}",
        )

    config_update = SecurityConfigUpdate(**update_data)
    config = create_or_update_security_config(db, tenant_id, config_update)
    return SecurityConfigResponse(
        tenant_id=str(config.tenant_id),
        isolation_level=config.isolation_level,
        pinecone_index_name=config.pinecone_index_name,
        pinecone_namespace=config.pinecone_namespace,
        encryption_key_id=config.encryption_key_id,
        data_retention_days=config.data_retention_days,
        ip_whitelist=config.ip_whitelist,
        require_mfa=config.require_mfa,
        audit_log_export_enabled=config.audit_log_export_enabled,
    )
