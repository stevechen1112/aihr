"""
UniHR Langfuse LLMOps 可觀測性客戶端

提供全域 Langfuse 實例，用於追蹤：
  - LlamaParse 文檔解析成本
  - Voyage AI embedding / rerank token 數
  - RAG 檢索品質分數與 Gemini 生成 token
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_langfuse_instance = None
_langfuse_init_attempted = False

try:
    from langfuse import Langfuse

    _HAS_LANGFUSE = True
except ImportError:
    _HAS_LANGFUSE = False


def get_langfuse() -> Optional["Langfuse"]:
    """回傳全域 Langfuse 實例（單例），未啟用時回傳 None。"""
    global _langfuse_instance, _langfuse_init_attempted

    if _langfuse_init_attempted:
        return _langfuse_instance
    _langfuse_init_attempted = True
    _langfuse_instance = _init_langfuse()
    return _langfuse_instance


def _init_langfuse() -> Optional["Langfuse"]:
    global _langfuse_instance

    if not _HAS_LANGFUSE:
        logger.info("langfuse 套件未安裝，LLMOps 追蹤停用")
        return None

    from app.config import settings

    if not settings.LANGFUSE_ENABLED:
        logger.info("LANGFUSE_ENABLED=False，LLMOps 追蹤停用")
        return None

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.warning("Langfuse API keys 未設定，LLMOps 追蹤停用")
        return None

    try:
        instance = Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_HOST,
        )
        logger.info("Langfuse LLMOps 追蹤已啟用 (host=%s)", settings.LANGFUSE_HOST)
        return instance
    except Exception as e:
        logger.error("Langfuse 初始化失敗: %s", e)
        return None
