"""
Custom Domain Resolution Middleware (T4-6)

Resolves tenant from Host header when a custom domain is configured.
Sets request.state.resolved_tenant_id for downstream handlers.
"""

import logging
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("unihr.domain")

# In-memory cache for domain → tenant_id mapping (None = confirmed not a custom domain)
_DOMAIN_CACHE: dict[str, str | None] = {}

# Regex to detect bare IP addresses (IPv4 or IPv6)
_IP_RE = re.compile(r'^[\d.:]+$')


class CustomDomainMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        host = request.headers.get("host", "").split(":")[0].lower()

        # Skip for well-known / non-custom-domain hosts.
        # - Internal docker hostnames often have no dot (e.g. "web")
        # - sslip.io is our infra/testing domain, not a tenant custom domain
        # - Plain IP addresses are never custom domains
        if (
            host in ("localhost", "127.0.0.1", "")
            or "." not in host
            or host.endswith(".sslip.io")
            or _IP_RE.match(host)
        ):
            return await call_next(request)

        # Check cache first (None = already looked up, not a custom domain)
        if host in _DOMAIN_CACHE:
            tenant_id = _DOMAIN_CACHE[host]
            if tenant_id:
                request.state.resolved_tenant_id = tenant_id
            return await call_next(request)

        # Lookup in database
        try:
            from app.db.session import SessionLocal
            from app.models.custom_domain import CustomDomain

            db = SessionLocal()
            try:
                record = db.query(CustomDomain).filter(
                    CustomDomain.domain == host,
                    CustomDomain.verified == True,
                ).first()
                if record:
                    _DOMAIN_CACHE[host] = str(record.tenant_id)
                    request.state.resolved_tenant_id = str(record.tenant_id)
                    logger.debug("Resolved custom domain %s → tenant %s", host, record.tenant_id)
                else:
                    # Cache negative result to avoid repeated DB lookups
                    _DOMAIN_CACHE[host] = None
            finally:
                db.close()
        except Exception as e:
            logger.warning("Custom domain resolution failed for %s: %s", host, e)

        return await call_next(request)


def invalidate_domain_cache(domain: str | None = None) -> None:
    """Clear domain cache when domains are added/removed."""
    if domain:
        _DOMAIN_CACHE.pop(domain, None)
    else:
        _DOMAIN_CACHE.clear()
