"""
End-to-End Integration Tests: SaaS → Core API
測試完整的問答流程，包含 Core API 整合
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from tests.conftest import create_tenant, create_user, login_user

CHAT_URL = "/api/v1/chat/chat"
ORCH_CLASS = "app.api.v1.endpoints.chat.ChatOrchestrator"


def _mock_orchestrator(answer="Test answer", sources=None):
    """Return a context-manager patch that replaces ChatOrchestrator."""
    result = {
        "request_id": "test-req-id",
        "question": "q",
        "answer": answer,
        "company_policy": None,
        "labor_law": None,
        "sources": sources or [],
        "notes": [],
        "disclaimer": "本回答僅供參考，不構成法律意見。",
    }
    mock_instance = AsyncMock()
    mock_instance.process_query = AsyncMock(return_value=result)
    return patch(ORCH_CLASS, return_value=mock_instance)


@pytest.mark.asyncio
async def test_chat_with_core_integration(client: AsyncClient, superuser_headers: dict):
    """測試 SaaS → Core API 的端對端問答流程"""

    tenant_data = await create_tenant(client, superuser_headers, {
        "name": "Test Company", "tax_id": "12345678",
        "contact_name": "Test Manager", "contact_email": "manager@test.com",
        "contact_phone": "0912345678",
    })

    await create_user(client, superuser_headers, {
        "email": "owner@test.com", "password": "TestPass123!",
        "full_name": "Test Owner", "role": "owner",
        "tenant_id": tenant_data["id"],
    })

    headers = await login_user(client, "owner@test.com", "TestPass123!")

    answer = "根據勞基法第 43 條，勞工每 7 日中至少應有 1 日之休息，作為例假。"
    sources = [{"type": "labor_law", "law_name": "勞基法", "article": "43"}]

    with _mock_orchestrator(answer=answer, sources=sources):
        chat_response = await client.post(
            CHAT_URL, headers=headers,
            json={"question": "請問例假的規定是什麼？"},
        )

    assert chat_response.status_code == 200
    chat_data = chat_response.json()
    assert "conversation_id" in chat_data
    assert "message_id" in chat_data
    assert "勞基法" in chat_data["answer"]

    # 驗證對話記錄
    convs = await client.get("/api/v1/chat/conversations", headers=headers)
    assert convs.status_code == 200
    assert len(convs.json()) == 1
    assert convs.json()[0]["id"] == chat_data["conversation_id"]


@pytest.mark.asyncio
async def test_chat_with_company_documents(client: AsyncClient, superuser_headers: dict):
    """測試上傳公司文件後的混合檢索"""

    tenant_data = await create_tenant(client, superuser_headers, {
        "name": "Company With Docs", "tax_id": "11223344",
        "contact_name": "Doc Manager", "contact_email": "doc@company.com",
        "contact_phone": "0911223344",
    })

    await create_user(client, superuser_headers, {
        "email": "owner@doccompany.com", "password": "DocPass123!",
        "full_name": "Doc Owner", "role": "owner",
        "tenant_id": tenant_data["id"],
    })

    headers = await login_user(client, "owner@doccompany.com", "DocPass123!")

    with patch("app.tasks.document_tasks.process_document_task.delay") as mock_task:
        mock_task.return_value.id = "test-task-id"
        upload = await client.post(
            "/api/v1/documents/upload", headers=headers,
            files={"file": ("test.txt", b"Company sick leave policy.", "text/plain")},
        )
        assert upload.status_code == 200

    sources = [
        {"type": "company_policy", "filename": "test.txt", "score": 0.88},
        {"type": "labor_law", "law_name": "勞基法", "article": "病假"},
    ]
    with _mock_orchestrator(answer="回答", sources=sources):
        chat = await client.post(
            CHAT_URL, headers=headers,
            json={"question": "請問請病假要提前多久申請？"},
        )
        assert chat.status_code == 200
        assert len(chat.json()["sources"]) >= 1


@pytest.mark.asyncio
async def test_usage_tracking_in_chat(client: AsyncClient, superuser_headers: dict):
    """測試用量記錄在聊天過程中的正確性"""

    tenant_data = await create_tenant(client, superuser_headers, {
        "name": "Usage Test Company", "tax_id": "99887766",
        "contact_name": "Usage Manager", "contact_email": "usage@test.com",
        "contact_phone": "0999887766",
    })

    await create_user(client, superuser_headers, {
        "email": "owner@usage.com", "password": "UsagePass123!",
        "full_name": "Usage Owner", "role": "owner",
        "tenant_id": tenant_data["id"],
    })

    headers = await login_user(client, "owner@usage.com", "UsagePass123!")

    with _mock_orchestrator():
        await client.post(CHAT_URL, headers=headers, json={"question": "Test query"})

    usage = await client.get(
        "/api/v1/audit/usage/records", headers=headers,
        params={"action_type": "chat"},
    )
    assert usage.status_code == 200
    records = usage.json()
    assert len(records) > 0
    assert records[0]["action_type"] == "chat"
    assert "pinecone_queries" in records[0]

    summary = await client.get("/api/v1/audit/usage/summary", headers=headers)
    assert summary.status_code == 200
    s = summary.json()
    assert s["total_actions"] >= 1
    assert "total_input_tokens" in s
    assert "total_output_tokens" in s
    assert "total_pinecone_queries" in s
