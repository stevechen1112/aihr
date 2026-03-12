import os
import io
import tempfile
import hashlib
import time
import logging
from typing import List
from uuid import UUID
import boto3
from pinecone import Pinecone
import voyageai
from celery.exceptions import SoftTimeLimitExceeded
from app.celery_app import celery_app
from app.config import settings
from app.db.session import SessionLocal
from app.crud import crud_document
from app.services.document_parser import DocumentParser, TextChunker
from app.schemas.document import DocumentUpdate
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _pinecone_index():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return pc.Index(settings.PINECONE_INDEX_NAME)


@celery_app.task(
    bind=True,
    max_retries=getattr(settings, "CELERY_DOCUMENT_TASK_MAX_RETRIES", 3),
    soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", 300),
    time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT_SECONDS", 360),
    retry_backoff=getattr(settings, "CELERY_TASK_RETRY_BACKOFF", True),
    retry_backoff_max=getattr(settings, "CELERY_TASK_RETRY_BACKOFF_MAX_SECONDS", 300),
    retry_jitter=getattr(settings, "CELERY_TASK_RETRY_JITTER", True),
)
def process_document_task(self, document_id: str, file_path: str, tenant_id: str):
    """
    背景任務：處理文件
    1. 解析文件（LlamaParse 優先 → 內建解析器 fallback）
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
        
        # 3. 從 R2 下載文件到暫存檔並解析
        file_ext = os.path.splitext(doc.filename)[1].lower() or ".bin"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=file_ext)
        os.close(tmp_fd)
        try:
            _r2_client().download_file(settings.R2_BUCKET, file_path, tmp_path)
            text_content, metadata = DocumentParser.parse(tmp_path, doc.file_type)
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
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        # 3.5 儲存品質報告
        crud_document.update(
            db,
            db_obj=doc,
            obj_in=DocumentUpdate(quality_report=metadata)
        )
        
        # 4. 切片（結構化表格優先全量入庫）
        full_table_ok = doc.file_type in {"csv", "xlsx", "xls"}
        if full_table_ok and len(text_content) <= settings.TABLE_FULL_CHUNK_MAX_CHARS:
            chunks = [text_content.strip()]
        else:
            chunks = TextChunker.split_by_tokens(
                text_content,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )
        
        # 4.5 小檔案 fallback：若文字有效但太短無法分割，整段作為一個 chunk
        if not chunks and text_content.strip():
            chunks = [text_content.strip()]
        
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
        
        # 7. 寫入 Pinecone（向量）+ PostgreSQL（文字 for BM25）
        pinecone_index = _pinecone_index()
        namespace = tenant_id  # tenant namespace 提供多租戶雔離

        vectors_to_upsert = []
        chunk_rows = []

        # 取得已存在的 chunk hashes（去重用）
        from app.models.document import DocumentChunk as DChunk
        existing_hashes = {
            row[0]
            for row in db.query(DChunk.chunk_hash)
            .filter(DChunk.document_id == UUID(document_id))
            .all()
        }

        inserted = 0
        skipped = 0
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]

            if chunk_hash in existing_hashes:
                skipped += 1
                continue

            vector_id = f"{document_id}-chunk-{idx}"

            # Pinecone vector
            vectors_to_upsert.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "filename": doc.filename,
                    "chunk_index": idx,
                    "text": chunk,
                    "parse_engine": metadata.get("parse_engine", "native"),
                },
            })

            # PostgreSQL chunk（保留文字供 BM25用）
            chunk_rows.append(DChunk(
                document_id=UUID(document_id),
                tenant_id=UUID(tenant_id),
                chunk_index=idx,
                text=chunk,
                chunk_hash=chunk_hash,
                vector_id=vector_id,
                # embedding=None — 向量儲存於 Pinecone
                metadata_json={
                    "filename": doc.filename,
                    "chunk_index": idx,
                    "parse_engine": metadata.get("parse_engine", "native"),
                    "quality_score": metadata.get("quality_score", 0),
                    "tables_detected": metadata.get("tables_detected", 0),
                    "ocr_used": metadata.get("ocr_used", False),
                },
            ))
            inserted += 1

        # Pinecone upsert（批次 100 vectors）
        upsert_batch = 100
        for i in range(0, len(vectors_to_upsert), upsert_batch):
            pinecone_index.upsert(
                vectors=vectors_to_upsert[i:i + upsert_batch],
                namespace=namespace,
            )

        # PostgreSQL commit
        for row in chunk_rows:
            db.add(row)
        db.commit()

        if skipped:
            logger.info(f"去重: 跳過 {skipped} 個重複 chunk，寫入 {inserted} 個")
        
        # 8. 更新狀態：完成
        crud_document.update(
            db,
            db_obj=doc,
            obj_in=DocumentUpdate(
                status="completed",
                chunk_count=inserted,
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
            "chunks": inserted,
        }
        
    except SoftTimeLimitExceeded as e:
        if db:
            doc = crud_document.get(db, document_id=UUID(document_id))
            if doc:
                crud_document.update(
                    db,
                    db_obj=doc,
                    obj_in=DocumentUpdate(
                        status="failed",
                        error_message="任務逾時，已中止處理",
                    )
                )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {"status": "failed", "error": "task soft time limit exceeded"}

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
            raise self.retry(exc=e)
        
        return {"status": "failed", "error": str(e)}
    
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=getattr(settings, "CELERY_URL_TASK_MAX_RETRIES", 2),
    soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", 300),
    time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT_SECONDS", 360),
    retry_backoff=getattr(settings, "CELERY_TASK_RETRY_BACKOFF", True),
    retry_backoff_max=getattr(settings, "CELERY_TASK_RETRY_BACKOFF_MAX_SECONDS", 300),
    retry_jitter=getattr(settings, "CELERY_TASK_RETRY_JITTER", True),
)
def process_url_task(self, document_id: str, url: str, tenant_id: str):
    """
    背景任務：擷取網頁 URL 內容並向量化。

    流程：
    1. 使用 trafilatura 擷取網頁正文
    2. 切片
    3. 向量化
    4. 寫入 pgvector
    """
    db = SessionLocal()

    try:
        doc = crud_document.get(db, document_id=UUID(document_id))
        if not doc:
            raise ValueError("文件記錄不存在")

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(status="parsing"),
        )

        # 1. 擷取網頁
        try:
            text_content, metadata = DocumentParser.parse_url(url)
        except Exception as e:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message=f"網頁擷取失敗: {e}"),
            )
            return {"status": "failed", "error": str(e)}

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(quality_report=metadata),
        )

        # 2. 切片
        chunks = TextChunker.split_by_tokens(
            text_content,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        if not chunks:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message="網頁內容切片後無有效內容"),
            )
            return {"status": "failed", "error": "No valid chunks from URL"}

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(status="embedding", chunk_count=len(chunks)),
        )

        # 3. 向量化
        if not settings.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY 未設定")

        voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            result = voyage_client.embed(batch, model=settings.VOYAGE_MODEL, input_type="document")
            all_embeddings.extend(result.embeddings)
            time.sleep(0.5)

        # 4. 寫入 pgvector（含去重）
        from app.models.document import DocumentChunk as DChunk

        inserted = 0
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]

            # 去重：同一文件內相同內容的 chunk 不重複寫入
            existing = (
                db.query(DChunk)
                .filter(
                    DChunk.document_id == UUID(document_id),
                    DChunk.chunk_hash == chunk_hash,
                )
                .first()
            )
            if existing:
                continue

            db_chunk = DChunk(
                document_id=UUID(document_id),
                tenant_id=UUID(tenant_id),
                chunk_index=idx,
                text=chunk,
                chunk_hash=chunk_hash,
                vector_id=f"{document_id}-url-chunk-{idx}",
                embedding=embedding,
                metadata_json={
                    "filename": doc.filename,
                    "source_url": url,
                    "chunk_index": idx,
                    "parse_engine": "trafilatura",
                },
            )
            db.add(db_chunk)
            inserted += 1

        db.commit()

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(
                status="completed",
                chunk_count=inserted,
                quality_report=metadata,
            ),
        )

        # 清除快取
        try:
            from app.services.kb_retrieval import KnowledgeBaseRetriever
            retriever = KnowledgeBaseRetriever()
            retriever.invalidate_cache(UUID(tenant_id))
        except Exception:
            pass

        return {
            "status": "completed",
            "document_id": document_id,
            "url": url,
            "chunks": inserted,
        }

    except SoftTimeLimitExceeded as e:
        if db:
            doc = crud_document.get(db, document_id=UUID(document_id))
            if doc:
                crud_document.update(
                    db,
                    db_obj=doc,
                    obj_in=DocumentUpdate(
                        status="failed",
                        error_message="任務逾時，已中止處理",
                    ),
                )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": "task soft time limit exceeded"}

    except Exception as e:
        if db:
            doc = crud_document.get(db, document_id=UUID(document_id))
            if doc:
                crud_document.update(
                    db, db_obj=doc,
                    obj_in=DocumentUpdate(status="failed", error_message=str(e)),
                )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()
