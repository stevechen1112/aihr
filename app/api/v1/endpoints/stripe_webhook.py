"""
Stripe Webhook Handler

Processes Stripe events to:
  - Activate subscriptions on checkout.session.completed
  - Record billing entries on invoice.paid
  - Handle subscription cancellations
"""

import hashlib
import hmac
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.config import settings
from app.models.billing import BillingRecord
from app.models.tenant import Tenant
from app.services.subscription import get_plan, PLAN_MATRIX

router = APIRouter()
logger = logging.getLogger("unihr.stripe")

# ── Stripe signature verification ──


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> dict:
    """Verify Stripe webhook signature and parse event.

    Stripe-Signature header format:
        t=<timestamp>,v1=<signature>[,v0=<legacy>]
    """
    import json

    if not sig_header or not secret:
        raise ValueError("Missing signature or webhook secret")

    elements = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
    timestamp = elements.get("t")
    signature = elements.get("v1")

    if not timestamp or not signature:
        raise ValueError("Invalid Stripe-Signature header")

    # Reject timestamps older than 5 minutes
    if abs(time.time() - int(timestamp)) > 300:
        raise ValueError("Webhook timestamp too old")

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise ValueError("Signature verification failed")

    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON payload: {e}")


# ── Webhook endpoint ──


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(deps.get_db)):
    """Handle Stripe webhook events."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = _verify_stripe_signature(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        logger.warning("Stripe webhook signature failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    logger.info("Stripe event received: %s (id=%s)", event_type, event.get("id"))

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, data_obj)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(db, data_obj)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_cancelled(db, data_obj)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"received": True}


def _resolve_tenant(db: Session, metadata: dict) -> Optional[Tenant]:
    """Find tenant from Stripe metadata.tenant_id."""
    tenant_id = metadata.get("tenant_id")
    if not tenant_id:
        return None
    try:
        import uuid as _uuid

        _uuid.UUID(str(tenant_id))
    except ValueError:
        logger.warning("_resolve_tenant: invalid UUID format: %s", tenant_id)
        return None
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def _handle_checkout_completed(db: Session, session: dict):
    """Activate plan after successful Stripe Checkout."""
    metadata = session.get("metadata", {})
    target_plan = metadata.get("plan")
    tenant = _resolve_tenant(db, metadata)

    if not tenant or not target_plan or target_plan not in PLAN_MATRIX:
        logger.warning("checkout.session.completed: missing tenant or plan in metadata")
        return

    old_plan = tenant.plan
    plan_config = get_plan(target_plan)

    tenant.plan = target_plan
    tenant.max_users = plan_config["max_users"]
    tenant.max_documents = plan_config["max_documents"]
    tenant.max_storage_mb = plan_config["max_storage_mb"]
    tenant.monthly_query_limit = plan_config["monthly_query_limit"]
    tenant.monthly_token_limit = plan_config["monthly_token_limit"]

    # Avoid duplicate billing records (idempotency)
    external_id = session.get("payment_intent") or session.get("id")
    existing = db.query(BillingRecord).filter(BillingRecord.external_id == external_id).first()
    if existing:
        logger.info("checkout.session.completed: duplicate for %s, skipping", external_id)
        db.rollback()
        return

    # Create billing record
    amount_total = session.get("amount_total")
    if not amount_total:
        logger.error(
            "checkout.session.completed: missing/zero amount_total for session %s",
            session.get("id"),
        )
        return
    amount = amount_total / 100  # Stripe amounts are in cents
    currency = (session.get("currency") or "usd").upper()

    record = BillingRecord(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=external_id,
        amount_usd=amount,
        currency=currency,
        status="paid",
        description=f"Upgrade to {plan_config['display_name']}",
        plan=target_plan,
        invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Checkout commit failed for tenant %s: %s", tenant.id, e)
        raise

    logger.info("Tenant %s upgraded via Stripe: %s → %s", tenant.id, old_plan, target_plan)


def _handle_invoice_paid(db: Session, invoice: dict):
    """Record a paid invoice (for recurring subscriptions)."""
    metadata = invoice.get("subscription_details", {}).get("metadata", {}) or invoice.get("metadata", {})
    tenant = _resolve_tenant(db, metadata)
    if not tenant:
        logger.debug("invoice.paid: no tenant_id in metadata, skipping")
        return

    # Avoid duplicates
    invoice_id = invoice.get("id")
    if not invoice_id:
        logger.warning("invoice.paid: missing invoice id, skipping")
        return
    existing = db.query(BillingRecord).filter(BillingRecord.external_id == invoice_id).first()
    if existing:
        return

    amount = (invoice.get("amount_paid", 0)) / 100
    currency = (invoice.get("currency") or "usd").upper()

    lines_data = invoice.get("lines", {}).get("data", [])
    period = lines_data[0].get("period", {}) if lines_data else {}
    period_start = datetime.fromtimestamp(period["start"], tz=timezone.utc) if period.get("start") else None
    period_end = datetime.fromtimestamp(period["end"], tz=timezone.utc) if period.get("end") else None

    record = BillingRecord(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=invoice_id,
        amount_usd=amount,
        currency=currency,
        status="paid",
        description=invoice.get("description") or "Subscription renewal",
        plan=tenant.plan,
        period_start=period_start,
        period_end=period_end,
        invoice_number=invoice.get("number"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Invoice commit failed for tenant %s: %s", tenant.id, e)
        raise

    logger.info("Invoice recorded for tenant %s: %s %.2f", tenant.id, currency, amount)


def _handle_subscription_cancelled(db: Session, subscription: dict):
    """Downgrade tenant to free plan when subscription is cancelled."""
    metadata = subscription.get("metadata", {})
    tenant = _resolve_tenant(db, metadata)
    if not tenant:
        return

    old_plan = tenant.plan
    free_config = get_plan("free")

    tenant.plan = "free"
    tenant.max_users = free_config["max_users"]
    tenant.max_documents = free_config["max_documents"]
    tenant.max_storage_mb = free_config["max_storage_mb"]
    tenant.monthly_query_limit = free_config["monthly_query_limit"]
    tenant.monthly_token_limit = free_config["monthly_token_limit"]
    db.commit()

    logger.info("Tenant %s subscription cancelled: %s → free", tenant.id, old_plan)
