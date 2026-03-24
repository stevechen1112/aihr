import logging
import json
import re
import asyncio
from datetime import date
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from uuid import UUID
import uuid
from app.config import settings
from app.services.kb_retrieval import KnowledgeBaseRetriever
from app.services.core_client import CoreAPIClient
from app.services.structured_answers import try_structured_answer
from app.services.hr_calculator import try_hr_calculation
from app.services.circuit_breaker import gemini_breaker

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
4. 若公司內規高於法定最低標準，屬合法且應明確指出
5. 若參考資料中出現「測試陷阱／提醒／警示」，需依其內容修正結論並點出原因
6. 使用結構化格式（標題、條列）讓回答清楚易讀
7. 引用法律時**必須**使用《法律名稱》第X條格式（例如：《勞動基準法》第38條），絕對不能只寫法律名稱。
   若用戶訊息結尾有「⚠️ 以下法條已在參考資料中明確提及」的清單，每一條都必須出現在回答中
8. 如果參考資料不足以回答，坦白說明並建議諮詢 HR 部門
9. 使用繁體中文回答
10. 需要數值計算時，請列出公式與代入值，嚴格依公式計算"""

    FOLLOWUP_PROMPT = """

在回答的最後，請另起一行輸出 2-3 個使用者可能會追問的建議問題，格式：
[建議問題]
1. ...
2. ...
3. ..."""
    
    def __init__(self):
        self.kb_retriever = KnowledgeBaseRetriever()
        self.core_client = CoreAPIClient()
        self._llm_backend = getattr(settings, "LLM_BACKEND", "gemini").strip().lower()
        self._llm_available = False
        self._source_priority_mode = getattr(settings, "SOURCE_PRIORITY_MODE", "adaptive")
        self._policy_source_weight = float(getattr(settings, "POLICY_SOURCE_WEIGHT", 0.65))
        self._law_source_weight = float(getattr(settings, "LAW_SOURCE_WEIGHT", 0.35))
        self._conflict_resolution_mode = getattr(settings, "CONFLICT_RESOLUTION_MODE", "legal_floor")

        # Gemini client (via OpenAI-compatible endpoint)
        self._openai = None
        self._openai_async = None
        _GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
        if self._llm_backend == "gemini":
            if _HAS_OPENAI:
                gemini_key = getattr(settings, "GEMINI_API_KEY", "")
                if gemini_key:
                    self._openai = openai_lib.OpenAI(api_key=gemini_key, base_url=_GEMINI_BASE)
                    self._openai_async = openai_lib.AsyncOpenAI(api_key=gemini_key, base_url=_GEMINI_BASE)
                    self._llm_available = True
                else:
                    logger.warning("LLM_BACKEND=gemini 但 GEMINI_API_KEY 未設定，將回退到模板回答")
            else:
                logger.warning("缺少 openai 套件，無法使用 gemini backend，將回退到模板回答")
        elif self._llm_backend == "core":
            self._llm_available = True
        else:
            logger.warning(f"未知 LLM_BACKEND={self._llm_backend}，將回退到模板回答")

    def _model_name(self) -> str:
        return getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash-preview")

    @staticmethod
    def _messages_to_core_prompt(messages: List[Dict[str, str]]) -> str:
        prompt_parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"[{role}]\n{content}")
        return "\n\n".join(prompt_parts)

    async def _llm_generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if self._llm_backend == "gemini" and self._openai_async:
            response = await gemini_breaker.call_async(
                self._openai_async.chat.completions.create,
                model=self._model_name(),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()

        if self._llm_backend == "core":
            core_prompt = self._messages_to_core_prompt(messages)
            core_resp = await self.core_client.chat(question=core_prompt, request_id=str(uuid.uuid4()))
            if core_resp.get("status") == "error":
                raise RuntimeError(core_resp.get("error") or "core generation failed")
            answer = core_resp.get("answer") or core_resp.get("message") or ""
            if not answer:
                answer = json.dumps(core_resp, ensure_ascii=False)
            return answer.strip()

        raise RuntimeError("LLM backend unavailable")

    # ──────────── T7-0: 檢索層（與生成解耦） ────────────

    async def retrieve_context(
        self,
        tenant_id: UUID,
        question: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        純檢索：並行查詢公司內規 + 勞資法 Core API，回傳結構化上下文。
        
        分離自原 process_query，使串流端點可先取得來源，再分段生成。
        """
        request_id = str(uuid.uuid4())

        async def get_company_policy():
            try:
                # run_in_executor：search() 含同步 Voyage embed/rerank 呼叫
                # 若直接在 async def 中呼叫會阻塞 event loop，
                # 導致 asyncio.gather() 無法真正並行。
                results = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.kb_retriever.search(
                        tenant_id=tenant_id,
                        query=question,
                        top_k=top_k,
                    ),
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

        retrieval_timeout = max(1, int(getattr(settings, "CHAT_RETRIEVAL_TIMEOUT_SECONDS", 20)))

        async def with_timeout(coro, fallback: Dict[str, Any], label: str):
            try:
                return await asyncio.wait_for(coro, timeout=retrieval_timeout)
            except asyncio.TimeoutError:
                logger.warning("%s timed out after %ss", label, retrieval_timeout)
                timed_out = dict(fallback)
                timed_out["error"] = "timeout"
                return timed_out

        company_policy_result, labor_law_result = await asyncio.gather(
            with_timeout(
                get_company_policy(),
                {"status": "error", "results": []},
                "company policy retrieval",
            ),
            with_timeout(
                get_labor_law(),
                {"status": "error", "answer": "勞資法查詢逾時"},
                "labor law retrieval",
            ),
        )

        # 內規補強：根據問題關鍵字做語意補強檢索（同樣用 executor 避免阻塞）
        boosted_results = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self._policy_boost_search(tenant_id, question, top_k),
        )
        if boosted_results and company_policy_result.get("status") == "success":
            base_results = company_policy_result.get("results", [])
            merged = self._merge_policy_results(base_results, boosted_results, top_k)
            company_policy_result["status"] = "success"
            company_policy_result["results"] = merged

        # ── 組裝結構化上下文 ──
        return self._build_context(
            question=question,
            company_policy=company_policy_result,
            labor_law=labor_law_result,
            request_id=request_id,
        )

    def _policy_boost_search(
        self, tenant_id: UUID, question: str, top_k: int
    ) -> List[Dict[str, Any]]:
        keywords = self._policy_hint_keywords(question)
        if not keywords:
            return []
        try:
            # 用語意查詢片段做補強搜尋（不限制檔名）
            boost_query = " ".join(keywords)
            return self.kb_retriever.search(
                tenant_id=tenant_id,
                query=boost_query,
                top_k=top_k,
                mode="semantic",
                rerank=False,
            )
        except Exception:
            return []

    @staticmethod
    def _policy_hint_keywords(question: str) -> List[str]:
        """
        根據問題關鍵字回傳適合做語意補強的搜尋查詢。
        不再硬編碼檔名，改為回傳語意查詢片段讓 retriever 做廣泛搜尋。
        """
        hints: List[str] = []
        if any(k in question for k in ["績效", "考核", "KPI"]):
            hints.append("績效考核辦法")
        if any(k in question for k in ["解僱", "終止契約", "開除"]):
            hints.append("解僱 終止勞動契約 資遣")
        if any(k in question for k in ["報帳", "計程車", "憑證", "發票", "出差"]):
            hints.append("報帳作業規範")
        if any(k in question for k in ["新人", "報到", "到職", "試用期"]):
            hints.append("新人到職 試用期")
        if "喪假" in question:
            hints.append("喪假 父母 配偶 祖父母 天數")
        if any(k in question for k in ["特休", "婚假", "生理假", "產假",
                                        "陪產", "請假", "年假", "特別休假", "假期"]):
            hints.append("請假規定 特休假")
        if any(k in question for k in ["年終獎金", "獎懲", "獎金"]):
            hints.append("獎懲管理 年終獎金")
        if any(k in question for k in ["加班", "延長工時"]):
            hints.append("加班規定 延長工時")
        if any(k in question for k in ["交通津貼", "津貼", "補貼"]):
            hints.append("交通津貼 補貼")
        if any(k in question for k in ["勞保", "健保", "保費"]):
            hints.append("勞保 健保 保費")
        if any(k in question for k in ["健檢", "健康檢查", "體檢"]):
            hints.append("健康檢查報告")
        if any(k in question for k in ["薪資", "薪水", "實領", "月薪", "底薪"]):
            hints.append("薪資條 薪資明細")
        return hints

    @staticmethod
    def _merge_policy_results(
        base: List[Dict[str, Any]],
        extra: List[Dict[str, Any]],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        seen = set()
        merged: List[Dict[str, Any]] = []
        for item in extra + base:
            key = item.get("id") or f"{item.get('document_id')}:{item.get('chunk_index')}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= max_results:
                break
        return merged

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
        arbitration = self._decide_source_arbitration(
            question=question,
            has_policy=has_policy,
            has_labor_law=bool(has_labor_law),
        )

        context: Dict[str, Any] = {
            "request_id": request_id,
            "question": question,
            "has_policy": has_policy,
            "has_labor_law": has_labor_law,
            "labor_law_status": labor_law.get("status"),
            "labor_law_error": labor_law.get("error"),
            "company_policy_raw": None,
            "labor_law_raw": None,
            "context_parts": [],
            "sources": [],
            "arbitration": arbitration,
            "requires_law_source": bool(arbitration.get("is_legal_sensitive")),
            "refusal_reason": None,
            "disclaimer": "本回答僅供參考，不構成正式法律意見。如有具體情況，請諮詢專業法律顧問。",
        }

        policy_context_parts: List[str] = []
        law_context_parts: List[str] = []

        if has_policy:
            top_policies = company_policy["results"][:3]
            context["company_policy_raw"] = {
                "content": top_policies[0].get("content") or "",
                "source": top_policies[0].get("filename") or "",
                "relevance_score": top_policies[0].get("score") or 0,
                "all_results": [
                    {
                        "content": (r.get("content") or "")[:500],
                        "filename": r.get("filename") or "",
                        "score": r.get("score") or 0,
                    }
                    for r in top_policies
                ],
            }
            for r in top_policies:
                context["sources"].append({
                    "type": "policy",
                    "title": r.get("filename") or "",
                    "snippet": (r.get("content") or "")[:200],
                    "score": r.get("score") or 0,
                })
            for i, r in enumerate(top_policies, 1):
                content = r.get("content") or ""
                filename = r.get("filename") or ""
                score = r.get("score") or 0
                policy_context_parts.append(
                    f"【公司內規 #{i}】（來源：{filename}，相關度：{score:.2f}）\n{content}"
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
                    # 格式化為 《勞動基準法》第17條 形式
                    if article:
                        title = f"《{law_name}》第{article}" if not article.startswith("第") else f"《{law_name}》{article}"
                    else:
                        title = f"《{law_name}》"
                    context["sources"].append({
                        "type": "law",
                        "title": title,
                        "snippet": labor_law.get("answer", "")[:200],
                    })
            else:
                # Core API 不回傳結構化 citations，從回答文字中解析法條引用
                answer_text = labor_law.get("answer") or ""
                if answer_text:
                    law_refs = re.findall(r'《(.+?)》(?:第(\d+[-之]?\d*條?))?', answer_text)
                    if law_refs:
                        seen = set()
                        for law_name, article in law_refs[:5]:
                            # 格式化為 《勞動基準法》第17條 形式
                            title = f"《{law_name}》第{article}" if article else f"《{law_name}》"
                            if title not in seen:
                                seen.add(title)
                                context["sources"].append({
                                    "type": "law",
                                    "title": title,
                                    "snippet": answer_text[:200],
                                })
                    else:
                        context["sources"].append({
                            "type": "law",
                            "title": "勞動法規 (Core API)",
                            "snippet": answer_text[:200],
                        })
            law_text = labor_law.get("answer", "")
            citations_text = ""
            if labor_law.get("citations"):
                citations_text = "；".join(
                    f"{c.get('law_name', '')} {c.get('article', '')}"
                    for c in labor_law["citations"]
                )
            elif law_text:
                # Core API 不回傳結構化 citations，從 answer 文字解析法條做為 heading
                parsed = re.findall(r'《(.+?)》(?:第([\d\-之]+條(?:之\d+)?))?', law_text)
                seen_cit: set = set()
                unique_cit: list = []
                for law_n, art_n in parsed[:8]:
                    key = f"《{law_n}》第{art_n}條" if art_n else f"《{law_n}》"
                    if key not in seen_cit:
                        seen_cit.add(key)
                        unique_cit.append(key)
                if unique_cit:
                    citations_text = "（法源：" + "、".join(unique_cit) + "）"
            law_context_parts.append(
                f"【勞動法規】{citations_text}\n{law_text}"
            )

        if arbitration["primary_source"] == "law":
            context["context_parts"].extend(law_context_parts + policy_context_parts)
        else:
            context["context_parts"].extend(policy_context_parts + law_context_parts)

        if context["requires_law_source"] and not has_labor_law:
            detail = context.get("labor_law_error") or "法規來源暫時不可用"
            context["refusal_reason"] = (
                "此問題涉及法規判斷，且法規來源目前無法驗證（"
                f"{detail}），為避免提供不準確或過期法規資訊，請稍後再試或改由法規資料可用時查詢。"
            )

        return context

    @staticmethod
    def _clamp_weight(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _decide_source_arbitration(
        self,
        question: str,
        has_policy: bool,
        has_labor_law: bool,
    ) -> Dict[str, Any]:
        policy_weight = self._clamp_weight(self._policy_source_weight)
        law_weight = self._clamp_weight(self._law_source_weight)

        lower_q = (question or "").lower()
        is_legal_sensitive = any(k in lower_q for k in self._LEGAL_SENSITIVE_KEYWORDS)
        is_policy_sensitive = any(k in lower_q for k in self._POLICY_SENSITIVE_KEYWORDS)

        if is_legal_sensitive and has_labor_law:
            law_weight = self._clamp_weight(law_weight + 0.2)
            policy_weight = self._clamp_weight(policy_weight - 0.2)
        elif is_policy_sensitive and has_policy:
            policy_weight = self._clamp_weight(policy_weight + 0.2)
            law_weight = self._clamp_weight(law_weight - 0.2)

        if not has_policy and not has_labor_law:
            primary_source = "none"
        elif not has_policy:
            primary_source = "law"
        elif not has_labor_law:
            primary_source = "policy"
        elif self._source_priority_mode == "policy_first":
            primary_source = "policy"
        elif self._source_priority_mode == "law_first":
            primary_source = "law"
        else:
            primary_source = "policy" if policy_weight >= law_weight else "law"

        secondary_source = "none"
        if primary_source == "policy":
            secondary_source = "law"
        elif primary_source == "law":
            secondary_source = "policy"

        return {
            "priority_mode": self._source_priority_mode,
            "conflict_mode": self._conflict_resolution_mode,
            "policy_weight": round(policy_weight, 2),
            "law_weight": round(law_weight, 2),
            "primary_source": primary_source,
            "secondary_source": secondary_source,
            "is_legal_sensitive": is_legal_sensitive,
            "is_policy_sensitive": is_policy_sensitive,
        }

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
        block_reason = self._guardrail_block_reason(question)
        if block_reason:
            logger.warning("Guardrail blocked stream query: %s", block_reason)
            yield "為確保資料與系統安全，此問題包含疑似越權或提示詞操控指令，請改為具體的人資制度或法規問題。"
            return

        input_sensitive = self._sensitive_content_reason(question, direction="input")
        if input_sensitive:
            logger.warning("Sensitive input blocked in stream query: %s", input_sensitive)
            yield "此問題包含敏感資訊請求，為保護資料安全已拒絕處理。請移除敏感資料後再提問。"
            return

        law_unavailable_reason = self._law_source_unavailable_reason(context)
        if law_unavailable_reason:
            logger.warning("Legal-sensitive query refused due to missing law source")
            yield law_unavailable_reason
            return

        if not self._llm_available or not (context["has_policy"] or context["has_labor_law"]):
            yield self._fallback_answer(context)
            return

        messages = self._build_llm_messages(
            question, context, history=history, include_followup=include_followup
        )

        try:
            if self._llm_backend == "gemini" and self._openai_async:
                # Circuit breaker check (streaming path — record success/failure manually)
                from app.services.circuit_breaker import CircuitOpenError
                cb_state = gemini_breaker.state
                if cb_state.value == "open":
                    yield "目前 AI 模型暫時無法回應，請稍後再試。"
                    return
                try:
                    response = await self._openai_async.chat.completions.create(
                        model=self._model_name(),
                        messages=messages,
                        temperature=getattr(settings, "LLM_TEMPERATURE", 0.3),
                        max_tokens=getattr(settings, "LLM_MAX_TOKENS", 1500),
                        stream=True,
                    )
                except Exception:
                    gemini_breaker._on_failure()
                    raise
                gemini_breaker._on_success()
                async for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        output_sensitive = self._sensitive_content_reason(
                            delta.content,
                            direction="output",
                        )
                        if output_sensitive:
                            logger.warning("Sensitive output blocked in stream response: %s", output_sensitive)
                            yield "回覆內容含敏感資訊，已由安全機制中止輸出。"
                            return
                        yield delta.content
            else:
                answer = await self._llm_generate_async(
                    messages=messages,
                    temperature=getattr(settings, "LLM_TEMPERATURE", 0.3),
                    max_tokens=getattr(settings, "LLM_MAX_TOKENS", 1500),
                )
                output_sensitive = self._sensitive_content_reason(answer, direction="output")
                if output_sensitive:
                    logger.warning("Sensitive output blocked in non-stream path: %s", output_sensitive)
                    yield "回覆內容含敏感資訊，已由安全機制中止輸出。"
                    return
                yield answer
        except Exception as e:
            logger.warning(f"LLM 串流生成失敗，回退到模板: {e}")
            yield self._fallback_answer(context)

    # ──────────── T7-2: 多輪對話支援 ────────────

    # 需要上下文補全的代名詞／指示詞
    _CONTEXT_PRONOUNS = ("他", "她", "它", "他的", "她的", "他們", "她們",
                         "這個人", "那個人", "此人", "該員工", "同一", "上述", "前述")
    _LEGAL_SENSITIVE_KEYWORDS = (
        "勞基法", "法條", "違法", "合法", "罰則", "工資", "加班", "資遣", "解僱", "解雇",
        "特休", "請假", "工時", "最低", "法定", "勞保", "健保", "職災", "職業災害",
    )
    _POLICY_SENSITIVE_KEYWORDS = (
        "公司規定", "內規", "流程", "sop", "報帳", "報到", "簽核", "核銷", "表單", "制度",
        "員工手冊", "部門", "津貼", "獎懲", "考核",
    )
    _PROMPT_INJECTION_PATTERNS = (
        r"ignore\s+(all\s+)?(previous|above)\s+instructions",
        r"(reveal|show|print).{0,20}(system\s*prompt|developer\s*message)",
        r"請\s*忽略.{0,30}(規則|指示|說明|限制)",
        r"忽略.{0,20}(上述|前述|系統|提示詞)",
        r"顯示.{0,20}(系統提示詞|提示詞|system prompt)",
        r"越權",
    )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        other_chars = max(0, len(text) - cjk_chars)
        return max(1, cjk_chars * 2 + other_chars // 4)

    def _truncate_text_by_tokens(self, text: str, token_budget: int) -> str:
        if token_budget <= 0:
            return ""
        if self._estimate_tokens(text) <= token_budget:
            return text

        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if self._estimate_tokens(text[:mid]) <= token_budget:
                low = mid
            else:
                high = mid - 1
        return text[:low].rstrip()

    def _apply_context_budget(
        self,
        context_parts: List[str],
        token_budget: int,
    ) -> Tuple[str, bool]:
        if token_budget <= 0:
            return "", bool(context_parts)

        used = 0
        kept_parts: List[str] = []
        truncated = False

        for part in context_parts:
            remaining = token_budget - used
            if remaining <= 0:
                truncated = True
                break

            part_tokens = self._estimate_tokens(part)
            if part_tokens <= remaining:
                kept_parts.append(part)
                used += part_tokens
                continue

            clipped = self._truncate_text_by_tokens(part, remaining)
            if clipped:
                kept_parts.append(clipped)
            truncated = True
            break

        return "\n\n".join(kept_parts), truncated

    def _guardrail_block_reason(self, question: str) -> Optional[str]:
        if not getattr(settings, "LLM_GUARDRAIL_ENABLED", True):
            return None

        compiled_patterns = list(self._PROMPT_INJECTION_PATTERNS)
        extra_patterns = getattr(settings, "LLM_GUARDRAIL_BLOCK_PATTERNS", "")
        if extra_patterns:
            compiled_patterns.extend(
                p.strip() for p in extra_patterns.split(",") if p.strip()
            )

        for pattern in compiled_patterns:
            try:
                if re.search(pattern, question, flags=re.IGNORECASE):
                    return f"matched pattern: {pattern}"
            except re.error:
                if pattern.lower() in question.lower():
                    return f"matched keyword: {pattern}"
        return None

    def _sensitive_content_reason(self, text: str, *, direction: str) -> Optional[str]:
        if not getattr(settings, "LLM_IO_SENSITIVE_FILTER_ENABLED", True):
            return None

        configured = (
            getattr(settings, "LLM_INPUT_SENSITIVE_PATTERNS", "")
            if direction == "input"
            else getattr(settings, "LLM_OUTPUT_SENSITIVE_PATTERNS", "")
        )
        patterns = [p.strip() for p in configured.split(",") if p.strip()]

        for pattern in patterns:
            try:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return f"matched pattern: {pattern}"
            except re.error:
                if pattern.lower() in text.lower():
                    return f"matched keyword: {pattern}"
        return None

    @staticmethod
    def _law_source_unavailable_reason(context: Dict[str, Any]) -> Optional[str]:
        if context.get("requires_law_source") and not context.get("has_labor_law"):
            return context.get("refusal_reason") or (
                "此問題涉及法規判斷，但法規來源目前不可用，為避免錯誤法規建議，暫不提供結論。"
            )
        return None

    async def contextualize_query(
        self, query: str, history: List[Dict[str, str]]
    ) -> str:
        """
        用 LLM 將含代名詞/省略主詞的查詢改寫為獨立查詢。
        若歷史為空、LLM 不可用、或問題不含指代詞，直接回傳原 query。
        """
        if not history or not self._llm_available:
            return query

        # 智慧跳過：問題不含代名詞/指示詞時無需 LLM 改寫（節省 ~0.9s）
        if not any(p in query for p in self._CONTEXT_PRONOUNS):
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
            rewritten = await self._llm_generate_async(
                messages=messages,
                temperature=0,
                max_tokens=200,
            )
            return rewritten
        except Exception as e:
            logger.warning(f"查詢改寫失敗: {e}")
            return query

    # ──────────── 向下相容：保留原 process_query ────────────

    async def process_query(
        self,
        tenant_id: UUID,
        question: str,
        top_k: int = settings.RETRIEVAL_TOP_K,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        處理用戶查詢（非串流，向下相容）。
        
        新增 conversation_id / history 參數以支援多輪對話。
        """
        block_reason = self._guardrail_block_reason(question)
        if block_reason:
            logger.warning("Guardrail blocked suspicious query: %s", block_reason)
            return {
                "request_id": str(uuid.uuid4()),
                "question": question,
                "company_policy": None,
                "labor_law": None,
                "answer": "為確保資料與系統安全，此問題包含疑似越權或提示詞操控指令，無法直接執行。請改為具體的人資制度或法規問題。",
                "sources": [],
                "notes": ["Guardrail 已攔截疑似 Prompt Injection"],
                "disclaimer": "本回答僅供參考，不構成正式法律意見。如有具體情況，請諮詢專業法律顧問。",
            }

        input_sensitive = self._sensitive_content_reason(question, direction="input")
        if input_sensitive:
            logger.warning("Sensitive input blocked in process_query: %s", input_sensitive)
            return {
                "request_id": str(uuid.uuid4()),
                "question": question,
                "company_policy": None,
                "labor_law": None,
                "answer": "此問題包含敏感資訊請求，為保護資料安全已拒絕處理。請移除敏感資料後再提問。",
                "sources": [],
                "notes": ["Sensitive IO filter 已攔截輸入"],
                "disclaimer": "本回答僅供參考，不構成正式法律意見。如有具體情況，請諮詢專業法律顧問。",
            }

        structured = await asyncio.get_running_loop().run_in_executor(
            None, lambda: try_structured_answer(tenant_id, question, history=history)
        )
        if structured:
            return {
                "request_id": str(uuid.uuid4()),
                "question": question,
                "company_policy": None,
                "labor_law": None,
                "answer": structured.answer,
                "sources": structured.sources,
                "notes": ["使用結構化資料直接計算"],
                "disclaimer": "本回答僅供參考，不構成正式法律意見。如有具體情況，請諮詢專業法律顧問。",
            }
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

        law_unavailable_reason = self._law_source_unavailable_reason(ctx)
        if law_unavailable_reason:
            return {
                "request_id": ctx["request_id"],
                "question": question,
                "company_policy": ctx["company_policy_raw"],
                "labor_law": ctx["labor_law_raw"],
                "answer": law_unavailable_reason,
                "sources": ctx["sources"],
                "notes": ["法規來源失效，已觸發安全拒答"],
                "disclaimer": ctx["disclaimer"],
            }

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

        arbitration = ctx.get("arbitration") or {}
        if arbitration:
            result["notes"].append(
                "來源仲裁"
                f"(primary={arbitration.get('primary_source')}, "
                f"mode={arbitration.get('priority_mode')}, "
                f"conflict={arbitration.get('conflict_mode')})"
            )

        if self._llm_available and (ctx["has_policy"] or ctx["has_labor_law"]):
            try:
                generation_timeout = max(1, int(getattr(settings, "CHAT_GENERATION_TIMEOUT_SECONDS", 20)))
                result["answer"] = await asyncio.wait_for(
                    self._generate_answer(question, ctx, history=history),
                    timeout=generation_timeout,
                )
                output_sensitive = self._sensitive_content_reason(
                    result["answer"], direction="output"
                )
                if output_sensitive:
                    logger.warning("Sensitive output blocked in process_query: %s", output_sensitive)
                    result["answer"] = "回覆內容含敏感資訊，已由安全機制中止輸出。"
                    result["notes"].append("Sensitive IO filter 已攔截輸出")
                else:
                    result["notes"].append("由 AI 根據檢索結果生成回答")
            except asyncio.TimeoutError:
                logger.warning("LLM 回答生成逾時，回退到模板")
                result["answer"] = self._fallback_answer(ctx)
                result["notes"].append("LLM 生成逾時，以結構化格式呈現")
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
        today_str = f"{date.today().year}年{date.today().month}月{date.today().day}日"
        system_content = f"今天日期：{today_str}\n\n" + self.SYSTEM_PROMPT
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
                msg_tokens = self._estimate_tokens(msg["content"])
                if total_tokens + msg_tokens > max_history_tokens:
                    break
                history_msgs.insert(0, {"role": msg["role"], "content": msg["content"]})
                total_tokens += msg_tokens
            messages.extend(history_msgs)

        history_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in messages)
        history_summary = self._format_history_summary(history)
        calc_guidance = self._build_calc_guidance(question)
        arbitration = context.get("arbitration", {})
        conflict_mode = arbitration.get("conflict_mode", "legal_floor")
        if conflict_mode == "law_override":
            conflict_rule = "若公司內規與法規衝突，優先採用勞動法規。"
        elif conflict_mode == "policy_override":
            conflict_rule = "若公司內規與法規衝突，優先採用公司內規，並標註法規風險。"
        else:
            conflict_rule = (
                "若公司內規低於法定最低標準，必須以法規為準並明確指出差異；"
                "若公司內規高於法定標準，採公司內規。"
            )

        arbitration_text = (
            "來源仲裁設定："
            f"primary={arbitration.get('primary_source', 'policy')}，"
            f"secondary={arbitration.get('secondary_source', 'law')}，"
            f"policy_weight={arbitration.get('policy_weight', 0.65)}，"
            f"law_weight={arbitration.get('law_weight', 0.35)}，"
            f"priority_mode={arbitration.get('priority_mode', 'adaptive')}，"
            f"conflict_mode={conflict_mode}。"
        )

        user_prefix = f"問題：{question}\n\n參考資料：\n"
        if history_summary:
            user_prefix = f"對話歷史摘要：\n{history_summary}\n\n" + user_prefix

        user_suffix = "\n\n請根據上述參考資料回答問題。"
        user_suffix += f"\n\n{arbitration_text}\n衝突處理規則：{conflict_rule}"
        if calc_guidance:
            user_suffix += f"\n\n計算與判斷提示：\n{calc_guidance}"
        # 結構化計算引擎：精確數值結果注入
        exact_calc = try_hr_calculation(question)
        if exact_calc:
            user_suffix += f"\n\n{exact_calc}"
        # 明確列出已找到的法條，要求 LLM 逐一引用
        law_sources = [
            s["title"] for s in context.get("sources", [])
            if s.get("type") == "law" and "Core API" not in s.get("title", "")
        ]
        if law_sources:
            user_suffix += (
                f"\n\n⚠️ 以下法條已在參考資料中明確標示，請務必在回答中引用（不得省略）："
                f"{'、'.join(law_sources)}"
            )

        max_input_tokens = int(getattr(settings, "LLM_MAX_INPUT_TOKENS", 6000))
        reserve_tokens = int(getattr(settings, "LLM_CONTEXT_RESERVE_TOKENS", 1800))
        base_tokens = (
            history_tokens
            + self._estimate_tokens(user_prefix)
            + self._estimate_tokens(user_suffix)
        )
        context_budget = max(200, max_input_tokens - reserve_tokens - base_tokens)
        context_text, context_truncated = self._apply_context_budget(
            context.get("context_parts", []),
            context_budget,
        )
        if context_truncated:
            user_suffix += "\n\n（系統提醒：參考資料過長，已自動裁剪至模型可處理範圍。）"

        user_content = f"{user_prefix}{context_text}{user_suffix}"
        messages.append({"role": "user", "content": user_content})

        return messages

    # ──────────── 同步生成（相容原介面） ────────────

    async def _generate_answer(
        self,
        question: str,
        context: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """LLM 生成回答（非串流）。"""
        messages = self._build_llm_messages(question, context, history=history)
        return await self._llm_generate_async(
            messages=messages,
            temperature=getattr(settings, "LLM_TEMPERATURE", 0.3),
            max_tokens=getattr(settings, "LLM_MAX_TOKENS", 1500),
        )

    @staticmethod
    def _build_calc_guidance(question: str) -> str:
        today = date.today()
        today_str = f"{today.year}年{today.month}月{today.day}日"
        hints: List[str] = []
        if "特休" in question or "特別休假" in question:
            hints.append("特休天數依勞基法第38條，按『實際到職日』計算年資，而非問題敘述中的概算。")
            hints.append("年資區間：未滿6個月=0天，6個月以上未滿1年=3天，1年=7天，2年=10天，3年=14天，5年=15天，10年以上每年+1天(最多30天)。")
            hints.append(f"若問題含有具體到職日期，請計算到今天（{today_str}）的正確年資後再查對照表。")
        if "資遣費" in question:
            hints.append("資遣費公式：年資(年) × 0.5 × 月平均工資。不要把月薪除以30。")
            hints.append("年資若含月份，需換算為年並可四捨五入到 0.5 年再計算。")
        if "加班" in question:
            hints.append("時薪計算：時薪 = 月薪 / 30 / 8（勞基法基準）。")
            hints.append("平日加班費：前 2 小時每小時 × 1.34 倍，第 3 小時起每小時 × 1.67 倍。")
            hints.append("休息日加班費：前 2 小時每小時 × 1.34 倍，第 3-8 小時每小時 × 1.67 倍，第 9 小時起 × 2.67 倍。")
            hints.append("計算時必須分段計算，不可把全部時數都乘同一倍率。例如：平日加班 4 小時 = 前 2 小時 × 1.34 + 後 2 小時 × 1.67。")
        if "平均" in question and ("薪" in question or "月薪" in question):
            hints.append("平均值需使用所有符合條件的資料列，不要只取前幾筆。")
        if "占比" in question or "比例" in question:
            hints.append("統計題請逐一計數並核對總數後再計算比例。")
        if "年資最深" in question or ("最深" in question and "年資" in question):
            hints.append("最深年資需比對完整名冊後再下結論。")
        if "加班" in question and ("合法" in question or "合法嗎" in question):
            hints.append("若題目只給單一倍數（如 1.5 倍），視為前 2 小時標準；可判定合法，但提醒超過 2 小時需 1.67 倍。")
        if "勞保" in question:
            hints.append("若薪資條已列出勞保自付金額，直接引用該數值。")
        if "颱風" in question or "停班停課" in question:
            hints.append("颱風停班停課屬行政建議性質，雇主可視需要出勤，但不得不利處分；若出勤需依規定給付。")
        if "責任制" in question:
            hints.append("一般工程師通常不適用責任制，仍應依工時規定與加班費規定。")
        if "年終獎金" in question and "工資" in question:
            hints.append("年終獎金是否屬工資需視是否為經常性/固定性給付與契約約定，通常需個案判斷。")
        if "離職" in question and "資遣費" in question:
            hints.append("自請離職無資遣費；資遣費僅適用雇主依法資遣情況。")
        if "喪假" in question and "配偶" in question and "祖父母" in question:
            hints.append("配偶的祖父母喪假法定 3 天；如公司內規給更高天數可視為優於法令。")
        if not hints:
            return ""
        return "\n".join(f"- {h}" for h in hints)

    @staticmethod
    def _format_history_summary(history: Optional[List[Dict[str, str]]]) -> str:
        if not history:
            return ""
        kept = history[-2:]
        lines = []
        for msg in kept:
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if not content:
                continue
            lines.append(f"[{role}] {content[:200]}")
        return "\n".join(lines)

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
