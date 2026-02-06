from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_chat
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationCreate,
    Message
)
from app.services.chat_orchestrator import ChatOrchestrator
from app.api.v1.endpoints.audit import log_usage
from app.services.quota_enforcement import enforce_query_quota

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    *,
    db: Session = Depends(deps.get_db),
    request: ChatRequest,
    current_user: User = Depends(deps.get_current_active_user),
    _quota: None = Depends(enforce_query_quota),
) -> Any:
    """
    發送聊天訊息
    - 並行查詢公司內規和勞資法
    - 合併結果並返回
    - 儲存對話歷史
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="問題不能為空"
        )
    
    # 1. 獲取或建立對話
    conversation_id = request.conversation_id
    if conversation_id:
        conversation = crud_chat.get_conversation(db, conversation_id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="對話不存在"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權訪問此對話"
            )
    else:
        # 建立新對話
        conversation = crud_chat.create_conversation(
            db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            title=request.question[:50]  # 使用問題前 50 字作為標題
        )
    
    # 2. 儲存用戶訊息
    user_message = crud_chat.create_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=request.question
    )
    
    # 3. 使用協調器處理查詢
    orchestrator = ChatOrchestrator()
    result = await orchestrator.process_query(
        tenant_id=current_user.tenant_id,
        question=request.question,
        top_k=request.top_k
    )
    
    # 4. 儲存助手回應
    assistant_message = crud_chat.create_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=result["answer"]
    )
    
    # 5. 記錄用量
    input_tokens = len(request.question) // 4  # 粗略估算
    output_tokens = len(result["answer"]) // 4
    pinecone_queries = 1 if result.get("company_policy") else 0
    
    # 從 labor_law 獲取實際 token 數（如果有）
    if result.get("labor_law") and result["labor_law"].get("usage"):
        usage = result["labor_law"]["usage"]
        input_tokens = usage.get("input_tokens", input_tokens)
        output_tokens = usage.get("output_tokens", output_tokens)
    
    log_usage(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action_type="chat",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        pinecone_queries=pinecone_queries,
        embedding_calls=0,
        metadata={"conversation_id": str(conversation.id)}
    )
    
    # 6. 返回結果
    return ChatResponse(
        request_id=result["request_id"],
        question=result["question"],
        answer=result["answer"],
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        company_policy=result.get("company_policy"),
        labor_law=result.get("labor_law"),
        sources=result["sources"],
        notes=result["notes"],
        disclaimer=result["disclaimer"]
    )


@router.get("/conversations", response_model=List[Conversation])
def list_conversations(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """獲取當前用戶的對話列表"""
    conversations = crud_chat.get_user_conversations(
        db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit
    )
    return conversations


@router.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(
    *,
    db: Session = Depends(deps.get_db),
    conversation_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """獲取特定對話"""
    conversation = crud_chat.get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權訪問此對話"
        )
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
def get_conversation_messages(
    *,
    db: Session = Depends(deps.get_db),
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """獲取對話的訊息歷史"""
    conversation = crud_chat.get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權訪問此對話"
        )
    
    messages = crud_chat.get_conversation_messages(
        db, conversation_id=conversation_id, skip=skip, limit=limit
    )
    return messages


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    *,
    db: Session = Depends(deps.get_db),
    conversation_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """刪除對話"""
    conversation = crud_chat.get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權刪除此對話"
        )
    
    crud_chat.delete_conversation(db, conversation_id=conversation_id)
    return {"message": "對話已刪除", "conversation_id": str(conversation_id)}
