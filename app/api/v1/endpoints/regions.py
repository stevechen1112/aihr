"""
多區域管理 API（T4-19）
========================

提供區域資訊查詢、Tenant 區域遷移（Superuser Only）。
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.api.deps_permissions import require_superuser
from app.models.user import User
from app.models.tenant import Tenant
from app.services.region import (
    get_all_regions,
    get_region_config,
    SUPPORTED_REGIONS,
    DEFAULT_REGION,
)

router = APIRouter()


# ═══════════════════════════════════════════
#  Schemas
# ═══════════════════════════════════════════

class RegionInfo(BaseModel):
    code: str
    name: str
    display_name_zh: str
    data_residency: str
    compliance_notes: str


class TenantRegionUpdate(BaseModel):
    region: str


class TenantRegionResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    region: str
    data_residency: str


class DataResidencyReport(BaseModel):
    tenant_id: str
    tenant_name: str
    region: str
    region_name: str
    data_residency: str
    compliance_notes: str
    db_location: str
    redis_location: str
    pinecone_index: str


# ═══════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════

@router.get("/regions", response_model=List[RegionInfo])
async def list_regions():
    """
    列出所有支援的部署區域。

    公開端點，無需認證。
    """
    return get_all_regions()


@router.get("/regions/current")
async def get_current_region():
    """取得本機所在區域"""
    import os
    local = os.getenv("LOCAL_REGION", DEFAULT_REGION)
    config = get_region_config(local)
    return {
        "region": local,
        "name": config.name,
        "display_name_zh": config.display_name_zh,
    }


@router.get("/tenants/{tenant_id}/region", response_model=TenantRegionResponse)
async def get_tenant_region(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """
    查看租戶的區域設定（Superuser Only）。
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    region = getattr(tenant, "region", DEFAULT_REGION)
    config = get_region_config(region)

    return TenantRegionResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        region=region,
        data_residency=config.data_residency,
    )


@router.put("/tenants/{tenant_id}/region", response_model=TenantRegionResponse)
async def update_tenant_region(
    tenant_id: UUID,
    body: TenantRegionUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """
    變更租戶的區域設定（Superuser Only）。

    ⚠️ 注意：變更區域後需手動執行資料遷移：
    1. 匯出原區域的 tenant 資料
    2. 匯入新區域的資料庫
    3. 遷移 Pinecone 向量資料
    4. 更新 DNS / 路由規則

    此端點僅更新 metadata，不自動遷移資料。
    """
    if body.region not in SUPPORTED_REGIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported region: {body.region}. "
                   f"Supported: {', '.join(SUPPORTED_REGIONS)}",
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_region = getattr(tenant, "region", DEFAULT_REGION)
    tenant.region = body.region
    db.commit()
    db.refresh(tenant)

    config = get_region_config(body.region)

    return TenantRegionResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        region=body.region,
        data_residency=config.data_residency,
    )


@router.get(
    "/tenants/{tenant_id}/data-residency",
    response_model=DataResidencyReport,
)
async def get_data_residency_report(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """
    產出資料落地合規報告（Superuser Only）。

    用於向客戶證明資料儲存位置，滿足 GDPR / PDPA / APPI 等合規要求。
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    region = getattr(tenant, "region", DEFAULT_REGION)
    config = get_region_config(region)

    return DataResidencyReport(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        region=region,
        region_name=config.name,
        data_residency=config.data_residency,
        compliance_notes=config.compliance_notes,
        db_location=f"{config.db_host}:{config.db_port}",
        redis_location=f"{config.redis_host}:{config.redis_port}",
        pinecone_index=f"{config.pinecone_index_prefix}-*",
    )


@router.get("/compliance/summary")
async def get_compliance_summary(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_superuser),
) -> Any:
    """
    全平台資料合規摘要（Superuser Only）。

    統計各區域的租戶數量，供合規審計使用。
    """
    from sqlalchemy import func

    # 查詢各區域的租戶數
    region_counts = (
        db.query(
            Tenant.region,
            func.count(Tenant.id).label("tenant_count"),
        )
        .group_by(Tenant.region)
        .all()
    )

    summary = []
    for region_code, count in region_counts:
        config = get_region_config(region_code or DEFAULT_REGION)
        summary.append({
            "region": region_code or DEFAULT_REGION,
            "region_name": config.name,
            "tenant_count": count,
            "data_residency": config.data_residency,
            "compliance_notes": config.compliance_notes,
        })

    return {
        "total_tenants": sum(item["tenant_count"] for item in summary),
        "regions": summary,
        "supported_regions": get_all_regions(),
    }
