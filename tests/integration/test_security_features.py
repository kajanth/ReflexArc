"""
Integration tests for security and reliability features.
Tests rate limiting, input validation, health checks, and secrets management.
"""

import asyncio
import pytest
import json
import time
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from unittest import mock as unittest_mock

from api_server import NSAApiServer
from utils.rate_limiter import RateLimiter
from utils.secrets_manager import SecretsManager
from utils.health_checker import HealthChecker, HealthStatus


_TEST_API_KEY = "integration-test-key-abc123"


class TestSecurityFeatures(AioHTTPTestCase):
    """Test security and reliability features."""

    def setUp(self):
        import os
        os.environ["NSA_API_KEY"] = _TEST_API_KEY
        super().setUp()

    def tearDown(self):
        import os
        os.environ.pop("NSA_API_KEY", None)
        super().tearDown()

    async def get_application(self):
        """Create test application with security middleware."""
        mock_brain = unittest_mock.MagicMock()
        mock_sensor_mgr = unittest_mock.MagicMock()
        api_server = NSAApiServer(
            brain=mock_brain,
            host="127.0.0.1",
            port=8080,
            sensor_mgr=mock_sensor_mgr,
        )
        return api_server.app

    def _auth_headers(self, extra=None):
        h = {"X-Api-Key": _TEST_API_KEY}
        if extra:
            h.update(extra)
        return h

    async def test_rate_limiting(self):
        """Test rate limiting middleware."""
        spike_data = {
            "description": "Test spike",
            "sense_type": "api",
            "priority": "normal",
        }

        responses = []
        for i in range(5):
            resp = await self.client.request(
                "POST",
                "/spike",
                json=spike_data,
                headers=self._auth_headers({"Content-Type": "application/json"}),
            )
            responses.append(resp.status)

        assert 200 in responses or 500 in responses  # 500 is OK for mock brain

        resp = await self.client.request(
            "POST",
            "/spike",
            json=spike_data,
            headers=self._auth_headers({"Content-Type": "application/json"}),
        )
        assert "X-RateLimit-Limit" in resp.headers or resp.status == 429

    async def test_content_type_validation(self):
        """Test content-type validation middleware."""
        resp = await self.client.request(
            "POST",
            "/spike",
            data="invalid data",
            headers=self._auth_headers({"Content-Type": "text/plain"}),
        )
        assert resp.status == 415
        data = await resp.json()
        assert "Invalid Content-Type" in data["error"]

    async def test_cors_headers(self):
        """Test CORS headers are properly set (public endpoint, no auth needed)."""
        resp = await self.client.request("GET", "/health")
        assert "X-Content-Type-Options" in resp.headers
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in resp.headers
        assert resp.headers["X-Frame-Options"] == "DENY"

    async def test_input_validation(self):
        """Test input validation for API endpoints."""
        invalid_spike = {
            "description": "",
            "sense_type": "invalid@type",
            "priority": "invalid_priority",
        }
        resp = await self.client.request(
            "POST",
            "/spike",
            json=invalid_spike,
            headers=self._auth_headers({"Content-Type": "application/json"}),
        )
        assert resp.status == 422

        dangerous_goal = {
            "objective": "Test goal",
            "metric": "cpu_percent; rm -rf /",
            "operator": "<",
            "value": 80.0,
        }
        resp = await self.client.request(
            "POST",
            "/goal",
            json=dangerous_goal,
            headers=self._auth_headers({"Content-Type": "application/json"}),
        )
        assert resp.status == 422

    async def test_protected_route_requires_auth(self):
        """Protected routes must return 401 without X-Api-Key."""
        resp = await self.client.request("GET", "/stats")
        assert resp.status == 401

        resp = await self.client.request(
            "GET", "/stats", headers={"X-Api-Key": "wrong-key"}
        )
        assert resp.status == 401

        resp = await self.client.request(
            "GET", "/stats", headers={"X-Api-Key": _TEST_API_KEY}
        )
        assert resp.status != 401

    async def test_health_endpoints(self):
        """Test health check endpoints (public, no auth required)."""
        resp = await self.client.request("GET", "/health")
        assert resp.status in [200, 503]
        data = await resp.json()
        assert "status" in data
        assert "components" in data
        assert "uptime" in data

        resp = await self.client.request("GET", "/ready")
        assert resp.status in [200, 503]
        data = await resp.json()
        assert "ready" in data

        resp = await self.client.request("GET", "/live")
        assert resp.status in [200, 503]
        data = await resp.json()
        assert "alive" in data


