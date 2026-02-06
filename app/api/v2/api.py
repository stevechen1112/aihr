"""API v2 router.

Strategy: v2 re-exports all v1 routes unchanged, plus any v2-specific
overrides. This gives a smooth migration path:
  - Clients on /api/v1/* keep working (deprecated but functional)
  - Clients on /api/v2/* get the same behaviour plus new endpoints
  - When v1 is sunset, just remove the v1 include from main.py

To override a v1 endpoint in v2:
  1. Create the new handler in app/api/v2/endpoints/
  2. Include it in this router with the same prefix
  3. FastAPI matches the first route, so v2 overrides appear first
"""

from fastapi import APIRouter

# Import ALL v1 routers (re-export as baseline)
from app.api.v1.endpoints import (
    auth, tenants, users, documents, kb, chat,
    audit, departments, admin, sso, feature_flags,
)

api_v2_router = APIRouter()

# ─── v2-specific overrides go here (add before v1 re-exports) ───
# Example:
# from app.api.v2.endpoints import chat_v2
# api_v2_router.include_router(chat_v2.router, prefix="/chat", tags=["chat-v2"])

# ─── Re-export all v1 routes as v2 baseline ───
api_v2_router.include_router(auth.router, prefix="/auth", tags=["login"])
api_v2_router.include_router(sso.router, prefix="/auth", tags=["sso"])
api_v2_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_v2_router.include_router(users.router, prefix="/users", tags=["users"])
api_v2_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v2_router.include_router(kb.router, prefix="/kb", tags=["knowledge-base"])
api_v2_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v2_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_v2_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_v2_router.include_router(admin.router, prefix="/admin", tags=["platform-admin"])
api_v2_router.include_router(feature_flags.router, prefix="/feature-flags", tags=["feature-flags"])
