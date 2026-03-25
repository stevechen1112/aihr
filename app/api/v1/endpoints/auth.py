import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.cookie_auth import set_auth_cookies, clear_auth_cookies, extract_refresh_token
from app.core.redis_client import get_redis_client
from app.crud import crud_user, crud_tenant
from app.schemas.token import Token
from app.schemas.user import UserCreate
from app.schemas.tenant import TenantCreate
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
router = APIRouter()

# ═══════════════════════════════════════════
#  Production security helpers
# ═══════════════════════════════════════════

_PASSWORD_MIN_LEN = 8
_PASSWORD_MAX_LEN = 72  # bcrypt limit
_NAME_MAX_LEN = 100
_COMPANY_MAX_LEN = 200


def _validate_password_strength(password: str) -> Optional[str]:
    """Return error message if password is weak, None if ok."""
    if len(password) < _PASSWORD_MIN_LEN:
        return f"密碼至少需要 {_PASSWORD_MIN_LEN} 個字元"
    if len(password) > _PASSWORD_MAX_LEN:
        return f"密碼不可超過 {_PASSWORD_MAX_LEN} 個字元"
    if not re.search(r"[A-Za-z]", password):
        return "密碼必須包含至少一個英文字母"
    if not re.search(r"\d", password):
        return "密碼必須包含至少一個數字"
    common = {"password", "12345678", "qwerty12", "abcd1234", "password1", "admin123"}
    if password.lower() in common:
        return "此密碼過於常見，請選擇更安全的密碼"
    return None


