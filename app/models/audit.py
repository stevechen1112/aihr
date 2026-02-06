import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class AuditLog(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    action = Column(String, nullable=False, index=True) # login, upload_doc, delete_doc, chat
    target_type = Column(String, nullable=True) # document, user, tenant
    target_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    detail_json = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")


class UsageRecord(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    action_type = Column(String, nullable=False, index=True) # chat, embed, index
    
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    pinecone_queries = Column(Integer, default=0)
    embedding_calls = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    
    estimated_cost_usd = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")
    user = relationship("User", back_populates="usage_records")
