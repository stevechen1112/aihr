"""
HttpOnly cookie-based session management.

Tokens are set as HttpOnly Secure SameSite cookies.
Access token: short-lived (30 min), HttpOnly cookie.
Refresh token: long-lived, HttpOnly cookie, path-restricted to /api/v1/auth/refresh.
CSRF token: non-HttpOnly cookie readable by JS, validated on state-changing requests.
"""
import secrets
from fastapi import Response, Request, HTTPException, status

from app.config import settings

# Cookie names
ACCESS_COOKIE = "unihr_access"
REFRESH_COOKIE = "unihr_refresh"
CSRF_COOKIE = "unihr_csrf"
CSRF_HEADER = "X-CSRF-Token"

# Cookie config
_SECURE = settings.COOKIE_SECURE if settings.COOKIE_SECURE is not None else settings.APP_ENV in ("production", "staging")
_SAMESITE = "lax"
_DOMAIN = None  # browser will scope to the current domain


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,
    csrf_token: str | None = None,
) -> None:
    """Set HttpOnly auth cookies on the response."""
    if csrf_token is None:
        csrf_token = generate_csrf_token()

    # Access token — HttpOnly, short-lived
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=_SECURE,
        samesite=_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    # Refresh token — HttpOnly, path-restricted
    if refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=refresh_token,
            httponly=True,
            secure=_SECURE,
            samesite=_SAMESITE,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            path="/api/v1/auth/refresh",
        )

    # CSRF token — NOT HttpOnly (JS must read it), but Secure + SameSite
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=_SECURE,
        samesite=_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove all auth cookies."""
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth/refresh")
    response.delete_cookie(CSRF_COOKIE, path="/")


def extract_access_token(request: Request) -> str | None:
    """Extract access token from cookie first, then fall back to Authorization header."""
    # 1. Try cookie
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        return token

    # 2. Fall back to Bearer header (backward compatibility / mobile clients)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def extract_refresh_token(request: Request) -> str | None:
    """Extract refresh token from cookie first, then body."""
    return request.cookies.get(REFRESH_COOKIE)


def validate_csrf(request: Request) -> None:
    """Validate CSRF token on state-changing requests.

    Compares the CSRF cookie value against the X-CSRF-Token header.
    GET/HEAD/OPTIONS are exempt.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    cookie_csrf = request.cookies.get(CSRF_COOKIE)
    header_csrf = request.headers.get(CSRF_HEADER)

    if not cookie_csrf or not header_csrf:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF token",
        )

    if not secrets.compare_digest(cookie_csrf, header_csrf):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )
