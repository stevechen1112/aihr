from typing import Dict, Any, List, Optional
from uuid import UUID
import uuid
from app.services.kb_retrieval import KnowledgeBaseRetriever
from app.services.core_client import CoreAPIClient


class ChatOrchestrator:
    """
    聊天協調器
    負責協調公司內規檢索和勞資法 Core API 的查詢
    """
    
    def __init__(self):
        self.kb_retriever = KnowledgeBaseRetriever()
        self.core_client = CoreAPIClient()
    
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
        2. 合併結果
        3. 返回統一格式的回應
        
        Args:
            tenant_id: 租戶 ID
            question: 用戶問題
            top_k: 內規檢索返回數量
        
        Returns:
            統一格式的回應結果
        """
        request_id = str(uuid.uuid4())
        
        # 1. 並行查詢公司內規和勞資法
        import asyncio
        
        # 查詢公司內規（同步轉非同步）
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
        
        # 查詢勞資法
        async def get_labor_law():
            try:
                result = await self.core_client.chat(
                    question=question,
                    request_id=request_id
                )
                return result
            except Exception as e:
                return {"status": "error", "answer": "勞資法查詢失敗", "error": str(e)}
        
        # 並行執行
        company_policy_task = asyncio.create_task(get_company_policy())
        labor_law_task = asyncio.create_task(get_labor_law())
        
        company_policy_result, labor_law_result = await asyncio.gather(
            company_policy_task,
            labor_law_task
        )
        
        # 2. 合併結果
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
        合併公司內規和勞資法結果
        
        策略：
        - 內規命中 → 內規優先，法律補充
        - 僅法律命中 → 法律回答 + 提示公司可能有內規
        - 衝突 → 提示法律最低標準
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
        
        # 組裝公司內規部分
        if has_policy:
            policy_results = company_policy["results"]
            top_result = policy_results[0]
            
            result["company_policy"] = {
                "content": top_result["content"],
                "source": top_result["filename"],
                "relevance_score": top_result["score"]
            }
            
            result["sources"].append({
                "type": "company_policy",
                "filename": top_result["filename"],
                "score": top_result["score"]
            })
        
        # 組裝勞資法部分
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
        
        # 合併策略
        if has_policy and has_labor_law:
            # 兩者皆有：內規優先，法律補充
            result["answer"] = f"""
📋 **公司內規規定**：
{result["company_policy"]["content"][:500]}

⚖️ **勞動法規補充**：
{result["labor_law"]["answer"][:500]}

💡 **說明**：公司內規是您的優先參考依據，但不得違反勞動法的最低標準。
"""
            result["notes"].append("公司內規與勞動法規已為您整合")
        
        elif has_policy:
            # 僅有內規
            result["answer"] = f"""
📋 **公司內規規定**：
{result["company_policy"]["content"]}

💡 **提醒**：未查詢到相關勞動法規補充。如需了解法律最低標準，請進一步諮詢。
"""
            result["notes"].append("僅查詢到公司內規")
        
        elif has_labor_law:
            # 僅有勞資法
            result["answer"] = f"""
⚖️ **勞動法規**：
{result["labor_law"]["answer"]}

💡 **提醒**：未在公司內規中找到相關規定。建議確認公司是否有額外規定。
"""
            result["notes"].append("僅查詢到勞動法規，未找到公司內規")
        
        else:
            # 兩者皆無
            result["answer"] = "抱歉，未找到相關資訊。請嘗試換個方式提問，或聯繫 HR 部門。"
            result["notes"].append("未找到相關資訊")
        
        return result
    
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
