"""SSO / OAuth2 endpoints for Google and Microsoft login.

Flow
────
1. Frontend redirects user to provider's auth URL (built client-side with correct client_id)
2. Provider redirects back to frontend callback with ?code=...
3. Frontend POSTs { code, redirect_uri, tenant_id, provider } to /auth/sso/callback
4. Backend exchanges code → tokens → userinfo → issues JWT
"""

from datetime import timedelta
import base64
import hashlib
import hmac
import json
import time
from typing import Any, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.config import settings
from app.core import security
from app.crud import crud_user
from app.models.sso_config import TenantSSOConfig
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.sso import (
    OAuthCallbackRequest,
    SSOConfigCreate,
    SSOConfigUpdate,
    SSOConfigRead,
    SSOConfigPublic,
    SSOStateRequest,
    SSOStateResponse,
)
from app.schemas.token import Token

router = APIRouter()

# ═══════════════════════════════════════════════════
# Provider helpers
# ═══════════════════════════════════════════════════

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

STATE_TTL_SECONDS = 10 * 60


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _sign_state(payload: dict) -> str:
    message = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), msg=message.encode("ascii"), digestmod=hashlib.sha256).digest()
    return f"{message}.{_b64url_encode(sig)}"


def _verify_state(token: str) -> Optional[dict]:
    try:
        message, sig = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        msg=message.encode("ascii"),
        digestmod=hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64url_encode(expected_sig), sig):
        return None

    try:
        payload = json.loads(_b64url_decode(message).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    return payload


async def _exchange_google(
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
    code_verifier: str,
) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        })
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Google token exchange failed: {resp.text}")
        tokens = resp.json()

        resp2 = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        if resp2.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google user info")
        info = resp2.json()
        return {"email": info["email"], "name": info.get("name", ""), "provider": "google"}


