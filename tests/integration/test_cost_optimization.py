"""
Integration tests for cost optimization using mock providers.

Tests Protocol Alpha (Conservation of Token Energy) - the system's core
principle of never using expensive models for cheap problems.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from tests.mocks.mock_provider import MockProvider
from providers.router import ModelRouter


class TestCostOptimization:
    """Test cost optimization with mock providers."""
    
    @pytest.fixture
    def cost_optimized_providers(self):
        """Create providers with different cost tiers."""
        return {
            "nano_provider": MockProvider(
                name="nano",
                cost_per_token=0.0001,
                base_latency_ms=10.0
            ),
            "mini_provider": MockProvider(
                name="mini", 
                cost_per_token=0.001,
                base_latency_ms=50.0
            ),
            "cortex_provider": MockProvider(
                name="cortex",
                cost_per_token=0.01,
                base_latency_ms=200.0
            )
        }
    
    @pytest.fixture
    def router_with_cost_providers(self, cost_optimized_providers):
        """Create router with cost-optimized providers."""
        router = ModelRouter()
        router.providers = cost_optimized_providers
        return router
    
    async def test_protocol_alpha_tier_routing(self, router_with_cost_providers):
        """Test Protocol Alpha: REFLEX > TEMPLATE > COMPLEX routing preference."""
        router = router_with_cost_providers
        
        # Test nano tier (cheapest) - should be preferred for simple tasks
        response = await router.route("Simple reflex task", tier="nano")
        assert response.cost < 0.01  # Should be very cheap
        
        # Test cortex tier (most expensive) - only for complex reasoning
        response = await router.route("Complex reasoning task requiring deep analysis", tier="cortex")
        assert response.cost > 0.001  # Should be more expensive
        
        # Verify cost difference
        nano_provider = router.providers["nano_provider"]
        cortex_provider = router.providers["cortex_provider"]
        
        assert nano_provider.total_cost < cortex_provider.total_cost
    
    async def test_cost_accumulation_tracking(self, cost_optimized_providers):
        """Test that costs accumulate correctly for budget monitoring."""
        provider = cost_optimized_providers["mini_provider"]
        
        # Make multiple calls
        for i in range(5):
            await provider.generate_response(f"Test prompt {i}", max_tokens=50)
        
        stats = provider.get_stats()
        
        # Verify cost tracking
        assert stats["call_count"] == 5
        assert stats["total_cost"] > 0
        assert stats["total_tokens"] > 0
        assert stats["avg_cost_per_call"] > 0
        assert stats["avg_tokens_per_call"] > 0
    
    async def test_cost_optimization_under_load(self, router_with_cost_providers):
        """Test cost optimization under concurrent load."""
        router = router_with_cost_providers
        
        # Create mixed workload - some simple, some complex
        simple_tasks = [
            router.route(f"Simple task {i}", tier="nano")
            for i in range(10)
        ]
        
        complex_tasks = [
            router.route(f"Complex analysis task {i}", tier="cortex")
            for i in range(2)
        ]
        
        # Execute all tasks concurrently
        all_tasks = simple_tasks + complex_tasks
        responses = await asyncio.gather(*all_tasks)
        
        # Verify cost distribution
        simple_responses = responses[:10]
        complex_responses = responses[10:]
        
        # Simple tasks should be much cheaper
        simple_total_cost = sum(r.cost for r in simple_responses)
        complex_total_cost = sum(r.cost for r in complex_responses)
        
        # Even with 5x more simple tasks, they should cost less than complex tasks
        assert simple_total_cost < complex_total_cost
    
    async def test_budget_constraint_simulation(self, cost_optimized_providers):
        """Test budget constraint handling."""
        provider = cost_optimized_providers["cortex_provider"]  # Most expensive
        
        # Simulate budget limit
        budget_limit = 0.10  # $0.10 limit
        current_spend = 0.0
        
        calls_made = 0
        while current_spend < budget_limit:
            response = await provider.generate_response(
                "Expensive reasoning task", 
                max_tokens=100
            )
            current_spend += response.cost
            calls_made += 1
            
            # Safety break to avoid infinite loop
            if calls_made > 20:
                break
        
        # Verify we stayed within budget
        assert provider.total_cost <= budget_limit * 1.1  # Allow 10% tolerance
        assert calls_made > 0  # Should have made at least some calls
    
    async def test_latency_vs_cost_tradeoff(self, cost_optimized_providers):
        """Test latency vs cost tradeoffs."""
        nano = cost_optimized_providers["nano_provider"]
        cortex = cost_optimized_providers["cortex_provider"]
        
        # Configure different latencies
        nano.set_latency(10.0, 5.0)    # Fast, cheap
        cortex.set_latency(200.0, 50.0)  # Slow, expensive
        
        # Test same prompt on both
        prompt = "Analyze system performance"
        
        nano_response = await nano.generate_response(prompt)
        cortex_response = await cortex.generate_response(prompt)
        
        # Nano should be faster and cheaper
        assert nano_response.latency_ms < cortex_response.latency_ms
        assert nano_response.cost < cortex_response.cost
    
    async def test_cost_optimization_with_failures(self, cost_optimized_providers):
        """Test cost optimization when providers fail."""
        # Configure one provider to fail
        failing_provider = cost_optimized_providers["nano_provider"]
        failing_provider.set_failure_rate(1.0)  # Always fail
        
        working_provider = cost_optimized_providers["mini_provider"]
        
        router = ModelRouter()
        router.providers = {
            "failing": failing_provider,
            "working": working_provider
        }
        
        # Should fallback to working provider despite higher cost
        response = await router.route("Test prompt", tier="nano")
        
        # Verify fallback occurred
        assert response is not None
        assert working_provider.call_count > 0
        assert failing_provider.failure_count > 0
    
    async def test_protocol_alpha_decision_matrix(self, router_with_cost_providers):
        """Test Protocol Alpha decision matrix: REFLEX > TEMPLATE > LOG > COMPLEX."""
        router = router_with_cost_providers
        
        # Test different prompt types that should route to different tiers
        test_cases = [
            ("reflex task", "nano", "Should route to cheapest for reflexes"),
            ("template generation", "mini", "Should use mid-tier for templates"),
            ("complex reasoning and analysis", "cortex", "Should use expensive tier for complex tasks")
        ]
        
        results = []
        for prompt, expected_tier, description in test_cases:
            response = await router.route(prompt, tier=expected_tier)
            results.append({
                "prompt": prompt,
                "tier": expected_tier,
                "cost": response.cost,
                "latency": response.latency_ms,
                "description": description
            })
        
        # Verify cost hierarchy: nano < mini < cortex
        nano_cost = next(r["cost"] for r in results if r["tier"] == "nano")
        mini_cost = next(r["cost"] for r in results if r["tier"] == "mini")
        cortex_cost = next(r["cost"] for r in results if r["tier"] == "cortex")
        
        assert nano_cost < mini_cost < cortex_cost
    
    async def test_cost_per_spike_optimization(self, cost_optimized_providers):
        """Test cost optimization per spike processing."""
        # Simulate different types of spikes with appropriate routing
        spike_scenarios = [
            {
                "type": "system_vitals",
                "description": "CPU usage at 85%",
                "expected_tier": "nano",  # Simple metric, should use cheapest
                "provider": cost_optimized_providers["nano_provider"]
            },
            {
                "type": "security_threat", 
                "description": "Suspicious process detected with complex behavior patterns",
                "expected_tier": "cortex",  # Complex analysis needed
                "provider": cost_optimized_providers["cortex_provider"]
            },
            {
                "type": "webhook",
                "description": "GitHub push event received",
                "expected_tier": "mini",  # Template processing
                "provider": cost_optimized_providers["mini_provider"]
            }
        ]
        
        total_cost = 0.0
        for scenario in spike_scenarios:
            response = await scenario["provider"].generate_response(
                scenario["description"],
                max_tokens=50
            )
            total_cost += response.cost
            
            # Verify appropriate cost for spike type
            if scenario["expected_tier"] == "nano":
                assert response.cost < 0.001
            elif scenario["expected_tier"] == "mini":
                assert 0.001 <= response.cost < 0.01
            elif scenario["expected_tier"] == "cortex":
                assert response.cost >= 0.01
        
        # Total cost should be reasonable for mixed workload
        assert total_cost < 0.05  # Should stay under $0.05 for this test
    
    async def test_daily_budget_simulation(self, cost_optimized_providers):
        """Test daily budget simulation for $0.50/day target."""
        daily_budget = 0.50
        
        # Simulate realistic daily workload
        workload = [
            ("nano_provider", 100),    # 100 simple operations
            ("mini_provider", 20),     # 20 template operations  
            ("cortex_provider", 5)     # 5 complex operations
        ]
        
        total_daily_cost = 0.0
        
        for provider_name, operation_count in workload:
            provider = cost_optimized_providers[provider_name]
            
            for i in range(operation_count):
                response = await provider.generate_response(
                    f"Daily operation {i}",
                    max_tokens=30  # Typical small response
                )
                total_daily_cost += response.cost
        
        # Verify we stay within daily budget
        assert total_daily_cost <= daily_budget
        
        # Log cost breakdown for analysis
        cost_breakdown = {
            name: provider.total_cost 
            for name, provider in cost_optimized_providers.items()
        }
        
        print(f"Daily cost simulation: ${total_daily_cost:.4f}")
        print(f"Cost breakdown: {cost_breakdown}")
        
        # Verify cost distribution follows Protocol Alpha
        assert cost_breakdown["nano_provider"] < cost_breakdown["cortex_provider"]