class TestSecretsManager:
    """Test secrets management functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.secrets_manager = SecretsManager()
    
    def test_api_key_validation(self):
        """Test API key format validation."""
        import os
        original_env = os.environ.copy()

        try:
            os.environ["OPENAI_API_KEY"] = "sk-" + "a" * 48
            os.environ["NSA_API_KEY"] = "test-nsa-key-16chars"
            valid, errors = self.secrets_manager.validate_api_keys_on_startup()
            assert valid
            assert len(errors) == 0

            os.environ["OPENAI_API_KEY"] = "invalid-key"
            valid, errors = self.secrets_manager.validate_api_keys_on_startup()
            assert not valid
            assert len(errors) > 0

        finally:
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_encrypted_storage(self):
        """Test encrypted secret storage."""
        # Store a secret
        success = self.secrets_manager.store_encrypted_secret("test_key", "test_value")
        assert success
        
        # Retrieve the secret
        retrieved = self.secrets_manager.retrieve_encrypted_secret("test_key")
        assert retrieved == "test_value"
        
        # Test non-existent key
        missing = self.secrets_manager.retrieve_encrypted_secret("missing_key")
        assert missing is None
    
    def test_key_masking(self):
        """Test key masking for logging."""
        import os
        original_env = os.environ.copy()
        
        try:
            os.environ["OPENAI_API_KEY"] = "sk-1234567890abcdef"
            
            masked_info = self.secrets_manager.get_masked_key_info()
            assert "OPENAI_API_KEY" in masked_info
            
            masked_key = masked_info["OPENAI_API_KEY"]
            assert masked_key.startswith("sk-1")
            assert masked_key.endswith("cdef")
            assert "*" in masked_key
            
        finally:
            os.environ.clear()
            os.environ.update(original_env)


class TestHealthChecker:
    """Test health checking functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.health_checker = HealthChecker()
    
    async def test_liveness_check(self):
        """Test liveness probe."""
        result = await self.health_checker.check_liveness()
        
        assert "alive" in result
        assert "status" in result
        assert "uptime" in result
        assert "checks" in result
        
        # Should include basic system checks
        checks = result["checks"]
        assert "memory_ok" in checks
        assert "disk_ok" in checks
        assert "loop_responsive" in checks
    
    async def test_readiness_check(self):
        """Test readiness probe."""
        result = await self.health_checker.check_readiness()
        
        assert "ready" in result
        assert "status" in result
        assert "components" in result
        
        # Should check critical components
        components = result["components"]
        assert "database" in components
        assert "providers" in components
    
    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        # Create health checker with very short timeout
        health_checker = HealthChecker()
        health_checker.health_timeout = 0.001  # 1ms timeout
        
        result = await health_checker.check_full_health()
        
        # Should timeout and return unhealthy status
        assert result["status"] == HealthStatus.UNHEALTHY
        assert "timeout" in result["message"].lower()


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.rate_limiter = RateLimiter()
    
    async def test_token_bucket(self):
        """Test token bucket algorithm."""
        from utils.rate_limiter import TokenBucket
        
        # Create bucket with 2 tokens, 1 token/second refill
        bucket = TokenBucket(capacity=2, refill_rate=1.0)
        
        # Should be able to consume 2 tokens initially
        assert await bucket.consume(1) == True
        assert await bucket.consume(1) == True
        
        # Third token should fail
        assert await bucket.consume(1) == False
        
        # Wait for refill and try again
        await asyncio.sleep(1.1)
        assert await bucket.consume(1) == True
    
    def test_endpoint_key_mapping(self):
        """Test endpoint key mapping."""
        # Test exact matches
        assert self.rate_limiter._get_endpoint_key("/spike") == "/spike"
        assert self.rate_limiter._get_endpoint_key("/goal") == "/goal"
        
        # Test pattern matches
        assert self.rate_limiter._get_endpoint_key("/goal/123/evaluate") == "/goal"
        assert self.rate_limiter._get_endpoint_key("/goal/abc") == "/goal"
        
        # Test non-rate-limited endpoints
        assert self.rate_limiter._get_endpoint_key("/health") is None
        assert self.rate_limiter._get_endpoint_key("/status") is None



def test_ssrf_protection():
    """Test that SSRF protection correctly identifies safe and unsafe URLs."""
    from utils.ssrf_protection import is_safe_url

    # Test safe URLs
    assert is_safe_url("https://example.com") is True
    assert is_safe_url("http://google.com") is True

    # Test unsafe IP addresses
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("https://10.0.0.5") is False
    assert is_safe_url("http://192.168.1.100") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_url("http://0.0.0.0") is False

    # Test unsafe hostnames that resolve to local/internal IP
    assert is_safe_url("http://localhost") is False

    # Test invalid/malformed URLs
    assert is_safe_url("ftp://example.com") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("not_a_url") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
