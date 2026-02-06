"""
配額強制執行服務（Quota Enforcement）
提供 FastAPI dependency 用於在端點中檢查配額
"""
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.crud import crud_tenant


class QuotaEnforcer:
    """
    配額檢查 Dependency — 在端點中注入以自動檢查資源配額。

    使用方式:
        @router.post("/upload")
        def upload(
            current_user = Depends(get_current_active_user),
            db = Depends(get_db),
            _ = Depends(QuotaEnforcer("document")),
        ):
            ...
    """

    def __init__(self, resource: str):
        """resource: 'user', 'document', 'query', 'token'"""
        self.resource = resource

    def __call__(
        self,
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_active_user),
    ):
        if current_user.is_superuser:
            return  # 超級管理員不受配額限制

        result = crud_tenant.check_quota(db, current_user.tenant_id, self.resource)

        if not result.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": result["message"],
                    "resource": self.resource,
                    "current": result.get("current"),
                    "limit": result.get("limit"),
                },
            )


# 預定義的配額檢查器
enforce_user_quota = QuotaEnforcer("user")
enforce_document_quota = QuotaEnforcer("document")
enforce_query_quota = QuotaEnforcer("query")
enforce_token_quota = QuotaEnforcer("token")
