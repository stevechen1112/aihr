"""
IP Whitelist Middleware for Admin API Network Isolation (T4-4)

Restricts access to admin-only API endpoints (/api/v1/admin/*, /api/v1/analytics/*)
to requests originating from whitelisted IP addresses or CIDR ranges.

Configuration via environment variables:
  ADMIN_IP_WHITELIST: comma-separated list of IPs/CIDRs (default: 127.0.0.1,::1)
  ADMIN_IP_WHITELIST_ENABLED: true/false (default: false in dev, true in prod)
"""

import ipaddress
import logging
from typing import Sequence

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Admin-only path prefixes ───
ADMIN_PATH_PREFIXES = (
    "/api/v1/admin",
    "/api/v1/analytics",
    "/api/v1/admin/",
    "/api/v1/analytics/",
)


def parse_whitelist(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse comma-separated IP/CIDR string into network objects."""
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            # Try as network first (e.g. 10.0.0.0/8)
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Invalid IP/CIDR in ADMIN_IP_WHITELIST: %s", entry)
    return networks


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For behind reverse proxy."""
    # Trust X-Forwarded-For if set (Nginx / load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First entry is the original client
        return forwarded.split(",")[0].strip()

    x_real = request.headers.get("X-Real-IP")
    if x_real:
        return x_real.strip()

    # Direct connection
    if request.client:
        return request.client.host
    return "0.0.0.0"


def is_ip_allowed(
    client_ip: str,
    whitelist: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    """Check if the client IP is within any whitelisted network."""
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    return any(addr in net for net in whitelist)


class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware that blocks non-whitelisted IPs from admin API endpoints.

    Enabled via ADMIN_IP_WHITELIST_ENABLED env var.
    Whitelist configured via ADMIN_IP_WHITELIST env var (comma-separated IPs/CIDRs).
    """

    def __init__(self, app, **kwargs):  # type: ignore
        super().__init__(app, **kwargs)
        self.enabled: bool = getattr(settings, "ADMIN_IP_WHITELIST_ENABLED", False)
        raw_whitelist: str = getattr(settings, "ADMIN_IP_WHITELIST", "127.0.0.1,::1")
        self.whitelist = parse_whitelist(raw_whitelist)

        if self.enabled:
            logger.info(
                "Admin IP whitelist enabled — allowed networks: %s",
                [str(n) for n in self.whitelist],
            )
        else:
            logger.info("Admin IP whitelist is DISABLED (development mode)")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Only check admin paths
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in ADMIN_PATH_PREFIXES):
            return await call_next(request)

        # Check client IP
        client_ip = get_client_ip(request)
        if is_ip_allowed(client_ip, self.whitelist):
            return await call_next(request)

        # Blocked
        logger.warning(
            "Admin API access denied — IP=%s path=%s", client_ip, path
        )
        return Response(
            content='{"detail":"Access denied: IP not in admin whitelist"}',
            status_code=403,
            media_type="application/json",
        )
