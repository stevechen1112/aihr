import os
import io
import re
import tempfile
import hashlib
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from uuid import UUID
import boto3
from pinecone import Pinecone
import voyageai
from celery import chain as celery_chain
from celery.exceptions import SoftTimeLimitExceeded
from app.celery_app import celery_app
from app.config import settings
from app.db.session import create_session
from app.crud import crud_document
from app.services.document_parser import DocumentParser, TextChunker
from app.schemas.document import DocumentUpdate
from app.models.document import DocumentChunk
from app.services.circuit_breaker import voyage_breaker, pinecone_breaker

logger = logging.getLogger(__name__)


def _set_progress(document_id: str, pct: int, detail: str = ""):
    """Â∞áÊ?‰ª∂Ë??ÜÈÄ≤Â∫¶ÂØ´ÂÖ• RedisÔºàTTL 1 Â∞èÊ?ÔºâÔ?‰æõÂ?Á´ØÊü•Ë©?""
    try:
        from app.core.redis_client import get_redis_client
        import json
        r = get_redis_client()
        if r:
            key = f"doc_progress:{document_id}"
            r.setex(key, 3600, json.dumps({"pct": pct, "detail": detail}))
    except Exception:
        pass  # best-effort, ‰∏çÂΩ±?ø‰∏ªÊµÅÁ?

# ?Ä?Ä Metrics placeholders (monitoring integration removed) ?Ä?Ä
_PROM = False


def _extract_section_title(chunk_text: str) -> str:
    """??chunk È¶ñË? Markdown Ê®ôÈ?‰ΩúÁÇ∫Á´†Á??çÁ®±Ôºå‰? Pinecone metadata ‰ΩøÁî®"""
    for line in chunk_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return re.sub(r"^#+\s*", "", stripped)
    return ""


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


# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
# Stage 1 ??Parse: download + parse + chunk
# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä

@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.parse_document_task",
    max_retries=getattr(settings, "CELERY_DOCUMENT_TASK_MAX_RETRIES", 3),
    soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", 300),
    time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT_SECONDS", 360),
    retry_backoff=True,
    retry_jitter=True,
)
def parse_document_task(self, document_id: str, file_path: str, tenant_id: str) -> Dict:
    """
    Stage 1Ôºö‰?Ëº???Ëß?? ???áÂ?
    ?ûÂÇ≥ dict ‰æ?embed_document_task ?•Êî∂??
    """
    db = None
    if _PROM:
        CELERY_QUEUE_ACTIVE.labels(stage="parse").inc()
    try:
        db = create_session(tenant_id=tenant_id)
        doc = crud_document.get_for_tenant(
            db, document_id=UUID(document_id), tenant_id=UUID(tenant_id)
        )
        if not doc:
            raise ValueError("?á‰ª∂‰∏çÂ???)

        crud_document.update(db, db_obj=doc, obj_in=DocumentUpdate(status="parsing"))
        _set_progress(document_id, 5, "‰∏ãË??á‰ª∂‰∏?)

        # Download from R2
        file_ext = os.path.splitext(doc.filename)[1].lower() or ".bin"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=file_ext)
        os.close(tmp_fd)
        parse_start = time.monotonic()
        try:
            _r2_client().download_file(settings.R2_BUCKET, file_path, tmp_path)
            _set_progress(document_id, 15, "Ëß???á‰ª∂?ßÂÆπ")
            text_content, metadata = DocumentParser.parse(tmp_path, doc.file_type)
        except Exception as e:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message=f"Ëß??Â§±Ê?: {e}"),
            )
            if _PROM:
                CELERY_TASKS_TOTAL.labels(stage="parse", outcome="failed").inc()
            return {"status": "failed", "error": str(e)}
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        parse_elapsed = time.monotonic() - parse_start
        if _PROM:
            DOCUMENT_PARSE_DURATION.labels(file_type=doc.file_type or "unknown").observe(parse_elapsed)

        crud_document.update(db, db_obj=doc, obj_in=DocumentUpdate(quality_report=metadata))

        # Chunk
        full_table_ok = doc.file_type in {"csv", "xlsx", "xls"}
        if full_table_ok and len(text_content) <= settings.TABLE_FULL_CHUNK_MAX_CHARS:
            chunks = [text_content.strip()]
        else:
            chunks = TextChunker.split_by_tokens(
                text_content,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )

        # ?µÊ∏¨Ê®°Êùø?çÁ®±ÔºàÁî®?ºËøΩËπ§Ë? metadataÔº?
        from app.services.chunk_templates import detect_template
        tmpl = detect_template(text_content)
        template_name = tmpl.name if tmpl else "generic"

        # ?Ä?Ä Langfuse: Ë®òÈ?Ê®°Êùø?µÊ∏¨ÁµêÊ? ?Ä?Ä
        from app.services.langfuse_client import get_langfuse
        lf = get_langfuse()
        if lf:
            lf.generation(
                name="chunk_template_detect",
                input={"filename": doc.filename, "file_type": doc.file_type},
                output={"template_name": template_name, "chunk_count": len(chunks)},
                metadata={"text_length": len(text_content), "parse_elapsed_s": round(parse_elapsed, 2)},
            )

        if not chunks and text_content.strip():
            chunks = [text_content.strip()]

        if not chunks:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message="?á‰ª∂Ëß??ÂæåÁÑ°?âÊ??ßÂÆπ"),
            )
            if _PROM:
                CELERY_TASKS_TOTAL.labels(stage="parse", outcome="empty").inc()
            return {"status": "failed", "error": "No valid chunks"}

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(status="embedding", chunk_count=len(chunks)),
        )

        if _PROM:
            CELERY_TASKS_TOTAL.labels(stage="parse", outcome="success").inc()

        return {
            "status": "parsed",
            "document_id": document_id,
            "tenant_id": tenant_id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "chunks": chunks,
            "metadata": metadata,
            "template_name": template_name,
        }

    except SoftTimeLimitExceeded as e:
        _mark_failed(db, document_id, "Ëß??Ë∂ÖÊ?ÔºåÂ∑≤‰∏≠Ê≠¢?ïÁ?")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": "parse timeout"}

    except Exception as e:
        _mark_failed(db, document_id, str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e)}

    finally:
        if _PROM:
            CELERY_QUEUE_ACTIVE.labels(stage="parse").dec()
        if db is not None:
            db.close()


# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
# Stage 2 ??Embed: Voyage API with circuit breaker
# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä

@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.embed_document_task",
    max_retries=getattr(settings, "CELERY_DOCUMENT_TASK_MAX_RETRIES", 3),
    soft_time_limit=600,  # embedding ?ØËÉΩËºÉ‰?
    time_limit=660,
    retry_backoff=True,
    retry_jitter=True,
)
def embed_document_task(self, parse_result: Dict) -> Dict:
    """
    Stage 2ÔºöÂ??èÂ??•Ô?‰ΩøÁî® Voyage API + circuit breakerÔº?
    ?•Êî∂ parse_document_task ?ÑËº∏?∫„Ä?
    """
    if parse_result.get("status") == "failed":
        return parse_result  # ?≥È?Â§±Ê?

    document_id = parse_result["document_id"]
    tenant_id = parse_result["tenant_id"]
    chunks = parse_result["chunks"]
    filename = parse_result["filename"]
    metadata = parse_result["metadata"]

    db = None
    if _PROM:
        CELERY_QUEUE_ACTIVE.labels(stage="embed").inc()
    try:
        if not settings.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY ?™Ë®≠ÂÆ?)

        voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        batch_size = 32
        all_embeddings: List[List[float]] = []

        enriched_chunks = [f"?á‰ª∂Ôºö{filename}\n\n{chunk}" for chunk in chunks]
        total_batches = max(1, (len(enriched_chunks) + batch_size - 1) // batch_size)

        embed_start = time.monotonic()
        for i in range(0, len(enriched_chunks), batch_size):
            batch_idx = i // batch_size
            pct = 35 + int(50 * batch_idx / total_batches)
            _set_progress(document_id, pct, f"?ëÈ??ñ‰∏≠ {batch_idx+1}/{total_batches}")
            batch = enriched_chunks[i : i + batch_size]
            last_err = None
            for attempt in range(3):
                try:
                    result = voyage_breaker.call(
                        voyage_client.embed,
                        batch,
                        model=settings.VOYAGE_MODEL,
                        input_type="document",
                    )
                    all_embeddings.extend(result.embeddings)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "Voyage embed batch %d attempt %d/3 failed: %s",
                        i // batch_size, attempt + 1, e,
                    )
                    time.sleep(2 ** attempt)

            if last_err is not None:
                # ?ê‰? chunk ?çË©¶
                logger.warning("Batch %d failed, falling back to per-chunk retry", i // batch_size)
                for j, single in enumerate(batch):
                    chunk_err = None
                    for attempt in range(3):
                        try:
                            result = voyage_breaker.call(
                                voyage_client.embed,
                                [single],
                                model=settings.VOYAGE_MODEL,
                                input_type="document",
                            )
                            all_embeddings.extend(result.embeddings)
                            chunk_err = None
                            break
                        except Exception as e:
                            chunk_err = e
                            time.sleep(2 ** attempt)
                    if chunk_err is not None:
                        logger.error("Chunk %d permanently failed, using zero vector", i + j)
                        dim = len(all_embeddings[0]) if all_embeddings else settings.EMBEDDING_DIMENSION
                        all_embeddings.append([0.0] * dim)
            time.sleep(0.5)

        embed_elapsed = time.monotonic() - embed_start
        if _PROM:
            DOCUMENT_EMBED_DURATION.observe(embed_elapsed)
            CELERY_TASKS_TOTAL.labels(stage="embed", outcome="success").inc()

        # ?Ä?Ä Langfuse: Ë®òÈ??πÊ¨° embedding token ???Ä?Ä
        from app.services.langfuse_client import get_langfuse
        lf = get_langfuse()
        if lf:
            lf.generation(
                name="voyage_embed_document",
                model=settings.VOYAGE_MODEL,
                input={"document_id": document_id, "num_chunks": len(chunks)},
                metadata={"batch_size": batch_size, "duration_s": round(embed_elapsed, 2), "filename": filename},
            )
            lf.flush()

        return {
            "status": "embedded",
            "document_id": document_id,
            "tenant_id": tenant_id,
            "filename": filename,
            "chunks": chunks,
            "embeddings": all_embeddings,
            "metadata": metadata,
            "template_name": parse_result.get("template_name", "generic"),
        }

    except SoftTimeLimitExceeded as e:
        db = create_session(tenant_id=tenant_id)
        _mark_failed(db, document_id, "ÂµåÂÖ•Ë∂ÖÊ?ÔºåÂ∑≤‰∏≠Ê≠¢?ïÁ?")
        db.close()
        if _PROM:
            CELERY_TASKS_TOTAL.labels(stage="embed", outcome="timeout").inc()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": "embed timeout"}

    except Exception as e:
        db = create_session(tenant_id=tenant_id)
        _mark_failed(db, document_id, str(e))
        db.close()
        if _PROM:
            CELERY_TASKS_TOTAL.labels(stage="embed", outcome="failed").inc()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e)}

    finally:
        if _PROM:
            CELERY_QUEUE_ACTIVE.labels(stage="embed").dec()


# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
# Stage 3 ??Store: Pinecone (parallel) + PostgreSQL
# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä

def _upsert_pinecone_batch(
    pinecone_index, vectors: List[dict], namespace: str, batch_idx: int
) -> None:
    """?ÆÂÄ?Pinecone batch upsertÔºàÂ∏∂ circuit breaker + retryÔº?""
    last_err = None
    for attempt in range(3):
        try:
            pinecone_breaker.call(
                pinecone_index.upsert,
                vectors=vectors,
                namespace=namespace,
            )
            return
        except Exception as e:
            last_err = e
            logger.warning(
                "Pinecone upsert batch %d attempt %d/3 failed: %s",
                batch_idx, attempt + 1, e,
            )
            time.sleep(2 ** attempt)
    if last_err is not None:
        raise last_err


