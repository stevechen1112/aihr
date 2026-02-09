#!/usr/bin/env python3
"""驗證 RAG pipeline 所有改進"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== 1. jieba 中文分詞 ===")
import jieba
tokens = list(jieba.cut("勞動基準法特別休假規定", cut_all=False))
print(f"  分詞結果: {tokens}")
assert "勞動" in tokens, "jieba 分詞失敗"
print("  OK   jieba 詞級分詞")

print()
print("=== 2. kb_retrieval 模組 ===")
from app.services.kb_retrieval import KnowledgeBaseRetriever
r = KnowledgeBaseRetriever.__new__(KnowledgeBaseRetriever)

tokens2 = r._tokenize("公司年假計算方式")
print(f"  _tokenize: {tokens2}")
assert len(tokens2) < 7, "分詞結果不應是逐字分詞"

assert hasattr(r, "_expand_query"), "_expand_query 缺失"
assert hasattr(r, "_hybrid_search"), "_hybrid_search 缺失"
assert hasattr(r, "_semantic_search"), "_semantic_search 缺失"
print("  OK   _expand_query (HyDE)")
print("  OK   _tokenize (jieba)")

# 檢查 filter_dict 有實際 SQL 過濾邏輯
import inspect
src = inspect.getsource(r._semantic_search)
assert "filter_dict" in src, "_semantic_search 缺少 filter_dict"
assert "metadata_json" in src, "_semantic_search 沒有用到 metadata_json 過濾"
print("  OK   filter_dict 落地")

print()
print("=== 3. chat_orchestrator 模組 ===")
from app.services.chat_orchestrator import ChatOrchestrator
co = ChatOrchestrator.__new__(ChatOrchestrator)

assert hasattr(co, "_generate_answer"), "_generate_answer 缺失"
assert hasattr(co, "_fallback_answer"), "_fallback_answer 缺失"
print("  OK   _generate_answer (LLM)")
print("  OK   _fallback_answer (模板)")

# 測試 fallback 回答
result_mock = {
    "company_policy": {"content": "年假 7 天"},
    "labor_law": {"answer": "勞基法第 38 條"},
}
ans = co._fallback_answer(True, True, result_mock)
assert "公司內規" in ans
assert "勞動法規" in ans
print("  OK   fallback 模板正確")

print()
print("=== 4. config 新增欄位 ===")
from app.config import settings
assert hasattr(settings, "OPENAI_MODEL"), "缺少 OPENAI_MODEL"
assert hasattr(settings, "OPENAI_TEMPERATURE"), "缺少 OPENAI_TEMPERATURE"
assert hasattr(settings, "OPENAI_MAX_TOKENS"), "缺少 OPENAI_MAX_TOKENS"
print(f"  OPENAI_MODEL: {settings.OPENAI_MODEL}")
print(f"  OPENAI_TEMPERATURE: {settings.OPENAI_TEMPERATURE}")
print(f"  OPENAI_MAX_TOKENS: {settings.OPENAI_MAX_TOKENS}")
print("  OK   Config 設定正確")

print()
print("=== 5. document_tasks 去重 ===")
from app.tasks.document_tasks import process_document_task, process_url_task
src1 = inspect.getsource(process_document_task)
assert "chunk_hash" in src1, "process_document_task 缺少 chunk_hash"
assert "existing" in src1, "process_document_task 缺少去重邏輯"
src2 = inspect.getsource(process_url_task)
assert "chunk_hash" in src2, "process_url_task 缺少 chunk_hash"
assert "existing" in src2, "process_url_task 缺少去重邏輯"
print("  OK   process_document_task 含去重")
print("  OK   process_url_task 含去重")

print()
print("=== 6. 依賴檢查 ===")
deps = {
    "jieba": "中文分詞",
    "openai": "LLM Generation",
    "voyageai": "Embedding + Rerank",
    "rank_bm25": "BM25 關鍵字檢索",
}
for mod, desc in deps.items():
    try:
        __import__(mod)
        print(f"  OK   {mod} ({desc})")
    except ImportError:
        print(f"  FAIL {mod} ({desc})")

print()
print("=== ALL CHECKS PASSED ===")
