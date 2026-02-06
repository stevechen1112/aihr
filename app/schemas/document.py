from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class DocumentBase(BaseModel):
    filename: Optional[str] = None
    file_type: Optional[str] = None  # pdf, docx, doc, txt, xlsx, xls, csv, html, markdown, rtf, json, image
    status: Optional[str] = None  # uploading, parsing, embedding, completed, failed
    

class DocumentCreate(DocumentBase):
    filename: str
    file_type: str


class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None
    chunk_count: Optional[int] = None
    quality_report: Optional[dict] = None  # QualityReport.to_dict()


class DocumentInDBBase(DocumentBase):
    id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    uploaded_by: Optional[UUID] = None
    file_size: Optional[int] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    quality_report: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Document(DocumentInDBBase):
    pass


class DocumentChunkBase(BaseModel):
    chunk_index: Optional[int] = None
    content: Optional[str] = None
    chunk_hash: Optional[str] = None


class DocumentChunk(DocumentChunkBase):
    id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    vector_id: Optional[str] = None

    class Config:
        from_attributes = True