@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.store_document_task",
    max_retries=getattr(settings, "CELERY_DOCUMENT_TASK_MAX_RETRIES", 3),
    soft_time_limit=300,
    time_limit=360,
    retry_backoff=True,
    retry_jitter=True,
)
def store_document_task(self, embed_result: Dict) -> Dict:
    """
    Stage 3ÔºöÂØ´??PineconeÔºà‰∏¶Ë°?P2Ôº? PostgreSQL + ?¥Êñ∞?Ä?ã„Ä?
    """
    if embed_result.get("status") == "failed":
        return embed_result

    document_id = embed_result["document_id"]
    tenant_id = embed_result["tenant_id"]
    filename = embed_result["filename"]
    chunks = embed_result["chunks"]
    embeddings = embed_result["embeddings"]
    metadata = embed_result["metadata"]
    template_name = embed_result.get("template_name", "generic")
    namespace = tenant_id

    db = None
    if _PROM:
        CELERY_QUEUE_ACTIVE.labels(stage="store").inc()
    try:
        db = create_session(tenant_id=tenant_id)
        doc = crud_document.get_for_tenant(
            db, document_id=UUID(document_id), tenant_id=UUID(tenant_id)
        )
        if not doc:
            raise ValueError("?á‰ª∂‰∏çÂ???)

        # ?ªÈ?
        from app.models.document import DocumentChunk as DChunk
        existing_hashes = {
            row[0]
            for row in db.query(DChunk.chunk_hash)
            .filter(DChunk.document_id == UUID(document_id))
            .all()
        }

        vectors_to_upsert: List[dict] = []
        chunk_rows: List[DocumentChunk] = []
        inserted = 0
        skipped = 0
        zero_vec_count = 0

        store_start = time.monotonic()
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]
            if chunk_hash in existing_hashes:
                skipped += 1
                continue

            # ?µÊ∏¨?∂Â??èÔ?embedding Â§±Ê???chunkÔº?
            is_zero_vector = all(v == 0.0 for v in embedding)

            vector_id = f"{document_id}-chunk-{idx}"

            # ?∂Â??è‰?ÂØ´ÂÖ• PineconeÔºàÈÅø?çÊ??ìË??èÊ™¢Á¥¢Ô?
            if not is_zero_vector:
                vectors_to_upsert.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "tenant_id": tenant_id,
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": idx,
                        "text": chunk,
                        "section_title": _extract_section_title(chunk),
                        "parse_engine": metadata.get("parse_engine", "native"),
                    },
                })
            else:
                zero_vec_count += 1

            chunk_meta = {
                "filename": filename,
                "chunk_index": idx,
                "parse_engine": metadata.get("parse_engine", "native"),
                "quality_score": metadata.get("quality_score", 0),
                "tables_detected": metadata.get("tables_detected", 0),
                "ocr_used": metadata.get("ocr_used", False),
                "template_name": template_name,
            }
            if is_zero_vector:
                chunk_meta["embedding_failed"] = True

            chunk_rows.append(DChunk(
                document_id=UUID(document_id),
                tenant_id=UUID(tenant_id),
                chunk_index=idx,
                text=chunk,
                chunk_hash=chunk_hash,
                vector_id=vector_id,
                embedding=None if is_zero_vector else embedding,
                metadata_json=chunk_meta,
            ))
            inserted += 1

        if zero_vec_count:
            logger.warning(
                "?á‰ª∂ %s: %d chunk(s) ÂµåÂÖ•Â§±Ê?ÔºàÈõ∂?ëÈ?ÔºâÔ?Â∑≤Ë∑≥??Pinecone ÂØ´ÂÖ•",
                document_id, zero_vec_count,
            )

        _set_progress(document_id, 90, "ÂØ´ÂÖ•?ëÈ?Ë≥áÊ?Â∫?)
        # P2: Parallel Pinecone upsert with ThreadPoolExecutor
        upsert_batch = 100
        pinecone_index = _pinecone_index()
        batches = [
            vectors_to_upsert[i : i + upsert_batch]
            for i in range(0, len(vectors_to_upsert), upsert_batch)
        ]

        max_workers = min(len(batches), 4) if batches else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _upsert_pinecone_batch, pinecone_index, batch, namespace, bi
                ): bi
                for bi, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                future.result()  # ?ãÂá∫‰ªª‰?‰æãÂ?

        # PostgreSQL commit
        for row in chunk_rows:
            db.add(row)
        db.commit()

        store_elapsed = time.monotonic() - store_start
        if _PROM:
            DOCUMENT_STORE_DURATION.observe(store_elapsed)

        if skipped:
            logger.info("?ªÈ?: Ë∑≥È? %d ?çË? chunkÔºåÂØ´??%d", skipped, inserted)

        _set_progress(document_id, 100, "?ïÁ?ÂÆåÊ?")
        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(
                status="completed",
                chunk_count=inserted,
                quality_report=metadata,
            ),
        )

        # Ê∏ÖÈô§ÁßüÊà∂Ê™¢Á¥¢Âø´Â?
        try:
            from app.services.kb_retrieval import KnowledgeBaseRetriever
            retriever = KnowledgeBaseRetriever()
            retriever.invalidate_cache(UUID(tenant_id))
        except Exception:
            pass

        if _PROM:
            CELERY_TASKS_TOTAL.labels(stage="store", outcome="success").inc()

        return {
            "status": "completed",
            "document_id": document_id,
            "chunks": inserted,
        }

    except SoftTimeLimitExceeded as e:
        _mark_failed(db, document_id, "?≤Â?Ë∂ÖÊ?ÔºåÂ∑≤‰∏≠Ê≠¢?ïÁ?")
        if _PROM:
            CELERY_TASKS_TOTAL.labels(stage="store", outcome="timeout").inc()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": "store timeout"}

    except Exception as e:
        _mark_failed(db, document_id, str(e))
        if _PROM:
            CELERY_TASKS_TOTAL.labels(stage="store", outcome="failed").inc()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e)}

    finally:
        if _PROM:
            CELERY_QUEUE_ACTIVE.labels(stage="store").dec()
        if db is not None:
            db.close()


# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
# Orchestrator ??backwards-compatible entry point
# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä

@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.process_document_task",
    max_retries=getattr(settings, "CELERY_DOCUMENT_TASK_MAX_RETRIES", 3),
    soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", 300),
    time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT_SECONDS", 360),
    retry_backoff=getattr(settings, "CELERY_TASK_RETRY_BACKOFF", True),
    retry_backoff_max=getattr(settings, "CELERY_TASK_RETRY_BACKOFF_MAX_SECONDS", 300),
    retry_jitter=getattr(settings, "CELERY_TASK_RETRY_JITTER", True),
)
def process_document_task(self, document_id: str, file_path: str, tenant_id: str):
    """
    ?ëÂ??∏ÂÆπ?ÑÂÖ•????üÂ? parse ??embed ??store ?à„Ä?
    ?¢ÂèØ?¥Êé• .delay() ?ºÂè´Ôºå‰??ØÂú®?πÈ??¥ÊôØ‰ΩøÁî®??
    """
    task_chain = celery_chain(
        parse_document_task.s(document_id, file_path, tenant_id),
        embed_document_task.s(),
        store_document_task.s(),
    )
    task_chain.apply_async()
    return {"status": "dispatched", "document_id": document_id}


# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
# Helper
# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä

def _mark_failed(db, document_id: str, message: str):
    """ÂÆâÂÖ®?∞Â??á‰ª∂Ê®ôË??∫Â§±??""
    if db is None:
        return
    try:
        doc = crud_document.get(db, document_id=UUID(document_id), _internal=True)
        if doc:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message=message),
            )
    except Exception:
        logger.exception("Failed to update document status after error")


# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
# URL Task (unchanged, standalone)
# ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä

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
    ?åÊôØ‰ªªÂ?ÔºöÊì∑?ñÁ∂≤??URL ?ßÂÆπ‰∏¶Â??èÂ???

    ÊµÅÁ?Ôº?
    1. ‰ΩøÁî® trafilatura ?ΩÂ?Á∂≤È??áÂ?
    2. ?áÂ?
    3. ÂµåÂÖ•?ëÈ?
    4. ÂØ´ÂÖ• pgvector
    """
    db = None

    try:
        db = create_session(tenant_id=tenant_id)
        doc = crud_document.get_for_tenant(
            db, document_id=UUID(document_id), tenant_id=UUID(tenant_id)
        )
        if not doc:
            raise ValueError("?á‰ª∂Ë®òÈ?‰∏çÂ???)

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(status="parsing"),
        )

        # 1. ?ΩÂ?Á∂≤È?
        try:
            text_content, metadata = DocumentParser.parse_url(url)
        except Exception as e:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message=f"Á∂≤È??ΩÂ?Â§±Ê?: {e}"),
            )
            return {"status": "failed", "error": str(e)}

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(quality_report=metadata),
        )

        # 2. ?áÂ?
        chunks = TextChunker.split_by_tokens(
            text_content,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        if not chunks:
            crud_document.update(
                db, db_obj=doc,
                obj_in=DocumentUpdate(status="failed", error_message="Á∂≤È??ßÂÆπ?áÂ?ÂæåÁÑ°?âÊ??ßÂÆπ"),
            )
            return {"status": "failed", "error": "No valid chunks from URL"}

        crud_document.update(
            db, db_obj=doc,
            obj_in=DocumentUpdate(status="embedding", chunk_count=len(chunks)),
        )

        # 3. ÂµåÂÖ•?ëÈ?
        if not settings.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY ?™Ë®≠ÂÆ?)

        voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            last_err = None
            for attempt in range(3):
                try:
                    result = voyage_breaker.call(
                        voyage_client.embed,
                        batch,
                        model=settings.VOYAGE_MODEL,
                        input_type="document",
                    )
                    all_embeddings.extend(result.embeddings)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "Voyage embed batch %d attempt %d/3 failed: %s",
                        i // batch_size, attempt + 1, e,
                    )
                    time.sleep(2 ** attempt)
            if last_err is not None:
                raise last_err
            time.sleep(0.5)

        # 4. ÂØ´ÂÖ• pgvectorÔºàÂê´?ªÈ?Ôº?
        from app.models.document import DocumentChunk as DChunk

        inserted = 0
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]

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

        # Ê∏ÖÈô§Âø´Â?
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
        _mark_failed(db, document_id, "‰ªªÂ?Ë∂ÖÊ?ÔºåÂ∑≤‰∏≠Ê≠¢?ïÁ?")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": "task soft time limit exceeded"}

    except Exception as e:
        _mark_failed(db, document_id, str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e)}

    finally:
        if db is not None:
            db.close()
