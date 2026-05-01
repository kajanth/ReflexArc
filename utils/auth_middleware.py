"""API key authentication middleware for aiohttp."""
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


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path in _PUBLIC_PATHS:
        return await handler(request)

    configured_key = os.getenv("NSA_API_KEY", "")
    provided_key = request.headers.get("X-Api-Key", "")

    if not configured_key or not hmac.compare_digest(
        configured_key.encode(), provided_key.encode()
    ):
        return web.Response(
            status=401,
            content_type="application/json",
            text='{"error": "Unauthorized"}',
        )

    return await handler(request)
