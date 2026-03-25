"""Billing record model for tracking payments and invoices."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NewebPay TradeNo or manual reference
    external_id = Column(String(255), nullable=True, unique=True)
    amount_usd = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(50), default="pending")  # pending, paid, failed, refunded
    description = Column(Text, nullable=True)
    plan = Column(String(50), nullable=True)  # free, pro, enterprise
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    invoice_number = Column(String(100), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", backref="billing_records")
