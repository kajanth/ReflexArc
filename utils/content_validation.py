"""
Content-Type validation middleware for NSA API Server.
Ensures only valid content types are accepted for POST requests.
"""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import structlog

logger = structlog.get_logger(__name__)


@web.middleware
async def content_type_middleware(request: Request, handler):
    """
    Validate Content-Type header for POST requests.
    
    Only allows application/json for POST requests to prevent
    various injection attacks and ensure proper parsing.
    
    Endpoints listed in BODYLESS_POST_PATHS are exempt — they
    accept POST with no body (e.g. trigger endpoints).
    """
    # Endpoints that legitimately accept POST with no body
    BODYLESS_POST_PATHS = {
        "/dream/trigger",
        "/heart/pulse",
        "/sensors/refresh",
        "/memory/defrag",
    }

    # Only validate POST requests that are NOT body-exempt
    if request.method == "POST" and request.path not in BODYLESS_POST_PATHS:
        content_type = request.headers.get('Content-Type', '').lower()
        
        # Remove charset and other parameters
        content_type = content_type.split(';')[0].strip()
        
        # Allow only application/json for POST requests
        if content_type != 'application/json':
            logger.warning(
                "Invalid content type for POST request",
                content_type=content_type,
                path=request.path,
                client_ip=request.remote
            )
            
            return web.json_response(
                {
                    "error": "Invalid Content-Type",
                    "message": "POST requests must use Content-Type: application/json",
                    "received": content_type or "missing"
                },
                status=415  # Unsupported Media Type
            )
    
    # Process request normally
    return await handler(request)



@web.middleware 
async def cors_middleware(request: Request, handler):
    """
    CORS middleware for web dashboard access.
    
    Allows cross-origin requests from trusted origins only.
    """
    # Handle preflight requests
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)
    
    # Get origin from request
    origin = request.headers.get('Origin')
    
    # Define allowed origins (customize based on deployment)
    allowed_origins = [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'https://localhost:8080',
        'https://127.0.0.1:8080',
    ]
    
    # Add environment-specific origins
    import os
    custom_origins = os.getenv('NSA_ALLOWED_ORIGINS', '').split(',')
    allowed_origins.extend([origin.strip() for origin in custom_origins if origin.strip()])
    
    # Set CORS headers for allowed origins
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        # Default to same-origin for dashboard
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Host', 'localhost:8080')
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response