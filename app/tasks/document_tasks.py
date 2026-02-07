import os
import time
from typing import List
from uuid import UUID
import voyageai
from app.celery_app import celery_app
from app.config import settings
from app.db.session import SessionLocal
from app.crud import crud_document
from app.services.document_parser import DocumentParser, TextChunker
from app.schemas.document import DocumentUpdate


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, document_id: str, file_path: str, tenant_id: str):
    """
    背景任務：處理文件
    1. 解析文件
    2. 切片
    3. 向量化（Voyage voyage-4-lite）
    4. 寫入 pgvector（PostgreSQL）
    """
    db = SessionLocal()
    
    try:
        # 1. 獲取文件記錄
        doc = crud_document.get(db, document_id=UUID(document_id))
        if not doc:
            raise ValueError("文件不存在")
        
        # 2. 更新狀態：解析中
        crud_document.update(
            db,
            db_obj=doc,
            obj_in=DocumentUpdate(status="parsing")
        )
        
        # 3. 解析文件
        try:
            text_content, metadata = DocumentParser.parse(file_path, doc.file_type)
        except Exception as e:
            crud_document.update(
                db,
                db_obj=doc,
                obj_in=DocumentUpdate(
                    status="failed",
                    error_message=f"解析失敗: {str(e)}"
                )
            )
            return {"status": "failed", "error": str(e)}
        
        # 3.5 儲存品質報告
        crud_document.update(
            db,
            db_obj=doc,
            obj_in=DocumentUpdate(quality_report=metadata)
        )
        
        # 4. 切片
        chunks = TextChunker.split_by_tokens(
            text_content,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        if not chunks:
            crud_document.update(
                db,
                db_obj=doc,
                obj_in=DocumentUpdate(
                    status="failed",
                    error_message="文件切片後無有效內容"
                )
            )
            return {"status": "failed", "error": "No valid chunks"}
        
        # 5. 更新狀態：向量化中
        crud_document.update(
            db,
            db_obj=doc,
            obj_in=DocumentUpdate(
                status="embedding",
                chunk_count=len(chunks)
            )
        )
        
        # 6. 向量化（Voyage voyage-4-lite）
        if not settings.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY 未設定")
        
        voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        
        # 批次處理（Voyage API 支援批次）
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            result = voyage_client.embed(
                batch,
                model=settings.VOYAGE_MODEL,
                input_type="document"
            )
            all_embeddings.extend(result.embeddings)
            time.sleep(0.5)  # Rate limiting
        
        # 7. 寫入 pgvector（直接儲存到 PostgreSQL）
        from app.models.document import DocumentChunk
        
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            vector_id = f"{document_id}-chunk-{idx}"
            
            # 建立 chunk 記錄，同時包含文字和向量
            db_chunk = DocumentChunk(
                document_id=UUID(document_id),
                tenant_id=UUID(tenant_id),
                chunk_index=idx,
                text=chunk,
                vector_id=vector_id,
                embedding=embedding,  # pgvector: 直接存入向量
                metadata_json={
                    "filename": doc.filename,
                    "chunk_index": idx,
                }
            )
            db.add(db_chunk)
        
        db.commit()
        
        # 8. 更新狀態：完成
        crud_document.update(
            db,
            db_obj=doc,
            obj_in=DocumentUpdate(
                status="completed",
                chunk_count=len(chunks),
                quality_report=metadata
            )
        )
        
        # 8.5 清除租戶檢索快取（新文件上傳後失效舊快取）
        try:
            from app.services.kb_retrieval import KnowledgeBaseRetriever
            retriever = KnowledgeBaseRetriever()
            retriever.invalidate_cache(UUID(tenant_id))
        except Exception:
            pass  # 快取清除失敗不影響主流程
        
        # 9. 清理臨時文件（可選）
        # os.remove(file_path)
        
        return {
            "status": "completed",
            "document_id": document_id,
            "chunks": len(chunks),
        }
        
    except Exception as e:
        # 記錄錯誤
        if db:
            doc = crud_document.get(db, document_id=UUID(document_id))
            if doc:
                crud_document.update(
                    db,
                    db_obj=doc,
                    obj_in=DocumentUpdate(
                        status="failed",
                        error_message=str(e)
                    )
                )
        
        # 重試機制
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        
        return {"status": "failed", "error": str(e)}
    
    finally:
        db.close()
