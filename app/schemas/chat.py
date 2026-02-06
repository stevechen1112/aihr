from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    title: str = "新對話"


class Conversation(ConversationBase):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    role: str  # user, assistant
    content: str


class MessageCreate(MessageBase):
    conversation_id: UUID


class Message(MessageBase):
    id: UUID
    conversation_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[UUID] = None
    top_k: int = 3


class ChatResponse(BaseModel):
    request_id: str
    question: str
    answer: str
    conversation_id: UUID
    message_id: UUID
    company_policy: Optional[dict] = None
    labor_law: Optional[dict] = None
    sources: list
    notes: list
    disclaimer: str
