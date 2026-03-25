from typing import Any, List
from uuid import UUID
from datetime import datetime, timezone
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps_permissions import check_user_management_permission
from app.crud import crud_user, crud_tenant
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(deps.get_current_active_user_lazy_db),
) -> Any:
    """
    獲取當前用戶資訊
    """
    return current_user


@router.post("/", response_model=UserSchema)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    建立新用戶
    - 權限：owner, admin
    - Superuser 可以為任何租戶建立用戶
    - 一般用戶只能為自己的租戶建立用戶
    """
    # 權限檢查
    check_user_management_permission(current_user)
    
    # 檢查權限
    if not current_user.is_superuser and user_in.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create user for this tenant"
        )
    
    # 配額檢查
    if not current_user.is_superuser:
        quota = crud_tenant.check_quota(db, user_in.tenant_id, "user")
        if not quota.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": quota["message"],
                    "resource": "user",
                    "current": quota.get("current"),
                    "limit": quota.get("limit"),
                },
            )
    
    # 檢查 email 是否已存在
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    user = crud_user.create(db, obj_in=user_in)
    return user


# ═══════════════════════════════════════════
#  個資法第 3 條 — 個人資料匯出
# ═══════════════════════════════════════════

@router.get("/me/export")
def export_my_data(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Response:
    """
    匯出當前使用者所有個人資料（個資法第 3 條第 2 款：請求製給複製本）。
    回傳 JSON 檔案，包含帳號資料、對話紀錄、使用紀錄。
    """
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.usage import UsageRecord

    # 帳號資料
    user_data = {
        "account": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "status": current_user.status,
            "tenant_id": str(current_user.tenant_id),
            "department_id": str(current_user.department_id) if current_user.department_id else None,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "agreed_to_terms": current_user.agreed_to_terms,
            "agreed_at": current_user.agreed_at.isoformat() if current_user.agreed_at else None,
        },
        "conversations": [],
        "usage_records": [],
    }

    # 對話與訊息
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).all()
    for conv in conversations:
        messages = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at).all()
        user_data["conversations"].append({
            "id": str(conv.id),
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        })

    # 使用紀錄
    usage_records = db.query(UsageRecord).filter(
        UsageRecord.user_id == current_user.id
    ).order_by(UsageRecord.created_at.desc()).limit(1000).all()
    for rec in usage_records:
        user_data["usage_records"].append({
            "action_type": rec.action_type,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
        })

    content = json.dumps(user_data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="unihr-data-export-{current_user.id}.json"'
        },
    )


# ═══════════════════════════════════════════
#  個資法第 3 條 — 刪除個人資料
# ═══════════════════════════════════════════

class DeleteAccountRequest(BaseModel):
    password: str
    confirm: bool = False


@router.post("/me/delete")
def delete_my_account(
    body: DeleteAccountRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> dict:
    """
    刪除帳號及所有個人資料（個資法第 3 條第 5 款：請求刪除）。
    需輸入密碼確認。租戶擁有者不得自行刪除（須先移轉擁有權）。
    """
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請確認刪除操作（confirm=true）",
        )

    # 驗證密碼
    from app.core.security import verify_password
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密碼不正確",
        )

    # 租戶唯一擁有者不能自刪
    if current_user.role == "owner":
        owner_count = db.query(User).filter(
            User.tenant_id == current_user.tenant_id,
            User.role == "owner",
            User.status == "active",
        ).count()
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您是租戶的唯一擁有者，請先轉移擁有權後再刪除帳號",
            )

    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.usage import UsageRecord

    # 刪除使用紀錄
    db.query(UsageRecord).filter(UsageRecord.user_id == current_user.id).delete()

    # 刪除對話與訊息
    conv_ids = [c.id for c in db.query(Conversation.id).filter(
        Conversation.user_id == current_user.id
    ).all()]
    if conv_ids:
        db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete(synchronize_session=False)

    # 匿名化稽核日誌（保留紀錄但抹除身份）
    from app.models.audit import AuditLog
    db.query(AuditLog).filter(
        AuditLog.actor_user_id == current_user.id
    ).update({"actor_user_id": None}, synchronize_session=False)

    # 寄送刪除確認信（best-effort）
    email = current_user.email
    name = current_user.full_name or ""

    # 刪除使用者
    db.delete(current_user)
    db.commit()

    try:
        from app.services.email_service import send_account_deleted_email
        send_account_deleted_email(email, name)
    except Exception:
        pass

    logger.info("User account deleted: %s (PDPA Art.3§5)", email)
    return {"msg": "帳號及個人資料已刪除"}
