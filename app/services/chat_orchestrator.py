import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from uuid import UUID
import uuid
from app.config import settings
from app.services.kb_retrieval import KnowledgeBaseRetriever
from app.services.core_client import CoreAPIClient

logger = logging.getLogger(__name__)

# ── 可選依賴 ──
try:
    import openai as openai_lib
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class ChatOrchestrator:
    """
    聊天協調器（RAG Generation 層）

    負責：
    1. 並行查詢公司內規 + 勞資法 Core API
    2. 使用 LLM 根據檢索結果生成上下文感知的回答
    3. 附帶來源引用與法律免責聲明
    4. 支援串流生成 (T7-1) 與多輪對話 (T7-2)
    """

    SYSTEM_PROMPT = """你是 UniHR 人資 AI 助理，專門回答台灣企業的人事規章與勞動法規問題。

回答規則：
1. **只根據下方提供的參考資料回答**，不要自行捏造或引用未提供的內容
2. 如果有公司內規，以公司內規為主，法律規定為輔助參照
3. 如果公司內規的規定**低於**勞動法的最低標準，必須明確指出
4. 使用結構化格式（標題、條列）讓回答清楚易讀
5. 引用資料時標註來源（檔名或法條名稱）
6. 如果參考資料不足以回答，坦白說明並建議諮詢 HR 部門
7. 使用繁體中文回答"""

    FOLLOWUP_PROMPT = """

在回答的最後，請另起一行輸出 2-3 個使用者可能會追問的建議問題，格式：
[建議問題]
1. ...
2. ...
3. ..."""
    
    def __init__(self):
        self.kb_retriever = KnowledgeBaseRetriever()
        self.core_client = CoreAPIClient()

        # OpenAI client (sync + async)
        self._openai = None
        self._openai_async = None
        openai_key = getattr(settings, "OPENAI_API_KEY", "")
        if _HAS_OPENAI and openai_key:
            self._openai = openai_lib.OpenAI(api_key=openai_key)
            self._openai_async = openai_lib.AsyncOpenAI(api_key=openai_key)

    # ──────────── T7-0: 檢索層（與生成解耦） ────────────

    async def retrieve_context(
        self,
        tenant_id: UUID,
        question: str,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        純檢索：並行查詢公司內規 + 勞資法 Core API，回傳結構化上下文。
        
        分離自原 process_query，使串流端點可先取得來源，再分段生成。
        """
        request_id = str(uuid.uuid4())

        async def get_company_policy():
            try:
                results = self.kb_retriever.search(
                    tenant_id=tenant_id,
                    query=question,
                    top_k=top_k,
                )
                return {"status": "success", "results": results}
            except Exception as e:
                return {"status": "error", "error": str(e), "results": []}

        async def get_labor_law():
            try:
                result = await self.core_client.chat(
                    question=question,
                    request_id=request_id,
                )
                return result
            except Exception as e:
                return {"status": "error", "answer": "勞資法查詢失敗", "error": str(e)}

        company_policy_result, labor_law_result = await asyncio.gather(
            asyncio.create_task(get_company_policy()),
            asyncio.create_task(get_labor_law()),
        )

        # ── 組裝結構化上下文 ──
        return self._build_context(
            question=question,
            company_policy=company_policy_result,
            labor_law=labor_law_result,
            request_id=request_id,
        )

    def _build_context(
        self,
        question: str,
        company_policy: Dict[str, Any],
        labor_law: Dict[str, Any],
        request_id: str,
    ) -> Dict[str, Any]:
        """將 raw 檢索結果組裝為結構化 context dict。"""
        has_policy = (
            company_policy.get("status") == "success"
            and len(company_policy.get("results", [])) > 0
        )
        has_labor_law = (
            labor_law.get("status") != "error" and labor_law.get("answer")
        )

        context: Dict[str, Any] = {
            "request_id": request_id,
            "question": question,
            "has_policy": has_policy,
            "has_labor_law": has_labor_law,
            "company_policy_raw": None,
            "labor_law_raw": None,
            "context_parts": [],
            "sources": [],
            "disclaimer": "本回答僅供參考，不構成正式法律意見。如有具體情況，請諮詢專業法律顧問。",
        }

        if has_policy:
            top_policies = company_policy["results"][:3]
            context["company_policy_raw"] = {
                "content": top_policies[0]["content"],
                "source": top_policies[0]["filename"],
                "relevance_score": top_policies[0]["score"],
                "all_results": [
                    {
                        "content": r["content"][:500],
                        "filename": r["filename"],
                        "score": r["score"],
                    }
                    for r in top_policies
                ],
            }
            for r in top_policies:
                context["sources"].append({
                    "type": "policy",
                    "title": r["filename"],
                    "snippet": r["content"][:200],
                    "score": r["score"],
                })
            for i, r in enumerate(top_policies, 1):
                context["context_parts"].append(
                    f"【公司內規 #{i}】（來源：{r['filename']}，相關度：{r['score']:.2f}）\n{r['content']}"
                )

        if has_labor_law:
            context["labor_law_raw"] = {
                "answer": labor_law.get("answer", ""),
                "citations": labor_law.get("citations", []),
                "usage": labor_law.get("usage", {}),
            }
            if labor_law.get("citations"):
                for citation in labor_law["citations"]:
                    law_name = citation.get("law_name") or "勞動法規"
                    article = citation.get("article") or ""
                    title = f"{law_name} {article}".strip()
                    context["sources"].append({
                        "type": "law",
                        "title": title,
                        "snippet": labor_law.get("answer", "")[:200],
                    })
            law_text = labor_law.get("answer", "")
            citations_text = ""
            if labor_law.get("citations"):
                citations_text = "；".join(
                    f"{c.get('law_name', '')} {c.get('article', '')}"
                    for c in labor_law["citations"]
                )
            context["context_parts"].append(
                f"【勞動法規】{citations_text}\n{law_text}"
            )

        return context

    # ──────────── T7-1: 串流生成 ────────────

    async def stream_answer(
        self,
        question: str,
        context: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None,
        include_followup: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        串流生成 LLM 回答（SSE 用）。

        yield 每個 token chunk，前端可逐字渲染。
        若 LLM 不可用，則 yield 整段 fallback。
        """
        if not self._openai_async or not (context["has_policy"] or context["has_labor_law"]):
            yield self._fallback_answer(context)
            return

        messages = self._build_llm_messages(
            question, context, history=history, include_followup=include_followup
        )

        try:
            response = await self._openai_async.chat.completions.create(
                model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=getattr(settings, "OPENAI_TEMPERATURE", 0.3),
                max_tokens=getattr(settings, "OPENAI_MAX_TOKENS", 1500),
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            logger.warning(f"LLM 串流生成失敗，回退到模板: {e}")
            yield self._fallback_answer(context)

    # ──────────── T7-2: 多輪對話支援 ────────────

    async def contextualize_query(
        self, query: str, history: List[Dict[str, str]]
    ) -> str:
        """
        用 LLM 將含代名詞/省略主詞的查詢改寫為獨立查詢。
        若歷史為空或 LLM 不可用，直接回傳原 query。
        """
        if not history or not self._openai_async:
            return query

        messages = [
            {
                "role": "system",
                "content": (
                    "根據對話歷史，將使用者的最新問題改寫為一個獨立、完整的查詢。"
                    "只輸出改寫後的查詢，不要解釋。如果問題已經夠明確，直接原樣輸出。"
                ),
            },
            *[{"role": m["role"], "content": m["content"]} for m in history[-4:]],
            {"role": "user", "content": query},
        ]

        try:
            response = await self._openai_async.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"查詢改寫失敗: {e}")
            return query

    # ──────────── 向下相容：保留原 process_query ────────────

    async def process_query(
        self,
        tenant_id: UUID,
        question: str,
        top_k: int = 3,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        處理用戶查詢（非串流，向下相容）。
        
        新增 conversation_id / history 參數以支援多輪對話。
        """
        # 查詢改寫（多輪）
        effective_question = question
        if history:
            effective_question = await self.contextualize_query(question, history)

        # 檢索
        ctx = await self.retrieve_context(
            tenant_id=tenant_id,
            question=effective_question,
            top_k=top_k,
        )

        # 生成回答（非串流）
        result = {
            "request_id": ctx["request_id"],
            "question": question,
            "company_policy": ctx["company_policy_raw"],
            "labor_law": ctx["labor_law_raw"],
            "answer": "",
            "sources": ctx["sources"],
            "notes": [],
            "disclaimer": ctx["disclaimer"],
        }

        if self._openai and (ctx["has_policy"] or ctx["has_labor_law"]):
            try:
                result["answer"] = self._generate_answer_sync(
                    question, ctx, history=history
                )
                result["notes"].append("由 AI 根據檢索結果生成回答")
            except Exception as e:
                logger.warning(f"LLM 回答生成失敗，回退到模板: {e}")
                result["answer"] = self._fallback_answer(ctx)
                result["notes"].append("LLM 暫時無法使用，以結構化格式呈現")
        else:
            result["answer"] = self._fallback_answer(ctx)
            if not (ctx["has_policy"] or ctx["has_labor_law"]):
                result["notes"].append("未找到相關資訊")

        return result

    # ──────────── LLM Messages 組裝（共用） ────────────

    def _build_llm_messages(
        self,
        question: str,
        context: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None,
        include_followup: bool = True,
    ) -> List[Dict[str, str]]:
        """組裝 LLM 的 messages 陣列（含歷史 + 檢索上下文）。"""
        system_content = self.SYSTEM_PROMPT
        if include_followup:
            system_content += self.FOLLOWUP_PROMPT

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        # 注入歷史（Token 預算管理）
        if history:
            max_history_tokens = 2000
            total_tokens = 0
            history_msgs = []
            for msg in reversed(history):
                # 粗估 1 中文字 ≈ 2 tokens
                msg_tokens = len(msg["content"])
                if total_tokens + msg_tokens > max_history_tokens:
                    break
                history_msgs.insert(0, {"role": msg["role"], "content": msg["content"]})
                total_tokens += msg_tokens
            messages.extend(history_msgs)

        context_text = "\n\n".join(context["context_parts"])
        user_content = f"問題：{question}\n\n參考資料：\n{context_text}\n\n請根據上述參考資料回答問題。"
        messages.append({"role": "user", "content": user_content})

        return messages

    # ──────────── 同步生成（相容原介面） ────────────

    def _generate_answer_sync(
        self,
        question: str,
        context: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """同步 LLM 生成回答（非串流）。"""
        messages = self._build_llm_messages(question, context, history=history)

        response = self._openai.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=getattr(settings, "OPENAI_TEMPERATURE", 0.3),
            max_tokens=getattr(settings, "OPENAI_MAX_TOKENS", 1500),
        )
        return response.choices[0].message.content.strip()

    # ──────────── Fallback ────────────

    @staticmethod
    def _fallback_answer(context: Dict[str, Any]) -> str:
        """LLM 不可用時的模板 fallback。"""
        has_policy = context.get("has_policy", False)
        has_labor_law = context.get("has_labor_law", False)

        if has_policy and has_labor_law:
            policy_content = context["company_policy_raw"]["content"][:500]
            law_answer = context["labor_law_raw"]["answer"][:500]
            return f"""📋 **公司內規規定**：
{policy_content}

⚖️ **勞動法規補充**：
{law_answer}

💡 **說明**：公司內規是您的優先參考依據，但不得違反勞動法的最低標準。"""

        elif has_policy:
            return f"""📋 **公司內規規定**：
{context["company_policy_raw"]["content"]}

💡 **提醒**：未查詢到相關勞動法規補充。如需了解法律最低標準，請進一步諮詢。"""

        elif has_labor_law:
            return f"""⚖️ **勞動法規**：
{context["labor_law_raw"]["answer"]}

💡 **提醒**：未在公司內規中找到相關規定。建議確認公司是否有額外規定。"""

        else:
            return "抱歉，未找到相關資訊。請嘗試換個方式提問，或聯繫 HR 部門。"

    def format_summary(self, result: Dict[str, Any]) -> str:
        """格式化摘要（用於顯示）"""
        summary = f"**問題**：{result['question']}\n\n"
        summary += result["answer"]

        if result["sources"]:
            summary += "\n\n**參考來源**：\n"
            for source in result["sources"]:
                if source["type"] == "company_policy":
                    summary += f"- 📋 {source['filename']} (相關度: {source['score']:.2f})\n"
                elif source["type"] == "labor_law":
                    summary += f"- ⚖️ {source.get('law_name', '勞動法規')} {source.get('article', '')}\n"

        summary += f"\n\n{result['disclaimer']}"
        return summary
