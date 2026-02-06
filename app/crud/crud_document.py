import os
import hashlib
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentCreate, DocumentUpdate


def get(db: Session, document_id: UUID) -> Document:
    return db.query(Document).filter(Document.id == document_id).first()


def get_by_tenant(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Document]:
    return db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()


def create(db: Session, *, obj_in: DocumentCreate, tenant_id: UUID, uploaded_by: UUID, file_size: int) -> Document:
    db_obj = Document(
        filename=obj_in.filename,
        file_type=obj_in.file_type,
        tenant_id=tenant_id,
        uploaded_by=uploaded_by,
        file_size=file_size,
        status="uploading"
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(db: Session, *, db_obj: Document, obj_in: DocumentUpdate) -> Document:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, *, document_id: UUID) -> bool:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        # Delete associated chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.delete(doc)
        db.commit()
        return True
    return False


def create_chunk(
    db: Session,
    *,
    document_id: UUID,
    tenant_id: UUID,
    chunk_index: int,
    content: str,
    vector_id: str = None
) -> DocumentChunk:
    chunk_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    db_obj = DocumentChunk(
        document_id=document_id,
        tenant_id=tenant_id,
        chunk_index=chunk_index,
        text=content,
        chunk_hash=chunk_hash,
        vector_id=vector_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_chunks(db: Session, document_id: UUID) -> List[DocumentChunk]:
    return db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).all()
