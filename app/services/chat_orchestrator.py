import logging
from typing import Dict, Any, List, Optional
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
    """
    
    def __init__(self):
        self.kb_retriever = KnowledgeBaseRetriever()
        self.core_client = CoreAPIClient()

        # OpenAI client
        self._openai = None
        openai_key = getattr(settings, "OPENAI_API_KEY", "")
        if _HAS_OPENAI and openai_key:
            self._openai = openai_lib.OpenAI(api_key=openai_key)
    
    async def process_query(
        self,
        tenant_id: UUID,
        question: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        處理用戶查詢
        
        工作流程：
        1. 並行查詢公司內規和勞資法 Core
        2. 使用 LLM 基於檢索結果生成回答
        3. 返回統一格式的回應
        """
        request_id = str(uuid.uuid4())
        
        import asyncio
        
        async def get_company_policy():
            try:
                results = self.kb_retriever.search(
                    tenant_id=tenant_id,
                    query=question,
                    top_k=top_k
                )
                return {"status": "success", "results": results}
            except Exception as e:
                return {"status": "error", "error": str(e), "results": []}
        
        async def get_labor_law():
            try:
                result = await self.core_client.chat(
                    question=question,
                    request_id=request_id
                )
                return result
            except Exception as e:
                return {"status": "error", "answer": "勞資法查詢失敗", "error": str(e)}
        
        company_policy_task = asyncio.create_task(get_company_policy())
        labor_law_task = asyncio.create_task(get_labor_law())
        
        company_policy_result, labor_law_result = await asyncio.gather(
            company_policy_task,
            labor_law_task
        )
        
        response = self._merge_results(
            question=question,
            company_policy=company_policy_result,
            labor_law=labor_law_result,
            request_id=request_id
        )
        
        return response
    
    def _merge_results(
        self,
        question: str,
        company_policy: Dict[str, Any],
        labor_law: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """
        合併公司內規和勞資法結果，使用 LLM 生成摘要回答。

        策略：
        - 若 LLM 可用 → 上下文感知的智慧回答
        - 若 LLM 不可用 → 結構化模板拼接（fallback）
        """
        has_policy = (
            company_policy.get("status") == "success" and
            len(company_policy.get("results", [])) > 0
        )
        
        has_labor_law = (
            labor_law.get("status") != "error" and
            labor_law.get("answer")
        )
        
        result = {
            "request_id": request_id,
            "question": question,
            "company_policy": None,
            "labor_law": None,
            "answer": "",
            "sources": [],
            "notes": [],
            "disclaimer": "本回答僅供參考，不構成正式法律意見。如有具體情況，請諮詢專業法律顧問。"
        }
        
        # ── 組裝 context（供 LLM 參考） ──
        context_parts: List[str] = []

        if has_policy:
            policy_results = company_policy["results"]
            # 取前 3 個最佳結果
            top_policies = policy_results[:3]
            
            result["company_policy"] = {
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
                result["sources"].append({
                    "type": "company_policy",
                    "filename": r["filename"],
                    "score": r["score"]
                })

            for i, r in enumerate(top_policies, 1):
                context_parts.append(
                    f"【公司內規 #{i}】（來源：{r['filename']}，相關度：{r['score']:.2f}）\n{r['content']}"
                )
        
        if has_labor_law:
            result["labor_law"] = {
                "answer": labor_law.get("answer", ""),
                "citations": labor_law.get("citations", []),
                "usage": labor_law.get("usage", {})
            }
            
            if labor_law.get("citations"):
                for citation in labor_law["citations"]:
                    result["sources"].append({
                        "type": "labor_law",
                        "law_name": citation.get("law_name"),
                        "article": citation.get("article")
                    })

            law_text = labor_law.get("answer", "")
            citations_text = ""
            if labor_law.get("citations"):
                citations_text = "；".join(
                    f"{c.get('law_name', '')} {c.get('article', '')}"
                    for c in labor_law["citations"]
                )
            context_parts.append(
                f"【勞動法規】{citations_text}\n{law_text}"
            )

        # ── LLM 生成回答 ──
        if self._openai and (has_policy or has_labor_law):
            try:
                result["answer"] = self._generate_answer(
                    question, context_parts, has_policy, has_labor_law
                )
                result["notes"].append("由 AI 根據檢索結果生成回答")
            except Exception as e:
                logger.warning(f"LLM 回答生成失敗，回退到模板: {e}")
                result["answer"] = self._fallback_answer(
                    has_policy, has_labor_law, result
                )
                result["notes"].append("LLM 暫時無法使用，以結構化格式呈現")
        else:
            result["answer"] = self._fallback_answer(
                has_policy, has_labor_law, result
            )
            if not (has_policy or has_labor_law):
                result["notes"].append("未找到相關資訊")
        
        return result

    def _generate_answer(
        self,
        question: str,
        context_parts: List[str],
        has_policy: bool,
        has_labor_law: bool,
    ) -> str:
        """
        使用 LLM 基於檢索到的上下文生成回答。

        Prompt 設計要點：
        - 只能根據提供的資料回答，不能捏造
        - 公司內規優先，法律做最低標準參照
        - 如有衝突要明確指出
        - 繁體中文回答
        """
        context_text = "\n\n".join(context_parts)

        system_prompt = """你是 UniHR 人資 AI 助理，專門回答台灣企業的人事規章與勞動法規問題。

回答規則：
1. **只根據下方提供的參考資料回答**，不要自行捏造或引用未提供的內容
2. 如果有公司內規，以公司內規為主，法律規定為輔助參照
3. 如果公司內規的規定**低於**勞動法的最低標準，必須明確指出
4. 使用結構化格式（標題、條列）讓回答清楚易讀
5. 引用資料時標註來源（檔名或法條名稱）
6. 如果參考資料不足以回答，坦白說明並建議諮詢 HR 部門
7. 使用繁體中文回答"""

        user_prompt = f"""問題：{question}

參考資料：
{context_text}

請根據上述參考資料回答問題。"""

        response = self._openai.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=getattr(settings, "OPENAI_TEMPERATURE", 0.3),
            max_tokens=getattr(settings, "OPENAI_MAX_TOKENS", 1500),
        )

        return response.choices[0].message.content.strip()

    @staticmethod
    def _fallback_answer(
        has_policy: bool,
        has_labor_law: bool,
        result: Dict[str, Any],
    ) -> str:
        """LLM 不可用時的模板 fallback。"""
        if has_policy and has_labor_law:
            return f"""📋 **公司內規規定**：
{result["company_policy"]["content"][:500]}

⚖️ **勞動法規補充**：
{result["labor_law"]["answer"][:500]}

💡 **說明**：公司內規是您的優先參考依據，但不得違反勞動法的最低標準。"""

        elif has_policy:
            return f"""📋 **公司內規規定**：
{result["company_policy"]["content"]}

💡 **提醒**：未查詢到相關勞動法規補充。如需了解法律最低標準，請進一步諮詢。"""

        elif has_labor_law:
            return f"""⚖️ **勞動法規**：
{result["labor_law"]["answer"]}

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