async def _exchange_microsoft(
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
    code_verifier: str,
) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(MICROSOFT_TOKEN_URL, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": "openid profile email User.Read",
            "code_verifier": code_verifier,
        })
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Microsoft token exchange failed: {resp.text}")
        tokens = resp.json()

        resp2 = await client.get(MICROSOFT_USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        if resp2.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Microsoft user info")
        info = resp2.json()
        email = info.get("mail") or info.get("userPrincipalName", "")
        return {"email": email, "name": info.get("displayName", ""), "provider": "microsoft"}


# ═══════════════════════════════════════════════════
# Public: discover enabled providers for a tenant
# ═══════════════════════════════════════════════════

@router.get("/sso/providers/{tenant_id}", response_model=List[SSOConfigPublic])
def list_sso_providers(
    tenant_id: UUID,
    db: Session = Depends(deps.get_db),
) -> Any:
    """Return enabled SSO providers for a tenant (no secrets)."""
    configs = (
        db.query(TenantSSOConfig)
        .filter(TenantSSOConfig.tenant_id == tenant_id, TenantSSOConfig.enabled == True)
        .all()
    )
    return configs


@router.post("/sso/state", response_model=SSOStateResponse)
def create_sso_state(
    body: SSOStateRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    """Create a signed OAuth state token for SSO login."""
    cfg = (
        db.query(TenantSSOConfig)
        .filter(
            TenantSSOConfig.tenant_id == body.tenant_id,
            TenantSSOConfig.provider == body.provider,
            TenantSSOConfig.enabled == True,
        )
        .first()
    )
    if not cfg:
        raise HTTPException(status_code=404, detail="SSO provider is not enabled for this tenant")

    payload = {
        "tenant_id": str(body.tenant_id),
        "provider": body.provider,
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    return {"state": _sign_state(payload)}


# ═══════════════════════════════════════════════════
# Public: OAuth callback (frontend → backend code exchange)
# ═══════════════════════════════════════════════════

@router.post("/sso/callback", response_model=Token)
async def sso_callback(
    body: OAuthCallbackRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    """Exchange OAuth authorization code for a UniHR JWT.

    Steps:
    1. Find per-tenant SSO config
    2. Exchange code with provider
    3. Validate email domain
    4. Find or create user
    5. Issue JWT
    """
    # 1. Load SSO config
    sso_cfg = (
        db.query(TenantSSOConfig)
        .filter(
            TenantSSOConfig.tenant_id == body.tenant_id,
            TenantSSOConfig.provider == body.provider,
            TenantSSOConfig.enabled == True,
        )
        .first()
    )
    if not sso_cfg:
        raise HTTPException(status_code=400, detail=f"SSO provider '{body.provider}' is not enabled for this tenant")

    # Verify OAuth state token
    state_payload = _verify_state(body.state)
    if not state_payload:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    if state_payload.get("tenant_id") != str(body.tenant_id) or state_payload.get("provider") != body.provider:
        raise HTTPException(status_code=400, detail="OAuth state does not match request")

    # 2. Exchange code → userinfo
    if body.provider == "google":
        if not body.code_verifier:
            raise HTTPException(status_code=400, detail="Missing code_verifier")
        user_info = await _exchange_google(
            body.code,
            body.redirect_uri,
            sso_cfg.client_id,
            sso_cfg.client_secret,
            body.code_verifier,
        )
    elif body.provider == "microsoft":
        if not body.code_verifier:
            raise HTTPException(status_code=400, detail="Missing code_verifier")
        user_info = await _exchange_microsoft(
            body.code,
            body.redirect_uri,
            sso_cfg.client_id,
            sso_cfg.client_secret,
            body.code_verifier,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")

    email: str = user_info["email"].lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Provider did not return an email address")

    # 3. Domain check
    if sso_cfg.allowed_domains:
        domain = email.split("@")[-1]
        if domain not in sso_cfg.allowed_domains:
            raise HTTPException(status_code=403, detail=f"Email domain '{domain}' is not allowed for this tenant")

    # 4. Find or create user
    user = crud_user.get_by_email(db, email=email)
    if user:
        # ensure belongs to same tenant
        if str(user.tenant_id) != str(body.tenant_id):
            raise HTTPException(status_code=403, detail="User belongs to a different tenant")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is inactive")
    else:
        if not sso_cfg.auto_create_user:
            raise HTTPException(status_code=403, detail="Auto-creation is disabled; contact your admin")
        # Create user with a random unusable password
        import secrets
        from app.schemas.user import UserCreate
        user_in = UserCreate(
            email=email,
            password=secrets.token_urlsafe(32),
            full_name=user_info.get("name", ""),
            tenant_id=body.tenant_id,
            role=sso_cfg.default_role or "employee",
        )
        user = crud_user.create(db, obj_in=user_in)

    # 5. Issue JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.email, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


# ═══════════════════════════════════════════════════
# Admin: manage per-tenant SSO configs (owner/admin only)
# ═══════════════════════════════════════════════════

@router.post("/sso/config", response_model=SSOConfigRead)
def create_sso_config(
    body: SSOConfigCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create (or overwrite) SSO config for the current user's tenant."""
    if current_user.role not in ("owner", "admin") and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    existing = (
        db.query(TenantSSOConfig)
        .filter(
            TenantSSOConfig.tenant_id == current_user.tenant_id,
            TenantSSOConfig.provider == body.provider,
        )
        .first()
    )
    if existing:
        # update in-place
        for field in ("client_id", "client_secret", "enabled", "allowed_domains", "auto_create_user", "default_role"):
            setattr(existing, field, getattr(body, field))
        db.commit()
        db.refresh(existing)
        return existing

    cfg = TenantSSOConfig(
        tenant_id=current_user.tenant_id,
        provider=body.provider,
        client_id=body.client_id,
        client_secret=body.client_secret,
        enabled=body.enabled,
        allowed_domains=body.allowed_domains,
        auto_create_user=body.auto_create_user,
        default_role=body.default_role,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.get("/sso/config", response_model=List[SSOConfigRead])
def list_sso_configs(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List SSO configs for current tenant (owner/admin only)."""
    if current_user.role not in ("owner", "admin") and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    configs = (
        db.query(TenantSSOConfig)
        .filter(TenantSSOConfig.tenant_id == current_user.tenant_id)
        .all()
    )
    return configs


@router.put("/sso/config/{provider}", response_model=SSOConfigRead)
def update_sso_config(
    provider: str,
    body: SSOConfigUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update an existing SSO config."""
    if current_user.role not in ("owner", "admin") and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    cfg = (
        db.query(TenantSSOConfig)
        .filter(
            TenantSSOConfig.tenant_id == current_user.tenant_id,
            TenantSSOConfig.provider == provider,
        )
        .first()
    )
    if not cfg:
        raise HTTPException(status_code=404, detail="SSO config not found")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.delete("/sso/config/{provider}")
def delete_sso_config(
    provider: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Delete SSO config for a provider."""
    if current_user.role not in ("owner", "admin") and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    cfg = (
        db.query(TenantSSOConfig)
        .filter(
            TenantSSOConfig.tenant_id == current_user.tenant_id,
            TenantSSOConfig.provider == provider,
        )
        .first()
    )
    if not cfg:
        raise HTTPException(status_code=404, detail="SSO config not found")
    db.delete(cfg)
    db.commit()
    return {"ok": True}
