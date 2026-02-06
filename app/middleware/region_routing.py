"""
多區域路由中間件（T4-19）
===========================

根據 Tenant 的 region 欄位，決定請求應轉發至哪個區域的服務。
在單區域部署時此中間件為 pass-through。
"""

import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.region import get_region_config, DEFAULT_REGION, SUPPORTED_REGIONS

logger = logging.getLogger("unihr.middleware.region")

# 本機所在區域（部署時設定）
LOCAL_REGION = os.getenv("LOCAL_REGION", DEFAULT_REGION)

# 是否啟用多區域路由（單區域部署時關閉）
MULTI_REGION_ENABLED = os.getenv("MULTI_REGION_ENABLED", "false").lower() == "true"


class RegionRoutingMiddleware(BaseHTTPMiddleware):
    """
    多區域路由中間件。

    工作流程：
    1. 從 request state 取得 tenant（由 CustomDomainMiddleware 或認證層設定）
    2. 比對 tenant.region 與 LOCAL_REGION
    3. 如果不符，回傳 302 重導向至正確區域的 API 端點
    4. 如果相符，正常處理

    注意：需放在認證/tenant 解析之後。
    """

    async def dispatch(self, request: Request, call_next):
        # 未啟用多區域時直接 pass-through
        if not MULTI_REGION_ENABLED:
            return await call_next(request)

        # 跳過不需要區域路由的路徑
        path = request.url.path
        skip_paths = ["/health", "/metrics", "/api/versions", "/docs", "/openapi.json"]
        if any(path.startswith(p) for p in skip_paths):
            return await call_next(request)

        # 嘗試從 request state 取得 tenant region
        tenant_region = getattr(request.state, "tenant_region", None)

        if tenant_region and tenant_region != LOCAL_REGION:
            # Tenant 不屬於本區域，回傳路由指引
            target_config = get_region_config(tenant_region)
            logger.info(
                "Region mismatch: tenant=%s, local=%s, redirect to %s",
                tenant_region,
                LOCAL_REGION,
                target_config.api_endpoint,
            )
            return JSONResponse(
                status_code=421,  # Misdirected Request
                content={
                    "detail": "Tenant belongs to a different region",
                    "tenant_region": tenant_region,
                    "local_region": LOCAL_REGION,
                    "redirect_to": target_config.api_endpoint,
                    "message": f"Please use {target_config.api_endpoint} for this tenant",
                },
            )

        return await call_next(request)
