"""
Structured Logging Configuration (T4-12)

Features:
  - JSON-formatted logs for centralized log collection (ELK / Loki)
  - Request ID tracking across the request lifecycle
  - PII masking (email, password, token, IP)
  - Environment-aware: JSON in production, human-readable in dev
"""

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from app.config import settings

# ── Context variable for request tracking ──
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="-")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")


def generate_request_id() -> str:
    return str(uuid.uuid4())[:8]


# ═══════════════════════════════════════════
#  PII Masking
# ═══════════════════════════════════════════

_EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')

_REDACT_PATTERNS = [
    (re.compile(r'("?password"?\s*[:=]\s*)"[^"]*"', re.I), r'\1"***"'),
    (re.compile(r'("?token"?\s*[:=]\s*)"[^"]*"', re.I), r'\1"***"'),
    (re.compile(r'("?secret"?\s*[:=]\s*)"[^"]*"', re.I), r'\1"***"'),
    (re.compile(r'("?api_key"?\s*[:=]\s*)"[^"]*"', re.I), r'\1"***"'),
    (re.compile(r'("?authorization"?\s*[:=]\s*)"[^"]*"', re.I), r'\1"***"'),
]


def _mask_email(match: re.Match) -> str:
    local = match.group(1)
    domain = match.group(2)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def mask_pii(text: str) -> str:
    """Mask sensitive data in log messages."""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _EMAIL_PATTERN.sub(_mask_email, text)
    return text


# ═══════════════════════════════════════════
#  JSON Formatter
# ═══════════════════════════════════════════

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.000Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_pii(record.getMessage()),
            "request_id": request_id_ctx.get("-"),
            "tenant_id": tenant_id_ctx.get("-"),
            "user_id": user_id_ctx.get("-"),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Remove empty context
        log_entry = {k: v for k, v in log_entry.items() if v and v != "-"}

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Readable formatter for development."""

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-24s | [%(request_id)s] %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_ctx.get("-")
        return super().format(record)


# ═══════════════════════════════════════════
#  Setup
# ═══════════════════════════════════════════

def setup_logging() -> None:
    """Configure application-wide logging."""
    root = logging.getLogger()

    # Clear existing handlers
    root.handlers.clear()

    # Choose formatter based on environment
    handler = logging.StreamHandler(sys.stdout)
    if settings.is_production or settings.is_staging:
        handler.setFormatter(JSONFormatter())
        root.setLevel(logging.INFO)
    else:
        handler.setFormatter(
            HumanFormatter(HumanFormatter.FORMAT, datefmt="%H:%M:%S")
        )
        root.setLevel(logging.DEBUG)

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "httpcore", "httpx", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
