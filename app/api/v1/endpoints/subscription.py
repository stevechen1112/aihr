"""
Subscription API (T4-17)

Endpoints:
  - GET  /plans            — Public: list all plans with features
  - GET  /current          — Current tenant's plan and limits
  - POST /upgrade          — Request plan upgrade
  - GET  /usage/export     — Export usage data (Pro+ feature)
"""
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.tenant import Tenant
from app.models.audit import UsageRecord
from app.services.subscription import (
    PLAN_MATRIX,
    get_plan,
    get_plan_feature,
    get_upgrade_suggestion,
)

router = APIRouter()
logger = logging.getLogger("unihr.subscription")


# ── Schemas ──

class PlanFeatures(BaseModel):
    ai_chat: bool = False
    document_upload: bool = False
    basic_analytics: bool = False
    audit_logs: bool = False
    sso: bool = False
    white_label: bool = False
    custom_domain: bool = False
    api_access: bool = False
    priority_support: bool = False
    data_export: bool = False
    department_management: bool = False
    advanced_analytics: bool = False


class PlanInfo(BaseModel):
    name: str
    display_name: str
    price_monthly_usd: int
    price_yearly_usd: int
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    max_storage_mb: Optional[int] = None
    monthly_query_limit: Optional[int] = None
    monthly_token_limit: Optional[int] = None
    features: PlanFeatures


class CurrentPlan(BaseModel):
    plan: str
    display_name: str
    features: PlanFeatures
    limits: dict
    usage: dict
    upgrade_available: bool = False


class UpgradeRequest(BaseModel):
    target_plan: str  # "pro" or "enterprise"


class UpgradeResult(BaseModel):
    success: bool
    message: str
    new_plan: Optional[str] = None


# ── Endpoints ──

@router.get("/plans", response_model=List[PlanInfo])
def list_plans() -> Any:
    """公開：列出所有訂閱方案"""
    plans = []
    for name, config in PLAN_MATRIX.items():
        plans.append(PlanInfo(
            name=name,
            display_name=config["display_name"],
            price_monthly_usd=config["price_monthly_usd"],
            price_yearly_usd=config["price_yearly_usd"],
            max_users=config["max_users"],
            max_documents=config["max_documents"],
            max_storage_mb=config["max_storage_mb"],
            monthly_query_limit=config["monthly_query_limit"],
            monthly_token_limit=config["monthly_token_limit"],
            features=PlanFeatures(**config["features"]),
        ))
    return plans


@router.get("/current", response_model=CurrentPlan)
def current_plan(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """查看目前租戶方案、用量與功能"""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan_config = get_plan(tenant.plan or "free")

    # Current month usage
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = db.query(
        func.count(UsageRecord.id).label("queries"),
        func.coalesce(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0).label("tokens"),
    ).filter(
        UsageRecord.tenant_id == current_user.tenant_id,
        UsageRecord.created_at >= month_start,
    ).first()

    from app.models.user import User as UserModel
    from app.models.document import Document
    user_count = db.query(func.count(UserModel.id)).filter(UserModel.tenant_id == current_user.tenant_id).scalar() or 0
    doc_count = db.query(func.count(Document.id)).filter(Document.tenant_id == current_user.tenant_id).scalar() or 0

    return CurrentPlan(
        plan=tenant.plan or "free",
        display_name=plan_config["display_name"],
        features=PlanFeatures(**plan_config["features"]),
        limits={
            "max_users": plan_config["max_users"],
            "max_documents": plan_config["max_documents"],
            "max_storage_mb": plan_config["max_storage_mb"],
            "monthly_query_limit": plan_config["monthly_query_limit"],
            "monthly_token_limit": plan_config["monthly_token_limit"],
        },
        usage={
            "users": user_count,
            "documents": doc_count,
            "monthly_queries": monthly.queries if monthly else 0,
            "monthly_tokens": int(monthly.tokens) if monthly else 0,
        },
        upgrade_available=tenant.plan in ("free", "pro"),
    )


@router.post("/upgrade", response_model=UpgradeResult)
def request_upgrade(
    body: UpgradeRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    申請升級方案

    目前階段：直接更新 plan 值（未來整合 Stripe 付款）
    """
    if current_user.role not in ("owner",) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="只有 Owner 可以變更方案")

    if body.target_plan not in PLAN_MATRIX:
        raise HTTPException(status_code=400, detail="無效的方案名稱")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate upgrade path
    plan_order = {"free": 0, "pro": 1, "enterprise": 2}
    current_level = plan_order.get(tenant.plan or "free", 0)
    target_level = plan_order.get(body.target_plan, 0)

    if target_level <= current_level:
        raise HTTPException(
            status_code=400,
            detail=f"目前方案為 {tenant.plan}，無法降級至 {body.target_plan}（降級請聯繫客服）",
        )

    # Update plan and apply limits
    old_plan = tenant.plan
    tenant.plan = body.target_plan
    new_config = get_plan(body.target_plan)
    tenant.max_users = new_config["max_users"]
    tenant.max_documents = new_config["max_documents"]
    tenant.max_storage_mb = new_config["max_storage_mb"]
    tenant.monthly_query_limit = new_config["monthly_query_limit"]
    tenant.monthly_token_limit = new_config["monthly_token_limit"]

    db.commit()
    logger.info(
        "Tenant %s upgraded: %s → %s (by user %s)",
        tenant.id, old_plan, body.target_plan, current_user.id,
    )

    return UpgradeResult(
        success=True,
        message=f"已升級至 {new_config['display_name']} 方案！",
        new_plan=body.target_plan,
    )


@router.get("/feature-check")
def check_feature(
    feature: str = Query(..., description="Feature name to check"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """檢查功能是否可用，若不可用建議升級方案"""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    plan = tenant.plan if tenant else "free"

    available = get_plan_feature(plan, feature)
    suggestion = get_upgrade_suggestion(plan, feature) if not available else None

    return {
        "feature": feature,
        "available": available,
        "current_plan": plan,
        "upgrade_suggestion": suggestion,
    }


@router.get("/usage/export")
def export_usage(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = Query("csv", regex="^(csv|json)$"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """匯出用量資料（Pro+ 功能）"""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant or not get_plan_feature(tenant.plan or "free", "data_export"):
        suggestion = get_upgrade_suggestion(tenant.plan if tenant else "free", "data_export")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=suggestion or "此功能需要升級方案",
        )

    if current_user.role not in ("owner", "admin") and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要 Owner 或 Admin 角色")

    # Build query
    q = db.query(UsageRecord).filter(UsageRecord.tenant_id == current_user.tenant_id)
    if start_date:
        q = q.filter(UsageRecord.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        q = q.filter(UsageRecord.created_at <= datetime.fromisoformat(end_date))
    records = q.order_by(UsageRecord.created_at.desc()).limit(10_000).all()

    if format == "json":
        data = [
            {
                "id": str(r.id),
                "action": r.action,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "estimated_cost_usd": float(r.estimated_cost_usd) if r.estimated_cost_usd else 0,
                "created_at": str(r.created_at),
            }
            for r in records
        ]
        return data

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Action", "Input Tokens", "Output Tokens", "Cost (USD)", "Created At"])
    for r in records:
        writer.writerow([
            str(r.id),
            r.action,
            r.input_tokens or 0,
            r.output_tokens or 0,
            float(r.estimated_cost_usd) if r.estimated_cost_usd else 0,
            str(r.created_at),
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=usage_export.csv"},
    )
