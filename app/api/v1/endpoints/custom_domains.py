"""
Custom Domain Management API (T4-6)

Allows tenant Owner/Admin to:
  1. Add a custom domain
  2. Get DNS verification instructions (TXT record)
  3. Verify DNS (checks TXT record)
  4. List / delete custom domains
"""
import hashlib
import logging
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.custom_domain import CustomDomain
from app.models.tenant import Tenant
from app.models.user import User
from app.middleware.custom_domain import invalidate_domain_cache

router = APIRouter()
logger = logging.getLogger("unihr.custom_domain")


# ── Schemas ──

class DomainCreate(BaseModel):
    domain: str


class DomainInfo(BaseModel):
    id: str
    domain: str
    verified: bool
    verification_token: str
    ssl_provisioned: bool
    created_at: Optional[str] = None


class DomainVerifyResult(BaseModel):
    domain: str
    verified: bool
    message: str


# ── Helpers ──

def _ensure_owner_admin(user: User):
    if user.is_superuser:
        return
    if user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="需要 Owner 或 Admin 角色")


def _generate_verification_token(tenant_id: str, domain: str) -> str:
    """Generate a deterministic verification token."""
    raw = f"unihr-verify-{tenant_id}-{domain}-{uuid.uuid4().hex[:8]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ── Endpoints ──

@router.get("/", response_model=List[DomainInfo])
def list_domains(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """列出本租戶的所有自訂域名"""
    _ensure_owner_admin(current_user)
    domains = db.query(CustomDomain).filter(
        CustomDomain.tenant_id == current_user.tenant_id
    ).order_by(CustomDomain.created_at.desc()).all()

    return [
        DomainInfo(
            id=str(d.id),
            domain=d.domain,
            verified=d.verified,
            verification_token=d.verification_token,
            ssl_provisioned=d.ssl_provisioned,
            created_at=str(d.created_at) if d.created_at else None,
        )
        for d in domains
    ]


@router.post("/", response_model=DomainInfo, status_code=201)
def add_domain(
    body: DomainCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """新增自訂域名（需 Pro / Enterprise 方案）"""
    _ensure_owner_admin(current_user)

    # Plan check
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant or tenant.plan not in ("pro", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自訂域名需要 Pro 或 Enterprise 方案",
        )

    domain = body.domain.lower().strip()
    if not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="無效的域名格式")

    # Check uniqueness
    exists = db.query(CustomDomain).filter(CustomDomain.domain == domain).first()
    if exists:
        raise HTTPException(status_code=409, detail="此域名已被使用")

    token = _generate_verification_token(str(current_user.tenant_id), domain)
    record = CustomDomain(
        tenant_id=current_user.tenant_id,
        domain=domain,
        verification_token=token,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    invalidate_domain_cache(domain)

    logger.info("Custom domain added: %s for tenant %s", domain, current_user.tenant_id)

    return DomainInfo(
        id=str(record.id),
        domain=record.domain,
        verified=record.verified,
        verification_token=record.verification_token,
        ssl_provisioned=record.ssl_provisioned,
        created_at=str(record.created_at) if record.created_at else None,
    )


@router.post("/{domain_id}/verify", response_model=DomainVerifyResult)
def verify_domain(
    domain_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    驗證域名 DNS TXT 記錄

    租戶須在 DNS 中新增 TXT 記錄：
      _unihr-verify.{domain}  →  {verification_token}
    """
    _ensure_owner_admin(current_user)

    record = db.query(CustomDomain).filter(
        CustomDomain.id == domain_id,
        CustomDomain.tenant_id == current_user.tenant_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="域名不存在")

    if record.verified:
        if record.ssl_provisioned:
            return DomainVerifyResult(domain=record.domain, verified=True, message="域名已驗證")
        return DomainVerifyResult(
            domain=record.domain,
            verified=True,
            message="域名已驗證，等待 SSL 憑證完成後即可啟用",
        )

    # Attempt DNS TXT lookup
    verified = False
    try:
        import dns.resolver
        answers = dns.resolver.resolve(f"_unihr-verify.{record.domain}", "TXT")
        for rdata in answers:
            txt_value = rdata.to_text().strip('"')
            if txt_value == record.verification_token:
                verified = True
                break
    except ImportError:
        # dnspython not installed — allow manual verification via admin
        logger.warning("dnspython not installed, skipping DNS verification for %s", record.domain)
        return DomainVerifyResult(
            domain=record.domain,
            verified=False,
            message="DNS 驗證模組未安裝，請聯繫系統管理員",
        )
    except Exception as e:
        logger.info("DNS verification failed for %s: %s", record.domain, e)

    if verified:
        from datetime import datetime, timezone
        record.verified = True
        record.verified_at = datetime.now(timezone.utc)
        if record.ssl_provisioned:
            # Only activate custom domain after SSL is ready
            tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
            if tenant:
                tenant.custom_domain = record.domain
        db.commit()
        invalidate_domain_cache(record.domain)
        logger.info("Domain verified: %s", record.domain)
        if record.ssl_provisioned:
            return DomainVerifyResult(domain=record.domain, verified=True, message="域名驗證成功！")
        return DomainVerifyResult(
            domain=record.domain,
            verified=True,
            message="域名驗證成功，等待 SSL 憑證完成後即可啟用",
        )
    else:
        return DomainVerifyResult(
            domain=record.domain,
            verified=False,
            message=f"驗證失敗。請在 DNS 新增 TXT 記錄：_unihr-verify.{record.domain} → {record.verification_token}",
        )


@router.delete("/{domain_id}")
def delete_domain(
    domain_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """刪除自訂域名"""
    _ensure_owner_admin(current_user)

    record = db.query(CustomDomain).filter(
        CustomDomain.id == domain_id,
        CustomDomain.tenant_id == current_user.tenant_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="域名不存在")

    domain_name = record.domain

    # Clear tenant custom_domain if it matches
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant and tenant.custom_domain == domain_name:
        tenant.custom_domain = None

    db.delete(record)
    db.commit()
    invalidate_domain_cache(domain_name)

    logger.info("Custom domain deleted: %s", domain_name)
    return {"message": f"域名 {domain_name} 已刪除"}
