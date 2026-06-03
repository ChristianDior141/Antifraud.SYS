"""
Authentication endpoint tests.
Run: pytest tests/ -v --asyncio-mode=auto
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="session")
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "Test1234!",
        "full_name": "Test User",
        "role": "client",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "client"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "Test1234!", "full_name": "Dup"}
    await client.post("/api/v1/auth/register", json=payload)
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "password": "Test1234!", "full_name": "Login User"
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "Test1234!"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com", "password": "Test1234!", "full_name": "Wrong"
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com", "password": "BadPassword"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_me_authenticated(client):
    await client.post("/api/v1/auth/register", json={
        "email": "me@example.com", "password": "Test1234!", "full_name": "Me User"
    })
    login_r = await client.post("/api/v1/auth/login", json={
        "email": "me@example.com", "password": "Test1234!"
    })
    token = login_r.json()["access_token"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
