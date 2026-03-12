import os
import asyncio
import uuid
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
import boto3

from app.api import deps
from app.api.deps_permissions import check_document_permission, can_access_document_by_department
from app.crud import crud_document
from app.models.user import User
from app.models.document import Document as DocumentModel
from app.schemas.document import Document, DocumentCreate
from app.config import settings
from app.tasks.document_tasks import process_document_task
from app.services.quota_enforcement import enforce_document_quota

router = APIRouter()


def _get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


@router.get("/", response_model=List[Document])
def list_documents(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[UUID] = Query(None, description="Filter by department"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    獲取當前租戶的文件列表，可依部門篩選
    """
    if department_id:
        if not can_access_document_by_department(current_user, department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限存取此部門的文件",
            )
        documents = (
            db.query(DocumentModel)
            .filter(
                DocumentModel.tenant_id == current_user.tenant_id,
                DocumentModel.department_id == department_id,
            )
            .order_by(DocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        if current_user.is_superuser or current_user.role in ["owner", "admin", "hr"]:
            documents = crud_document.get_by_tenant(
                db, tenant_id=current_user.tenant_id, skip=skip, limit=limit
            )
        else:
            q = db.query(DocumentModel).filter(DocumentModel.tenant_id == current_user.tenant_id)
            if current_user.department_id is None:
                q = q.filter(DocumentModel.department_id.is_(None))
            else:
                q = q.filter(
                    or_(
                        DocumentModel.department_id.is_(None),
                        DocumentModel.department_id == current_user.department_id,
                    )
                )
            documents = (
                q.order_by(DocumentModel.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
    return documents


@router.post("/upload", response_model=Document)
async def upload_document(
    *,
    db: Session = Depends(deps.get_db),
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
    _quota: None = Depends(enforce_document_quota),
) -> Any:
    """
    上傳文件
    - 支援 PDF(文字/掃描/表格)、DOCX、DOC、TXT、Excel、CSV、HTML、Markdown、RTF、JSON、圖片
    - 非同步處理：解析、切片、向量化
    - 權限：owner, admin, hr
    """
    # 權限檢查
    check_document_permission(current_user, "create")
    
    # 1. 驗證文件類型（支援所有 Phase 0-2 格式）
    from app.services.document_parser import DocumentParser, SUPPORTED_FORMATS
    allowed_extensions = set(SUPPORTED_FORMATS.keys())
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支援的文件類型: {file_ext}。支援的類型: {', '.join(sorted(allowed_extensions))}"
        )
    
    # 2. 偵測文件類型
    try:
        file_type = DocumentParser.detect_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # 3. 檢查文件大小
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件過大（{file_size / 1024 / 1024:.2f} MB），上限為 {settings.MAX_FILE_SIZE / 1024 / 1024} MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件為空"
        )
    
    # 4. 建立文件記錄
    doc_in = DocumentCreate(
        filename=file.filename,
        file_type=file_type
    )
    
    document = crud_document.create(
        db,
        obj_in=doc_in,
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        file_size=file_size
    )
    
    # 5. 上传文件到 Cloudflare R2
    r2_key = f"{current_user.tenant_id}/{document.id}{file_ext}"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: _get_r2_client().put_object(
            Bucket=settings.R2_BUCKET,
            Key=r2_key,
            Body=file_content,
        ),
    )

    # 6. 觸發背景任務處理
    process_document_task.delay(
        document_id=str(document.id),
        file_path=r2_key,
        tenant_id=str(current_user.tenant_id)
    )
    
    return document


@router.get("/{document_id}", response_model=Document)
def get_document(
    *,
    db: Session = Depends(deps.get_db),
    document_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    獲取文件詳情
    """
    document = (
        crud_document.get(db, document_id=document_id)
        if current_user.is_superuser
        else crud_document.get_for_tenant(
            db,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
        )
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    return document


@router.delete("/{document_id}")
def delete_document(
    *,
    db: Session = Depends(deps.get_db),
    document_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    刪除文件
    - 刪除 Pinecone 向量
    - 刪除 PostgreSQL chunks（BM25 文字）
    - 刪除 R2 原始檔案
    - 刪除資料庫記錄
    - 權限：owner, admin, hr
    """
    # 權限檢查
    check_document_permission(current_user, "delete")
    
    document = (
        crud_document.get(db, document_id=document_id)
        if current_user.is_superuser
        else crud_document.get_for_tenant(
            db,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
        )
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 取得 chunks（供 Pinecone 刪除和 DB 清除用）
    chunks = (
        crud_document.get_chunks(db, document_id=document_id)
        if current_user.is_superuser
        else crud_document.get_chunks_for_tenant(
            db,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
        )
    )

    # 刪除向量（Pinecone）
    try:
        vector_ids = [c.vector_id for c in chunks if c.vector_id]
        if vector_ids:
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            idx = pc.Index(settings.PINECONE_INDEX_NAME)
            idx.delete(ids=vector_ids, namespace=str(document.tenant_id))
    except Exception as e:
        print(f"刪除 Pinecone 向量失敗: {e}")

    # 刪除 PostgreSQL chunks
    try:
        for chunk in chunks:
            db.delete(chunk)
        db.commit()
    except Exception as e:
        print(f"刪除向量 chunks 失敗: {e}")

    # 刪除 R2 文件
    try:
        file_ext = os.path.splitext(document.filename)[1]
        r2_key = f"{document.tenant_id}/{document.id}{file_ext}"
        _get_r2_client().delete_object(Bucket=settings.R2_BUCKET, Key=r2_key)
    except Exception as e:
        print(f"刪除 R2 文件失敗: {e}")
    
    # 刪除資料庫記錄
    if current_user.is_superuser:
        crud_document.delete(db, document_id=document_id)
    else:
        crud_document.delete_for_tenant(
            db,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
        )
    
    return {"message": "文件已刪除", "document_id": str(document_id)}
