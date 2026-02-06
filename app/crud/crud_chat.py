from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.chat import Conversation, Message


def get_conversation(db: Session, conversation_id: UUID) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_user_conversations(
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[Conversation]:
    return db.query(Conversation).filter(
        Conversation.user_id == user_id,
        Conversation.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()


def create_conversation(
    db: Session,
    *,
    user_id: UUID,
    tenant_id: UUID,
    title: str = "新對話"
) -> Conversation:
    db_obj = Conversation(
        user_id=user_id,
        tenant_id=tenant_id,
        title=title
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_message(
    db: Session,
    *,
    conversation_id: UUID,
    role: str,
    content: str
) -> Message:
    db_obj = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_conversation_messages(
    db: Session,
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[Message]:
    return db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).offset(skip).limit(limit).all()


def delete_conversation(db: Session, conversation_id: UUID) -> bool:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        # 刪除相關訊息
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        db.delete(conv)
        db.commit()
        return True
    return False
