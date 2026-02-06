"""Pytest configuration and fixtures for integration tests."""
import asyncio
import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.db.base_class import Base

# --- Constants ---
SUPERUSER_EMAIL = "superuser@test.com"
SUPERUSER_PASSWORD = "Super123!"

# --- DB URL ---

def _build_test_db_url() -> str:
    """Build a test DB URL."""
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        return env_url

    db_name = settings.POSTGRES_DB
    if not db_name.endswith("_test"):
        db_name = f"{db_name}_test"

    host = os.getenv("POSTGRES_SERVER_TEST", settings.POSTGRES_SERVER)
    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{host}/{db_name}"
    )


# --- Session-level fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a SQLAlchemy engine for the test database (session scope)."""
    engine = create_engine(_build_test_db_url())
    yield engine
    engine.dispose()


# --- Per-test fixtures ---

@pytest.fixture(scope="function")
async def client(test_engine):
    """
    Create async HTTP client with proper DB dependency override.
    Each test gets:
      - Fresh tables (create_all / drop_all)
      - get_db overridden to use the test database
      - A pre-seeded superuser for admin operations
    """
    from app.main import app as fastapi_app
    from app.api.deps import get_db
    from app.core.security import get_password_hash
    # Import all models so Base.metadata knows every table
    import app.models  # noqa: F401

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Override get_db
    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    # Seed a platform tenant + superuser
    db = TestSession()
    try:
        from app.models.tenant import Tenant
        from app.models.user import User

        platform_tenant = Tenant(
            id=uuid.uuid4(),
            name="Platform",
            plan="enterprise",
            status="active",
        )
        db.add(platform_tenant)
        db.flush()

        superuser = User(
            id=uuid.uuid4(),
            email=SUPERUSER_EMAIL,
            hashed_password=get_password_hash(SUPERUSER_PASSWORD),
            full_name="System Admin",
            role="admin",
            is_superuser=True,
            status="active",
            tenant_id=platform_tenant.id,
        )
        db.add(superuser)
        db.commit()
    finally:
        db.close()

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Teardown
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
async def superuser_headers(client: AsyncClient):
    """Get Authorization headers for the pre-seeded superuser."""
    login = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
    )
    assert login.status_code == 200, f"Superuser login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Helpers ---

async def create_tenant(client: AsyncClient, headers: dict, data: dict) -> dict:
    """Helper: create a tenant via API and return its JSON."""
    resp = await client.post("/api/v1/tenants/", json=data, headers=headers)
    assert resp.status_code == 200, f"Create tenant failed: {resp.text}"
    return resp.json()


async def create_user(client: AsyncClient, headers: dict, data: dict) -> dict:
    """Helper: create a user via API and return its JSON."""
    resp = await client.post("/api/v1/users/", json=data, headers=headers)
    assert resp.status_code == 200, f"Create user failed: {resp.text}"
    return resp.json()


async def login_user(client: AsyncClient, email: str, password: str) -> dict:
    """Helper: login and return auth headers."""
    resp = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
