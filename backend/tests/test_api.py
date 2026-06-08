"""API 接口测试"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from main import app


@pytest.fixture
def mock_db():
    from unittest.mock import MagicMock
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    session.__aenter__ = AsyncMock(return_value=session)
    return session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_spa_pages_return_html(client):
    for path in ["/", "/classify", "/pipeline", "/dashboard", "/history"]:
        resp = await client.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_classify_requires_fields(client):
    resp = await client.post("/api/classify", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_history_returns_list(client, mock_db):
    with patch("api.routes.history.async_session", return_value=mock_db):
        resp = await client.get("/api/history?limit=5")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_not_found(client):
    resp = await client.get("/api/nonexistent")
    assert resp.status_code == 404
