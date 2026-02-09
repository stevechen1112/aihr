from typing import Optional, List
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


# ──────────── T7-5: Feedback ────────────

class FeedbackCreate(BaseModel):
    message_id: UUID
    rating: int  # 1=👎, 2=👍
    category: Optional[str] = None  # wrong_answer / incomplete / outdated / hallucination / other
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: UUID
    message_id: UUID
    rating: int
    category: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCategoryCount(BaseModel):
    category: Optional[str] = None
    count: int


class FeedbackStats(BaseModel):
    total: int
    positive: int
    negative: int
    positive_rate: float
    categories: List[FeedbackCategoryCount]


# ──────────── T7-13: 搜尋結果 ────────────

class SearchResult(BaseModel):
    conversation_id: UUID
    conversation_title: Optional[str] = None
    message_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
