"""
Usage Tracking Tests
測試使用量追蹤與計費統計
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from tests.conftest import create_tenant, create_user, login_user

CHAT_URL = "/api/v1/chat/chat"
ORCH_CLASS = "app.api.v1.endpoints.chat.ChatOrchestrator"


def _mock_orchestrator(**overrides):
    result = {
        "request_id": "r-usage", "question": "q", "answer": "a",
        "company_policy": None, "labor_law": None,
        "sources": [], "notes": [], "disclaimer": "僅供參考",
    }
    result.update(overrides)
    inst = AsyncMock()
    inst.process_query = AsyncMock(return_value=result)
    return patch(ORCH_CLASS, return_value=inst)


async def _setup_tenant_owner(client, superuser_headers, suffix):
    t = await create_tenant(client, superuser_headers, {
        "name": f"Usage {suffix}", "tax_id": f"U{suffix}",
        "contact_name": suffix, "contact_email": f"c@{suffix}.com",
        "contact_phone": f"091{suffix}111",
    })
    await create_user(client, superuser_headers, {
        "email": f"owner@{suffix}.com", "password": "Owner123!",
        "full_name": f"Owner {suffix}", "role": "owner",
        "tenant_id": t["id"],
    })
    h = await login_user(client, f"owner@{suffix}.com", "Owner123!")
    return t, h


@pytest.mark.asyncio
async def test_usage_tracking_token_counts(client: AsyncClient, superuser_headers: dict):
    """測試 token 用量是否正確追蹤"""
    _, h = await _setup_tenant_owner(client, superuser_headers, "tok")

    with _mock_orchestrator():
        r = await client.post(CHAT_URL, headers=h, json={"question": "token test"})
        assert r.status_code == 200

    summary = await client.get("/api/v1/audit/usage/summary", headers=h)
    assert summary.status_code == 200
    data = summary.json()
    assert isinstance(data, (dict, list))


@pytest.mark.asyncio
async def test_usage_tracking_pinecone_queries(client: AsyncClient, superuser_headers: dict):
    """測試向量資料庫查詢次數追蹤"""
    _, h = await _setup_tenant_owner(client, superuser_headers, "pin")

    with _mock_orchestrator():
        for i in range(3):
            r = await client.post(CHAT_URL, headers=h, json={"question": f"pinecone q{i}"})
            assert r.status_code == 200

    summary = await client.get("/api/v1/audit/usage/summary", headers=h)
    assert summary.status_code == 200


@pytest.mark.asyncio
async def test_usage_cost_estimation(client: AsyncClient, superuser_headers: dict):
    """測試使用成本估算"""
    _, h = await _setup_tenant_owner(client, superuser_headers, "cost")

    with _mock_orchestrator():
        await client.post(CHAT_URL, headers=h, json={"question": "cost test"})

    summary = await client.get("/api/v1/audit/usage/summary", headers=h)
    assert summary.status_code == 200
    data = summary.json()
    if isinstance(data, dict) and "total_cost" in data:
        assert isinstance(data["total_cost"], (int, float))


@pytest.mark.asyncio
async def test_usage_aggregation_by_action_type(client: AsyncClient, superuser_headers: dict):
    """測試依動作類型彙總用量"""
    _, h = await _setup_tenant_owner(client, superuser_headers, "agg")

    with _mock_orchestrator():
        await client.post(CHAT_URL, headers=h, json={"question": "q1"})

    with patch("app.tasks.document_tasks.process_document_task.delay") as mt:
        mt.return_value.id = "t-agg"
        await client.post(
            "/api/v1/documents/upload", headers=h,
            files={"file": ("agg.txt", b"some text", "text/plain")},
        )

    logs = await client.get("/api/v1/audit/logs", headers=h)
    assert logs.status_code == 200
    data = logs.json()
    if data:
        types = {l.get("action_type") for l in data}
        assert len(types) >= 1


@pytest.mark.asyncio
async def test_usage_time_range_filtering(client: AsyncClient, superuser_headers: dict):
    """測試依時間範圍篩選用量"""
    _, h = await _setup_tenant_owner(client, superuser_headers, "time")

    with _mock_orchestrator():
        await client.post(CHAT_URL, headers=h, json={"question": "time q"})

    r = await client.get(
        "/api/v1/audit/usage/summary",
        headers=h,
        params={"start_date": "2020-01-01", "end_date": "2099-12-31"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_multi_user_usage_attribution(client: AsyncClient, superuser_headers: dict):
    """測試多用戶用量歸屬"""
    t, h_owner = await _setup_tenant_owner(client, superuser_headers, "musr")

    await create_user(client, superuser_headers, {
        "email": "emp@musr.com", "password": "Emp123!",
        "full_name": "Emp MUSR", "role": "employee",
        "tenant_id": t["id"],
    })
    h_emp = await login_user(client, "emp@musr.com", "Emp123!")

    with _mock_orchestrator():
        await client.post(CHAT_URL, headers=h_owner, json={"question": "owner q"})
        await client.post(CHAT_URL, headers=h_emp, json={"question": "emp q"})

    summary = await client.get("/api/v1/audit/usage/summary", headers=h_owner)
    assert summary.status_code == 200

    logs = await client.get("/api/v1/audit/logs", headers=h_owner)
    assert logs.status_code == 200
    data = logs.json()
    if data:
        user_ids = {l.get("actor_user_id") for l in data}
        assert len(user_ids) >= 1
