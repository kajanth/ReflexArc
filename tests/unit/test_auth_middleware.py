"""Unit tests for API key authentication middleware."""
import pytest
from aiohttp import web


@pytest.fixture
def api_key():
    return "test-secret-key-abc123"


@pytest.fixture(autouse=True)
def set_env(api_key, monkeypatch):
    monkeypatch.setenv("NSA_API_KEY", api_key)


async def _ok_handler(request):
    return web.Response(text="ok")


def _make_app_with_auth():
    from utils.auth_middleware import auth_middleware
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/protected", _ok_handler)
    app.router.add_get("/health", _ok_handler)
    app.router.add_get("/live", _ok_handler)
    app.router.add_get("/ready", _ok_handler)
    app.router.add_get("/openapi.yaml", _ok_handler)
    app.router.add_get("/docs", _ok_handler)
    app.router.add_get("/dashboard", _ok_handler)
    return app


@pytest.mark.asyncio
async def test_missing_key_returns_401(aiohttp_client, api_key):
    client = await aiohttp_client(_make_app_with_auth())
    resp = await client.get("/protected")
    assert resp.status == 401


@pytest.mark.asyncio
async def test_wrong_key_returns_401(aiohttp_client, api_key):
    client = await aiohttp_client(_make_app_with_auth())
    resp = await client.get("/protected", headers={"X-Api-Key": "wrong"})
    assert resp.status == 401


@pytest.mark.asyncio
async def test_correct_key_returns_200(aiohttp_client, api_key):
    client = await aiohttp_client(_make_app_with_auth())
    resp = await client.get("/protected", headers={"X-Api-Key": api_key})
    assert resp.status == 200


@pytest.mark.asyncio
async def test_public_routes_skip_auth(aiohttp_client):
    client = await aiohttp_client(_make_app_with_auth())
    for path in ["/health", "/live", "/ready", "/openapi.yaml", "/docs", "/dashboard"]:
        resp = await client.get(path)
        assert resp.status == 200, f"{path} should be public but got {resp.status}"


@pytest.mark.asyncio
async def test_no_env_key_blocks_all(aiohttp_client, monkeypatch):
    monkeypatch.delenv("NSA_API_KEY", raising=False)
    client = await aiohttp_client(_make_app_with_auth())
    resp = await client.get("/protected")
    assert resp.status == 401


@pytest.mark.asyncio
async def test_timing_safe_comparison(aiohttp_client, api_key):
    client = await aiohttp_client(_make_app_with_auth())
    resp = await client.get("/protected", headers={"X-Api-Key": api_key + " "})
    assert resp.status == 401


def test_startup_validation_fails_without_api_key(monkeypatch):
    monkeypatch.delenv("NSA_API_KEY", raising=False)
    from utils.secrets_manager import SecretsManager
    sm = SecretsManager()
    valid, errors = sm.validate_api_keys_on_startup()
    assert not valid
    assert any("NSA_API_KEY" in e for e in errors)


def test_startup_validation_passes_with_api_key(monkeypatch):
    monkeypatch.setenv("NSA_API_KEY", "test-key-abc-def-123")
    from utils.secrets_manager import SecretsManager
    sm = SecretsManager()
    _, errors = sm.validate_api_keys_on_startup()
    nsa_errors = [e for e in errors if "NSA_API_KEY" in e]
    assert not nsa_errors
