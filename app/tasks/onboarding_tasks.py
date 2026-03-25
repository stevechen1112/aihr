"""
Onboarding email drip sequence (Celery tasks)

Schedule:
  - Day 0: Welcome email (sent immediately at registration)
  - Day 1: Quick start guide (send_onboarding_step1)
  - Day 3: Document upload reminder / congratulations (send_onboarding_step2)
"""

import logging
from uuid import UUID
from app.celery_app import celery_app
from app.db.session import create_session
from app.services.email_service import (
    send_onboarding_step1_email,
    send_onboarding_step2_email,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="onboarding.send_step1", bind=True, max_retries=2)
def send_onboarding_step1_task(self, user_id: str, tenant_id: str):
    """Day 1: Quick-start guide email."""
    db = create_session(tenant_id=tenant_id)
    try:
        from app.models.user import User
        from app.models.tenant import Tenant

        user = db.query(User).filter(User.id == UUID(user_id)).first()
        tenant = db.query(Tenant).filter(Tenant.id == UUID(tenant_id)).first()
        if not user or not tenant:
            logger.warning("Onboarding step1: user/tenant not found (%s/%s)", user_id, tenant_id)
            return

        if user.status != "active":
            return

        ok = send_onboarding_step1_email(user.email, user.full_name or user.email, tenant.name)
        if not ok:
            logger.warning("Onboarding step1 email delivery returned failure for %s", user.email)
        else:
            logger.info("Onboarding step1 sent to %s", user.email)
    except Exception as exc:
        logger.error("Onboarding step1 failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(name="onboarding.send_step2", bind=True, max_retries=2)
def send_onboarding_step2_task(self, user_id: str, tenant_id: str):
    """Day 3: Document upload check + reminder or congratulations."""
    db = create_session(tenant_id=tenant_id)
    try:
        from app.models.user import User
        from app.models.tenant import Tenant
        from app.models.document import Document
        from sqlalchemy import func

        user = db.query(User).filter(User.id == UUID(user_id)).first()
        tenant = db.query(Tenant).filter(Tenant.id == UUID(tenant_id)).first()
        if not user or not tenant:
            return

        if user.status != "active":
            return

        doc_count = db.query(func.count(Document.id)).filter(Document.tenant_id == UUID(tenant_id)).scalar() or 0

        ok = send_onboarding_step2_email(user.email, user.full_name or user.email, doc_count)
        if not ok:
            logger.warning("Onboarding step2 email delivery returned failure for %s", user.email)
        else:
            logger.info("Onboarding step2 sent to %s (docs=%d)", user.email, doc_count)
    except Exception as exc:
        logger.error("Onboarding step2 failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


def schedule_onboarding_sequence(user_id: str, tenant_id: str):
    """
    Called after user registration to schedule the onboarding drip emails.
    Day 0 welcome email is sent synchronously at registration time.
    """
    # Day 1 (24 hours)
    send_onboarding_step1_task.apply_async(
        args=[user_id, tenant_id],
        countdown=86400,  # 24 hours
    )
    # Day 3 (72 hours)
    send_onboarding_step2_task.apply_async(
        args=[user_id, tenant_id],
        countdown=259200,  # 72 hours
    )