def _check_auth_rate_limit(key: str, max_attempts: int, window: int) -> None:
    """Raise 429 if rate limit exceeded. key should include IP or email."""
    rc = get_redis_client()
    if rc is None:
        return
    rl_key = f"auth_rl:{key}"
    try:
        count = rc.incr(rl_key)
        if count == 1:
            rc.expire(rl_key, window)
        if count > max_attempts:
            ttl = rc.ttl(rl_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"操作過於頻繁，請 {max(ttl, 1)} 秒後再試",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis failure → allow


def _check_login_lockout(email: str) -> None:
    """Lock account for 15 min after 5 failed login attempts."""
    rc = get_redis_client()
    if rc is None:
        return
    lock_key = f"login_locked:{email}"
    if rc.get(lock_key):
        ttl = rc.ttl(lock_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"帳號因多次登入失敗已暫時鎖定，請 {max(ttl // 60, 1)} 分鐘後再試",
        )


def _record_login_failure(email: str) -> None:
    rc = get_redis_client()
    if rc is None:
        return
    fail_key = f"login_fail:{email}"
    try:
        count = rc.incr(fail_key)
        if count == 1:
            rc.expire(fail_key, 900)  # 15 min window
        if count >= 5:
            rc.setex(f"login_locked:{email}", 900, "1")  # lock 15 min
    except Exception:
        pass


def _clear_login_failures(email: str) -> None:
    rc = get_redis_client()
    if rc is None:
        return
    try:
        rc.delete(f"login_fail:{email}", f"login_locked:{email}")
    except Exception:
        pass


def _is_admin_mfa_user(user) -> bool:
    return bool(user.is_superuser or user.role in {"owner", "admin"})


def _issue_tokens_with_cookies(response: Response, user_email: str) -> dict:
    """Issue access + refresh tokens and set HttpOnly cookies on the response."""
    from app.config import settings as cfg

    access_token = security.create_access_token(
        user_email, expires_delta=timedelta(minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token, jti = security.create_refresh_token(user_email)

    # Store refresh jti in Redis
    rc = get_redis_client()
    if rc:
        rc.setex(f"refresh:{jti}", cfg.REFRESH_TOKEN_EXPIRE_DAYS * 86400, user_email)

    # Set HttpOnly cookies
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "token_type": "bearer",
    }


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(f"login_ip:{client_ip}", max_attempts=20, window=60)
    _check_login_lockout(form_data.username)

    user = crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        _record_login_failure(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    elif not user.email_verified:
        # Actually resend verification email
        try:
            _token = security.create_email_verification_token(user.email)
            from app.services.email_service import send_email_verification
            send_email_verification(user.email, user.full_name or "", _token)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="請先完成電子郵件驗證，已重新寄送驗證信至您的信箱。",
        )

    _clear_login_failures(form_data.username)

    if _is_admin_mfa_user(user) and user.mfa_enabled:
        return {
            "token_type": "bearer",
            "mfa_required": True,
            "mfa_token": security.create_mfa_login_token(user.email),
        }

    return _issue_tokens_with_cookies(response, user.email)


class MFAVerifyLoginRequest(BaseModel):
    mfa_token: str
    code: str


@router.post("/mfa/verify-login", response_model=Token)
def verify_mfa_login(
    body: MFAVerifyLoginRequest,
    response: Response,
    db: Session = Depends(deps.get_db),
) -> Any:
    email = security.verify_mfa_login_token(body.mfa_token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA challenge expired or invalid",
        )

    user = crud_user.get_by_email(db, email=email)
    if not user or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA challenge is no longer valid",
        )

    if not security.verify_totp(user.mfa_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="驗證碼錯誤",
        )

    return _issue_tokens_with_cookies(response, user.email)


# ═══════════════════════════════════════════
#  Refresh Token Rotation
# ═══════════════════════════════════════════

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = None,
) -> Any:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is invalidated (single-use rotation).
    """
    refresh_token = extract_refresh_token(request) or (body.refresh_token if body else None)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    payload = security.verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    jti = payload.get("jti")
    email = payload.get("sub")

    # Check if refresh token has already been used (Redis)
    from app.core.redis_client import get_redis_client
    rc = get_redis_client()
    if rc:
        stored = rc.get(f"refresh:{jti}")
        if stored is None:
            # Token was already rotated or revoked — possible token theft
            # Revoke all refresh tokens for this user as a precaution
            # (scan is acceptable here since this is a rare security event)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token already used or revoked",
            )
        # Invalidate old token
        rc.delete(f"refresh:{jti}")

    # Verify user still exists and is active
    db = SessionLocal()
    try:
        user = crud_user.get_by_email(db, email=email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
    finally:
        db.close()

    return _issue_tokens_with_cookies(response, user.email)


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    refresh_token = extract_refresh_token(request)
    if refresh_token:
        payload = security.verify_refresh_token(refresh_token)
        jti = payload.get("jti") if payload else None
        rc = get_redis_client()
        if rc and jti:
            try:
                rc.delete(f"refresh:{jti}")
            except Exception:
                pass
    clear_auth_cookies(response)
    return {"msg": "Logged out"}


# ═══════════════════════════════════════════
#  公開自助註冊
# ═══════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    agree_terms: bool = False

    @field_validator("full_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > _NAME_MAX_LEN:
            raise ValueError(f"姓名不可為空且不可超過 {_NAME_MAX_LEN} 個字元")
        return v

    @field_validator("company_name")
    @classmethod
    def _check_company(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > _COMPANY_MAX_LEN:
            raise ValueError(f"公司名稱不可為空且不可超過 {_COMPANY_MAX_LEN} 個字元")
        return v


@router.post("/register")
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> dict:
    """
    Public self-service registration.
    Creates tenant (Free plan) + owner user, sends verification email.
    """
    # Rate limit: 5 registrations per IP per 10 min
    client_ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(f"register_ip:{client_ip}", max_attempts=5, window=600)

    if not body.agree_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您必須同意服務條款與隱私權政策才能註冊",
        )

    pw_err = _validate_password_strength(body.password)
    if pw_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    # Check duplicate email
    if crud_user.get_by_email(db, email=body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="此電子郵件已被註冊",
        )

    # Check duplicate company name
    if crud_tenant.get_by_name(db, name=body.company_name.strip()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="此公司名稱已被使用",
        )

    # 1. Create tenant with Free plan
    tenant = crud_tenant.create(
        db, obj_in=TenantCreate(name=body.company_name.strip(), plan="free")
    )
    tenant_id = tenant.id  # capture before potential rollback

    # 2. Create owner user
    try:
        user_in = UserCreate(
            email=body.email,
            full_name=body.full_name.strip(),
            password=body.password,
            tenant_id=tenant.id,
            role="owner",
        )
        new_user = crud_user.create(db, obj_in=user_in)
    except IntegrityError:
        db.rollback()
        # Clean up orphaned tenant (race condition: duplicate email slipped past check)
        from sqlalchemy import text
        db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": str(tenant_id)})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="此電子郵件已被註冊",
        )

    # Record consent
    new_user.agreed_to_terms = True
    new_user.agreed_at = datetime.now(timezone.utc)
    db.commit()

    # 3. Send verification email
    try:
        verify_token = security.create_email_verification_token(new_user.email)
        from app.services.email_service import send_email_verification
        send_email_verification(new_user.email, new_user.full_name or "", verify_token)
    except Exception:
        pass

    return {"msg": "註冊成功！請至信箱收取驗證信。", "email": new_user.email}


class VerifyEmailRequest(BaseModel):
    token: str


@router.post("/verify-email")
def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> dict:
    """Verify email address using the token from verification email."""
    client_ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(f"verify_ip:{client_ip}", max_attempts=10, window=60)

    email = security.verify_email_verification_token(body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="驗證連結無效或已過期",
        )

    # Single-use: check if token already consumed
    rc = get_redis_client()
    token_hash = security.get_password_hash(body.token)[:32]  # short hash as key
    used_key = f"ev_used:{token_hash}"
    if rc:
        if rc.get(used_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此驗證連結已使用過",
            )

    user = crud_user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到此帳號",
        )

    if user.email_verified:
        return {"msg": "電子郵件已驗證", "already_verified": True}

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    db.commit()

    # Mark token as consumed (24h TTL matches token lifetime)
    if rc:
        try:
            rc.setex(used_key, 86400, "1")
        except Exception:
            pass

    # Send welcome email
    try:
        from app.services.email_service import send_welcome_email
        send_welcome_email(user.email, user.full_name or "")
    except Exception:
        pass

    # Schedule onboarding drip
    try:
        from app.tasks.onboarding_tasks import schedule_onboarding_sequence
        schedule_onboarding_sequence(str(user.id), str(user.tenant_id))
    except Exception:
        pass

    return {"msg": "電子郵件驗證成功！", "already_verified": False}


class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/resend-verification")
def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> dict:
    """Resend verification email. Always returns success to prevent enumeration."""
    # Rate limit: 3 resends per IP per 5 min
    client_ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(f"resend_ip:{client_ip}", max_attempts=3, window=300)

    user = crud_user.get_by_email(db, email=body.email)
    if user and not user.email_verified:
        try:
            token = security.create_email_verification_token(user.email)
            from app.services.email_service import send_email_verification
            send_email_verification(user.email, user.full_name or "", token)
        except Exception:
            pass
    return {"msg": "如果帳號存在，驗證信已重新寄出。"}


# ═══════════════════════════════════════════
#  忘記密碼 / 重設密碼
# ═══════════════════════════════════════════

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(deps.get_db),
) -> dict:
    """
    Send a password-reset email.
    Always returns success to prevent email enumeration.
    """
    user = crud_user.get_by_email(db, email=body.email)
    if user and user.is_active:
        token = security.create_password_reset_token(user.email)
        from app.services.email_service import send_password_reset_email
        send_password_reset_email(user.email, token)
    # Always return 200 to prevent email enumeration
    return {"msg": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(deps.get_db),
) -> dict:
    """
    Reset password using a valid reset token.
    """
    email = security.verify_password_reset_token(body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    user = crud_user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    pw_err = _validate_password_strength(body.new_password)
    if pw_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)
    user.hashed_password = security.get_password_hash(body.new_password)
    db.commit()
    return {"msg": "Password updated successfully"}


# ═══════════════════════════════════════════
#  Email 邀請 — 接受邀請
# ═══════════════════════════════════════════

class AcceptInviteRequest(BaseModel):
    token: str
    full_name: str
    password: str
    agree_terms: bool = False


@router.post("/accept-invite")
def accept_invite(
    body: AcceptInviteRequest,
    db: Session = Depends(deps.get_db),
) -> dict:
    """
    Accept a tenant invitation token and create the user account.
    """
    pw_err = _validate_password_strength(body.password)
    if pw_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    if not body.agree_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您必須同意服務條款與隱私權政策才能建立帳號",
        )

    payload = security.verify_invite_token(body.token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token",
        )

    email = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "employee")

    # Prevent duplicate signup
    existing = crud_user.get_by_email(db, email=email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email has already been registered",
        )

    user_in = UserCreate(
        email=email,
        full_name=body.full_name,
        password=body.password,
        tenant_id=UUID(tenant_id),
        role=role,
    )
    new_user = crud_user.create(db, obj_in=user_in)

    # Record PDPA consent timestamp + mark email as verified (invite flow)
    new_user.agreed_to_terms = True
    new_user.agreed_at = datetime.now(timezone.utc)
    new_user.email_verified = True
    new_user.email_verified_at = datetime.now(timezone.utc)
    db.commit()

    # Send welcome email (best-effort)
    try:
        from app.services.email_service import send_welcome_email
        send_welcome_email(new_user.email, new_user.full_name or "")
    except Exception:
        pass

    # Schedule onboarding drip sequence (Day 1 + Day 3)
    try:
        from app.tasks.onboarding_tasks import schedule_onboarding_sequence
        schedule_onboarding_sequence(str(new_user.id), tenant_id)
    except Exception:
        pass

    return {"msg": "Account created successfully", "email": new_user.email}


class MFAStatusResponse(BaseModel):
    enabled: bool
    eligible: bool
    enabled_at: datetime | None = None


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    setup_token: str


class MFAEnableRequest(BaseModel):
    setup_token: str
    code: str


class MFADisableRequest(BaseModel):
    password: str
    code: str


@router.get("/mfa/status", response_model=MFAStatusResponse)
def get_mfa_status(
    current_user=Depends(deps.get_current_active_user),
) -> Any:
    return MFAStatusResponse(
        enabled=bool(current_user.mfa_enabled),
        eligible=_is_admin_mfa_user(current_user),
        enabled_at=current_user.mfa_enabled_at,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
def setup_mfa(
    current_user=Depends(deps.get_current_active_user),
) -> Any:
    if not _is_admin_mfa_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有 owner、admin 或平台管理員可以啟用 2FA",
        )

    secret = security.generate_totp_secret()
    return MFASetupResponse(
        secret=secret,
        otpauth_uri=security.build_totp_uri(current_user.email, secret),
        setup_token=security.create_mfa_setup_token(current_user.email, secret),
    )


@router.post("/mfa/enable", response_model=MFAStatusResponse)
def enable_mfa(
    body: MFAEnableRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
) -> Any:
    if not _is_admin_mfa_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有 owner、admin 或平台管理員可以啟用 2FA",
        )

    payload = security.verify_mfa_setup_token(body.setup_token)
    if not payload or payload.get("sub") != current_user.email:
        raise HTTPException(status_code=400, detail="2FA 設定已失效，請重新產生")

    secret = payload.get("secret")
    if not secret or not security.verify_totp(secret, body.code):
        raise HTTPException(status_code=400, detail="驗證碼錯誤")

    user = crud_user.get_by_email(db, email=current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.mfa_enabled = True
    user.mfa_secret = secret
    user.mfa_enabled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return MFAStatusResponse(
        enabled=True,
        eligible=True,
        enabled_at=user.mfa_enabled_at,
    )


@router.post("/mfa/disable", response_model=MFAStatusResponse)
def disable_mfa(
    body: MFADisableRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
) -> Any:
    user = crud_user.get_by_email(db, email=current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="尚未啟用 2FA")
    if not security.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="密碼錯誤")
    if not security.verify_totp(user.mfa_secret, body.code):
        raise HTTPException(status_code=400, detail="驗證碼錯誤")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_enabled_at = None
    db.commit()

    return MFAStatusResponse(enabled=False, eligible=_is_admin_mfa_user(user), enabled_at=None)
