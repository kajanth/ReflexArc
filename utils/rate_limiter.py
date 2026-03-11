"""
Rate limiting middleware for NSA API Server.
Implements token bucket algorithm with per-endpoint limits.
"""

import asyncio
import time
from typing import Dict, Optional
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import structlog

logger = structlog.get_logger(__name__)


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens per second refill rate
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimiter:
    """Rate limiter with per-endpoint and per-client limits."""
    
    def __init__(self):
        self.endpoint_limits = {
            "/spike": {"capacity": 100, "refill_rate": 100/60},  # 100 req/min
            "/goal": {"capacity": 10, "refill_rate": 10/60},     # 10 req/min  
            "/skill/run": {"capacity": 20, "refill_rate": 20/60}, # 20 req/min
            "/spike/threat": {"capacity": 50, "refill_rate": 50/60}, # 50 req/min
            "/spike/metric": {"capacity": 200, "refill_rate": 200/60}, # 200 req/min
        }
        
        # Per-client buckets: {client_ip: {endpoint: TokenBucket}}
        self.client_buckets: Dict[str, Dict[str, TokenBucket]] = {}
        
        # Global endpoint buckets: {endpoint: TokenBucket}
        self.global_buckets: Dict[str, TokenBucket] = {}
        
        # Initialize global buckets
        for endpoint, config in self.endpoint_limits.items():
            self.global_buckets[endpoint] = TokenBucket(
                capacity=config["capacity"] * 10,  # 10x capacity for global limit
                refill_rate=config["refill_rate"] * 10
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
            
        # Fall back to remote address
        return request.remote or "unknown"
    
    def _get_endpoint_key(self, path: str) -> Optional[str]:
        """Get rate limit key for endpoint path."""
        # Exact matches first
        if path in self.endpoint_limits:
            return path
            
        # Pattern matches for parameterized endpoints
        if path.startswith("/goal/") and path.endswith("/evaluate"):
            return "/goal"
        if path.startswith("/goal/") and len(path.split("/")) == 3:
            return "/goal"  # DELETE /goal/{id}
            
        return None
    
    async def check_rate_limit(self, request: Request) -> Optional[Response]:
        """
        Check if request should be rate limited.
        
        Returns:
            None if request is allowed, Response if rate limited
        """
        client_ip = self._get_client_ip(request)
        endpoint_key = self._get_endpoint_key(request.path)
        
        if not endpoint_key:
            # No rate limit for this endpoint
            return None
            
        # Get or create client bucket
        if client_ip not in self.client_buckets:
            self.client_buckets[client_ip] = {}
            
        if endpoint_key not in self.client_buckets[client_ip]:
            config = self.endpoint_limits[endpoint_key]
            self.client_buckets[client_ip][endpoint_key] = TokenBucket(
                capacity=config["capacity"],
                refill_rate=config["refill_rate"]
            )
        
        client_bucket = self.client_buckets[client_ip][endpoint_key]
        global_bucket = self.global_buckets[endpoint_key]
        
        # Check both client and global limits
        client_allowed = await client_bucket.consume()
        global_allowed = await global_bucket.consume() if client_allowed else False
        
        if not client_allowed or not global_allowed:
            # Rate limited
            retry_after = int(60 / self.endpoint_limits[endpoint_key]["refill_rate"])
            
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                endpoint=endpoint_key,
                retry_after=retry_after
            )
            
            return web.json_response(
                {
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests to {endpoint_key}",
                    "retry_after": retry_after
                },
                status=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.endpoint_limits[endpoint_key]["capacity"]),
                    "X-RateLimit-Remaining": str(int(client_bucket.tokens)),
                    "X-RateLimit-Reset": str(int(time.time() + retry_after))
                }
            )
        
        return None


# Global rate limiter instance
rate_limiter = RateLimiter()


@web.middleware
async def rate_limit_middleware(request: Request, handler):
    """Rate limiting middleware for aiohttp."""
    # Check rate limit
    rate_limit_response = await rate_limiter.check_rate_limit(request)
    if rate_limit_response:
        return rate_limit_response
    
    # Process request normally
    response = await handler(request)
    
    # Add rate limit headers to successful responses
    endpoint_key = rate_limiter._get_endpoint_key(request.path)
    if endpoint_key:
        client_ip = rate_limiter._get_client_ip(request)
        if (client_ip in rate_limiter.client_buckets and 
            endpoint_key in rate_limiter.client_buckets[client_ip]):
            
            bucket = rate_limiter.client_buckets[client_ip][endpoint_key]
            config = rate_limiter.endpoint_limits[endpoint_key]
            
            response.headers["X-RateLimit-Limit"] = str(config["capacity"])
            response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
    
    return response