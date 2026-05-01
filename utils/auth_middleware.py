"""API key authentication middleware for aiohttp."""
import hashlib
import hmac
import os
from aiohttp import web

_PUBLIC_PATHS = frozenset({
    "/health",
    "/live",
    "/ready",
    "/openapi.yaml",
    "/docs",
    "/dashboard",
})

# Cache at import time; restart required to rotate key (intentional — avoids
# per-request env reads and removes the window where CWD race could change it).
_CONFIGURED_KEY: str = os.getenv("NSA_API_KEY", "")


def _digest(key: str) -> bytes:
    """SHA-256 digest of key so hmac.compare_digest operates on equal-length bytes."""
    return hashlib.sha256(key.encode()).digest()


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path in _PUBLIC_PATHS:
        return await handler(request)

    provided_key = request.headers.get("X-Api-Key", "")

    if not _CONFIGURED_KEY or not hmac.compare_digest(
        _digest(_CONFIGURED_KEY), _digest(provided_key)
    ):
        return web.Response(
            status=401,
            content_type="application/json",
            text='{"error": "Unauthorized"}',
        )

    return await handler(request)
