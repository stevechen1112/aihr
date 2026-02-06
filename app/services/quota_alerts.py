"""
配額告警通知服務（Quota Alert Service）
在配額接近上限或超額時發送通知
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.db.base_class import Base
from app.crud import crud_tenant

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
#  Alert Record Model
# ═══════════════════════════════════════════

class QuotaAlert(Base):
    """配額告警記錄"""
    import uuid as _uuid
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, index=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    alert_type = Column(String, nullable=False)        # warning, exceeded
    resource = Column(String, nullable=False)           # users, documents, queries, tokens, storage
    current_value = Column(Integer, default=0)
    limit_value = Column(Integer, nullable=True)
    usage_ratio = Column(Float, default=0.0)
    message = Column(String, nullable=True)
    notified = Column(Boolean, default=False)           # 是否已發送通知
    notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════
#  Alert Service
# ═══════════════════════════════════════════

class QuotaAlertService:
    """配額告警服務"""

    RESOURCE_MAP = {
        "users_usage_ratio": ("users", "max_users", "current_users", "使用者"),
        "documents_usage_ratio": ("documents", "max_documents", "current_documents", "文件"),
        "storage_usage_ratio": ("storage", "max_storage_mb", "current_storage_mb", "儲存空間"),
        "queries_usage_ratio": ("queries", "monthly_query_limit", "current_monthly_queries", "月查詢次數"),
        "tokens_usage_ratio": ("tokens", "monthly_token_limit", "current_monthly_tokens", "月 Token 量"),
    }

    @staticmethod
    def check_and_create_alerts(db: Session, tenant_id: UUID) -> List[Dict[str, Any]]:
        """
        檢查租戶配額狀態並建立告警記錄。
        回傳新建的告警列表。
        """
        status = crud_tenant.get_quota_status(db, tenant_id)
        if not status:
            return []

        threshold = status.get("quota_alert_threshold", 0.8)
        alerts: List[Dict[str, Any]] = []

        for ratio_key, (resource, limit_key, current_key, label) in QuotaAlertService.RESOURCE_MAP.items():
            ratio = status.get(ratio_key)
            if ratio is None:
                continue

            current = status.get(current_key, 0)
            limit_val = status.get(limit_key)

            if ratio >= 1.0:
                alert_type = "exceeded"
                message = f"[超額] {label}已超過上限：{current}/{limit_val}"
            elif ratio >= threshold:
                alert_type = "warning"
                message = f"[警告] {label}已達 {int(ratio*100)}%：{current}/{limit_val}"
            else:
                continue

            # 檢查是否已有近期相同告警（避免重複）
            existing = (
                db.query(QuotaAlert)
                .filter(
                    QuotaAlert.tenant_id == tenant_id,
                    QuotaAlert.resource == resource,
                    QuotaAlert.alert_type == alert_type,
                    QuotaAlert.created_at >= func.now() - func.cast("1 hour", String),
                )
                .first()
            )
            if existing:
                continue

            alert = QuotaAlert(
                tenant_id=tenant_id,
                alert_type=alert_type,
                resource=resource,
                current_value=int(current) if isinstance(current, (int, float)) else 0,
                limit_value=limit_val,
                usage_ratio=ratio,
                message=message,
            )
            db.add(alert)
            alerts.append({
                "alert_type": alert_type,
                "resource": resource,
                "message": message,
                "current": current,
                "limit": limit_val,
                "ratio": ratio,
            })

        if alerts:
            db.commit()
            logger.warning(
                "Quota alerts for tenant %s: %d alerts",
                tenant_id, len(alerts)
            )

        return alerts

    @staticmethod
    def get_alerts(
        db: Session,
        tenant_id: UUID,
        *,
        alert_type: Optional[str] = None,
        unnotified_only: bool = False,
        limit: int = 50,
    ) -> List[QuotaAlert]:
        """查詢租戶告警記錄"""
        q = db.query(QuotaAlert).filter(QuotaAlert.tenant_id == tenant_id)
        if alert_type:
            q = q.filter(QuotaAlert.alert_type == alert_type)
        if unnotified_only:
            q = q.filter(QuotaAlert.notified == False)
        return q.order_by(QuotaAlert.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_notified(db: Session, alert_ids: List[UUID]) -> int:
        """標記告警為已通知"""
        count = (
            db.query(QuotaAlert)
            .filter(QuotaAlert.id.in_(alert_ids))
            .update(
                {"notified": True, "notified_at": datetime.utcnow()},
                synchronize_session="fetch",
            )
        )
        db.commit()
        return count

    @staticmethod
    def send_alert_email(tenant_id: UUID, alerts: List[Dict], recipient: str) -> bool:
        """
        發送告警 Email（預留介面，目前只記錄 log）
        未來可整合 SMTP / SendGrid / SES
        """
        logger.info(
            "Sending quota alert email to %s for tenant %s: %d alerts",
            recipient, tenant_id, len(alerts),
        )
        # TODO: 實作 Email 發送
        # import smtplib
        # ...
        return True
