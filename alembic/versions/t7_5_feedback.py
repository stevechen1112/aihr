"""add chat_feedbacks table for T7-5

Revision ID: t7_5_feedback
Revises: t4_19_multi_region
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "t7_5_feedback"
down_revision = "t4_19_multi_region"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_feedbacks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "message_id", name="uq_feedback_user_message"),
    )


def downgrade() -> None:
    op.drop_table("chat_feedbacks")
