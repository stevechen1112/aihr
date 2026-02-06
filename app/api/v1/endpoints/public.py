"""
Public Branding API (T4-3)

Unauthenticated endpoint for login page to load tenant branding.
Resolves tenant by custom domain or tenant_id query param.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.models.tenant import Tenant

router = APIRouter()


class BrandingPublic(BaseModel):
    tenant_name: str = ""
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None
    brand_favicon_url: Optional[str] = None


@router.get("/branding", response_model=BrandingPublic)
def get_public_branding(
    request: Request,
    tenant_id: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Public branding endpoint (no auth required).
    Resolve tenant by:
      1. ?domain=hr.example.com  (custom domain lookup)
      2. ?tenant_id=<uuid>       (direct lookup)
      3. Host header             (fallback)
    """
    tenant = None

    if domain:
        tenant = db.query(Tenant).filter(Tenant.custom_domain == domain).first()
    elif tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    else:
        # Try resolving from Host header
        host = request.headers.get("host", "").split(":")[0]
        if host and host not in ("localhost", "127.0.0.1"):
            tenant = db.query(Tenant).filter(Tenant.custom_domain == host).first()

    if not tenant:
        # Return default branding
        return BrandingPublic()

    return BrandingPublic(
        tenant_name=tenant.name,
        brand_name=tenant.brand_name,
        brand_logo_url=tenant.brand_logo_url,
        brand_primary_color=tenant.brand_primary_color,
        brand_secondary_color=tenant.brand_secondary_color,
        brand_favicon_url=tenant.brand_favicon_url,
    )
