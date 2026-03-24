from fastapi import Request
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.cookie_auth import validate_csrf, ACCESS_COOKIE, REFRESH_COOKIE


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token for cookie-authenticated unsafe requests."""

    EXEMPT_PATHS = {
        "/api/v1/auth/login/access-token",
        "/api/v1/auth/register",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/accept-invite",
        "/api/v1/auth/sso/callback",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/payment/notify",
        "/api/v1/payment/return",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        has_cookie_auth = bool(request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE))

        if has_cookie_auth and path not in self.EXEMPT_PATHS:
            try:
                validate_csrf(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                )

        return await call_next(request)