"""
Integration tests for provider routing and circuit breaker functionality.

Tests the interaction between ModelRouter, providers, and circuit breakers
using mock providers to avoid API costs.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from typing import List

from providers.router import ModelRouter
from providers.base import ModelInfo, StandardResponse
from providers.circuit_breaker import CircuitBreakerProvider
from tests.mocks.mock_provider import MockProvider


class TestProviderIntegration:
    """Test provider integration with routing and circuit breakers."""
    
    @pytest.fixture
    async def mock_providers(self):
        """Create mock providers for testing."""
        providers = {
            "mock_openai": MockProvider("mock_openai", {
                "test prompt": "OpenAI mock response"
            }),
            "mock_anthropic": MockProvider("mock_anthropic", {
                "test prompt": "Anthropic mock response"
            }),
            "mock_gemini": MockProvider("mock_gemini", {
                "test prompt": "Gemini mock response"
            })
        }
        return providers
    
    @pytest.fixture
    async def router_with_mocks(self, mock_providers):
        """Create router with mock providers."""
        router = ModelRouter()
        
        # Replace providers with mocks
        for name, provider in mock_providers.items():
            router.providers[name] = provider
            
        return router
    
    async def test_provider_routing_by_tier(self, router_with_mocks):
        """Test that router selects appropriate provider by tier."""
        router = router_with_mocks
        
        # Test nano tier routing
        response = await router.route("test prompt", tier="nano")
        assert response.content is not None
        assert response.cost == 0.0  # Mock provider cost
        
        # Test mini tier routing
        response = await router.route("test prompt", tier="mini")
        assert response.content is not None
        
        # Test cortex tier routing
        response = await router.route("test prompt", tier="cortex")
        assert response.content is not None
    
    async def test_provider_fallback_on_failure(self, mock_providers):
        """Test provider fallback when primary provider fails."""
        # Create a failing provider
        failing_provider = MockProvider("failing")
        failing_provider.generate_response = AsyncMock(
            side_effect=Exception("Provider unavailable")
        )
        
        # Create router with failing primary and working fallback
        router = ModelRouter()
        router.providers = {
            "primary": failing_provider,
            "fallback": mock_providers["mock_openai"]
        }
        
        # Should fallback to working provider
        response = await router.route("test prompt", tier="nano")
        assert response.content is not None
        assert "mock response" in response.content.lower()
    
    async def test_circuit_breaker_integration(self, mock_providers):
        """Test circuit breaker behavior with providers."""
        # Create provider that fails consistently
        failing_provider = MockProvider("failing")
        failing_provider.generate_response = AsyncMock(
            side_effect=Exception("Consistent failure")
        )
        
        # Wrap with circuit breaker
        cb_provider = CircuitBreakerProvider(
            failing_provider,
            failure_threshold=2,
            recovery_timeout=1
        )
        
        # First few calls should fail and open circuit
        with pytest.raises(Exception):
            await cb_provider.generate_response("test")
            
        with pytest.raises(Exception):
            await cb_provider.generate_response("test")
        
        # Circuit should now be open
        assert cb_provider.circuit_breaker.current_state == "open"
        
        # Subsequent calls should fail fast
        with pytest.raises(Exception):
            await cb_provider.generate_response("test")
    
    async def test_parallel_provider_calls(self, mock_providers):
        """Test parallel execution of multiple provider calls."""
        router = ModelRouter()
        router.providers = mock_providers
        
        # Create multiple concurrent requests
        tasks = [
            router.route(f"prompt {i}", tier="nano")
            for i in range(5)
        ]
        
        # Execute in parallel
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(responses) == 5
        for response in responses:
            assert response.content is not None
            assert response.latency_ms >= 0
    
    async def test_provider_cost_tracking(self, mock_providers):
        """Test that provider costs are properly tracked."""
        router = ModelRouter()
        router.providers = mock_providers
        
        # Make several requests
        total_cost = 0
        for i in range(3):
            response = await router.route(f"prompt {i}", tier="nano")
            total_cost += response.cost
        
        # Mock providers should have zero cost
        assert total_cost == 0.0
        
        # Check that usage is tracked
        for provider in mock_providers.values():
            assert provider.call_count > 0
    
    async def test_provider_model_discovery(self, mock_providers):
        """Test provider model discovery and caching."""
        provider = mock_providers["mock_openai"]
        
        # Get available models
        models = await provider.get_available_models()
        
        # Should return mock models
        assert len(models) == 3
        assert any(m.name == "mock-nano" for m in models)
        assert any(m.name == "mock-mini" for m in models)
        assert any(m.name == "mock-cortex" for m in models)
        
        # Check tier assignments
        nano_model = next(m for m in models if m.name == "mock-nano")
        assert nano_model.tier == "nano"
        assert nano_model.cost_per_token == 0.0001
    
    async def test_provider_timeout_handling(self, mock_providers):
        """Test provider timeout handling."""
        # Create slow provider
        slow_provider = MockProvider("slow")
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow response
            return StandardResponse(
                content="Slow response",
                model="mock-nano",
                usage_tokens=10,
                cost=0.0,
                latency_ms=2000
            )
        
        slow_provider.generate_response = slow_response
        
        router = ModelRouter()
        router.providers = {"slow": slow_provider}
        
        # Should timeout and raise exception
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                router.route("test prompt", tier="nano"),
                timeout=1.0
            )
    
    async def test_provider_error_isolation(self, mock_providers):
        """Test that provider errors don't affect other providers."""
        # Create mixed providers - some working, some failing
        failing_provider = MockProvider("failing")
        failing_provider.generate_response = AsyncMock(
            side_effect=Exception("Provider error")
        )
        
        router = ModelRouter()
        router.providers = {
            "working": mock_providers["mock_openai"],
            "failing": failing_provider
        }
        
        # Working provider should still work despite failing provider
        response = await router.route("test prompt", tier="nano")
        assert response.content is not None
        
        # Failing provider should be isolated
        assert mock_providers["mock_openai"].call_count > 0
        assert failing_provider.call_count == 0  # Should not be called due to error