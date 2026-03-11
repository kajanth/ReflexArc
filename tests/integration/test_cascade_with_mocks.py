"""
Integration tests for neural cascade with mock providers.

Tests the complete spike processing pipeline using mock providers
to verify Protocol Alpha cost optimization without API costs.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock

from tests.mocks.mock_provider import MockProvider
from providers.router import ModelRouter


class MockNSAOrchestrator:
    """Simplified mock NSA brain for cascade testing."""
    
    def __init__(self):
        # Create mock providers with different cost tiers
        self.providers = {
            "nano": MockProvider(
                name="nano",
                cost_per_token=0.0001,
                base_latency_ms=10.0,
                responses={
                    "reflex": "REFLEX_RESPONSE",
                    "simple task": "REFLEX_RESPONSE"
                }
            ),
            "mini": MockProvider(
                name="mini", 
                cost_per_token=0.001,
                base_latency_ms=50.0,
                responses={
                    "template": "TEMPLATE_RESPONSE",
                    "moderate task": "TEMPLATE_RESPONSE"
                }
            ),
            "cortex": MockProvider(
                name="cortex",
                cost_per_token=0.01,
                base_latency_ms=200.0,
                responses={
                    "complex": "CORTEX_RESPONSE",
                    "complex reasoning": "CORTEX_RESPONSE"
                }
            )
        }
        
        self.router = ModelRouter()
        self.router.providers = self.providers
        
        # Mock components
        self.ras_threshold = 0.7
        self.memory_store = {}
        self.habit_strengths = {}
        self.event_log = []
        
    async def process_spike(self, sense_type: str, description: str):
        """Mock spike processing through neural cascade."""
        self.event_log.append(("spike", sense_type, description))
        
        # Layer 1: RAS filtering (mock)
        if await self._ras_filter(description):
            return None  # Filtered out
        
        # Layer 2: Thalamus routing decision
        routing_decision = await self._thalamus_route(description)
        
        # Layer 3: Hippocampus memory context
        context = await self._hippocampus_context(description)
        
        # Execute based on routing decision
        if routing_decision == "REFLEX":
            return await self._cerebellum_reflex(description, context)
        elif routing_decision == "TEMPLATE":
            return await self._template_engine(description, context)
        elif routing_decision == "CORTEX":
            return await self._cortex_reasoning(description, context)
        
        return "Unknown routing decision"
    
    async def _ras_filter(self, description: str) -> bool:
        """Mock RAS habituation filtering."""
        # Simple mock: filter if we've seen similar recently
        recent_descriptions = [event[2] for event in self.event_log[-5:]]
        return description in recent_descriptions
    
    async def _thalamus_route(self, description: str) -> str:
        """Mock Thalamus routing decision."""
        desc_lower = description.lower()
        
        # Protocol Alpha routing: REFLEX > TEMPLATE > CORTEX
        if any(word in desc_lower for word in ["reflex", "simple", "quick"]):
            return "REFLEX"
        elif any(word in desc_lower for word in ["template", "moderate", "alert"]):
            return "TEMPLATE"
        else:
            return "CORTEX"
    
    async def _hippocampus_context(self, description: str) -> str:
        """Mock Hippocampus memory retrieval."""
        # Store and retrieve from mock memory
        self.memory_store[description] = f"Context for: {description}"
        return self.memory_store.get(description, "No context")
    
    async def _cerebellum_reflex(self, description: str, context: str) -> str:
        """Mock Cerebellum reflex execution."""
        # Use nano provider (cheapest)
        response = await self.providers["nano"].generate_response(
            f"Execute reflex for: {description}",
            model="mock-nano"
        )
        
        # Update habit strength (Basal Ganglia)
        habit_key = f"reflex_{description}"
        self.habit_strengths[habit_key] = self.habit_strengths.get(habit_key, 0) + 0.1
        
        return f"REFLEX: {response.content} (cost: ${response.cost:.6f})"
    
    async def _template_engine(self, description: str, context: str) -> str:
        """Mock Template Engine guided AI."""
        # Use mini provider (mid-tier)
        response = await self.providers["mini"].generate_response(
            f"Generate template response for: {description}",
            model="mock-mini"
        )
        
        return f"TEMPLATE: {response.content} (cost: ${response.cost:.6f})"
    
    async def _cortex_reasoning(self, description: str, context: str) -> str:
        """Mock Cortex complex reasoning."""
        # Use cortex provider (most expensive)
        response = await self.providers["cortex"].generate_response(
            f"Complex reasoning for: {description}",
            model="mock-cortex"
        )
        
        return f"CORTEX: {response.content} (cost: ${response.cost:.6f})"
    
    def get_cost_stats(self):
        """Get cost statistics from all providers."""
        return {
            name: provider.get_stats()
            for name, provider in self.providers.items()
        }


class TestCascadeWithMocks:
    """Test neural cascade with mock providers."""
    
    @pytest.fixture
    def mock_brain(self):
        """Create mock brain for testing."""
        return MockNSAOrchestrator()
    
    async def test_reflex_routing_cost_optimization(self, mock_brain):
        """Test that reflex tasks use cheapest provider."""
        brain = mock_brain
        
        # Process reflex spike
        result = await brain.process_spike("system", "simple reflex task")
        
        # Should route to REFLEX (cheapest)
        assert "REFLEX:" in result
        assert "REFLEX_RESPONSE" in result
        
        # Verify cost optimization
        stats = brain.get_cost_stats()
        assert stats["nano"]["call_count"] > 0
        assert stats["mini"]["call_count"] == 0
        assert stats["cortex"]["call_count"] == 0
        
        # Cost should be minimal
        total_cost = sum(s["total_cost"] for s in stats.values())
        assert total_cost < 0.001  # Very cheap for reflex
    
    async def test_template_routing_mid_tier_cost(self, mock_brain):
        """Test that template tasks use mid-tier provider."""
        brain = mock_brain
        
        # Process template spike
        result = await brain.process_spike("alert", "moderate template task")
        
        # Should route to TEMPLATE (mid-tier)
        assert "TEMPLATE:" in result
        assert "TEMPLATE_RESPONSE" in result
        
        # Verify mid-tier usage
        stats = brain.get_cost_stats()
        assert stats["nano"]["call_count"] == 0
        assert stats["mini"]["call_count"] > 0
        assert stats["cortex"]["call_count"] == 0
        
        # Cost should be moderate
        total_cost = sum(s["total_cost"] for s in stats.values())
        assert 0.001 <= total_cost < 0.01
    
    async def test_cortex_routing_expensive_tier(self, mock_brain):
        """Test that complex tasks use expensive provider."""
        brain = mock_brain
        
        # Process complex spike
        result = await brain.process_spike("analysis", "complex reasoning task requiring deep analysis")
        
        # Should route to CORTEX (most expensive)
        assert "CORTEX:" in result
        assert "CORTEX_RESPONSE" in result
        
        # Verify expensive tier usage
        stats = brain.get_cost_stats()
        assert stats["nano"]["call_count"] == 0
        assert stats["mini"]["call_count"] == 0
        assert stats["cortex"]["call_count"] > 0
        
        # Cost should be highest
        total_cost = sum(s["total_cost"] for s in stats.values())
        assert total_cost >= 0.01
    
    async def test_protocol_alpha_cost_hierarchy(self, mock_brain):
        """Test Protocol Alpha: REFLEX > TEMPLATE > CORTEX cost hierarchy."""
        brain = mock_brain
        
        # Process different types of spikes
        reflex_result = await brain.process_spike("system", "simple reflex task")
        template_result = await brain.process_spike("alert", "moderate template task")
        cortex_result = await brain.process_spike("analysis", "complex reasoning task")
        
        # Get individual costs
        stats = brain.get_cost_stats()
        reflex_cost = stats["nano"]["total_cost"]
        template_cost = stats["mini"]["total_cost"]
        cortex_cost = stats["cortex"]["total_cost"]
        
        # Verify cost hierarchy
        assert reflex_cost < template_cost < cortex_cost
        
        # Verify routing worked correctly
        assert "REFLEX:" in reflex_result
        assert "TEMPLATE:" in template_result
        assert "CORTEX:" in cortex_result
    
    async def test_ras_habituation_filtering(self, mock_brain):
        """Test RAS habituation filters repeated spikes."""
        brain = mock_brain
        
        # First spike should process
        result1 = await brain.process_spike("system", "repeated spike")
        assert result1 is not None
        
        # Immediate repeat should be filtered
        result2 = await brain.process_spike("system", "repeated spike")
        assert result2 is None  # Filtered by RAS
        
        # Different spike should process
        result3 = await brain.process_spike("system", "different spike")
        assert result3 is not None
    
    async def test_basal_ganglia_habit_reinforcement(self, mock_brain):
        """Test Basal Ganglia habit strength increases with repetition."""
        brain = mock_brain
        
        # Process same reflex multiple times
        for i in range(3):
            await brain.process_spike("system", f"reflex task {i}")
        
        # Check habit strength increased
        habit_keys = [k for k in brain.habit_strengths.keys() if "reflex" in k]
        assert len(habit_keys) > 0
        
        # Habit strength should increase with repetition
        for key in habit_keys:
            assert brain.habit_strengths[key] > 0
    
    async def test_concurrent_spike_processing_cost_efficiency(self, mock_brain):
        """Test concurrent spike processing maintains cost efficiency."""
        brain = mock_brain
        
        # Create mixed workload
        spike_tasks = [
            brain.process_spike("system", f"simple reflex {i}")
            for i in range(5)
        ] + [
            brain.process_spike("alert", f"template task {i}")
            for i in range(2)
        ] + [
            brain.process_spike("analysis", f"complex task {i}")
            for i in range(1)
        ]
        
        # Process concurrently
        results = await asyncio.gather(*spike_tasks)
        
        # Verify all processed
        processed_results = [r for r in results if r is not None]
        assert len(processed_results) == 8  # All should process (no duplicates)
        
        # Verify cost distribution
        stats = brain.get_cost_stats()
        total_cost = sum(s["total_cost"] for s in stats.values())
        
        # Should be dominated by cheap operations
        reflex_cost = stats["nano"]["total_cost"]
        template_cost = stats["mini"]["total_cost"]
        cortex_cost = stats["cortex"]["total_cost"]
        
        # 5 reflex + 2 template + 1 cortex
        assert reflex_cost < template_cost + cortex_cost  # Cheap operations dominate
        assert total_cost < 0.05  # Total should be reasonable
    
    async def test_memory_context_integration(self, mock_brain):
        """Test Hippocampus memory context integration."""
        brain = mock_brain
        
        # Process spike to store memory
        result = await brain.process_spike("system", "memory test spike")
        
        # Verify memory was stored
        assert "memory test spike" in brain.memory_store
        assert "Context for: memory test spike" in brain.memory_store["memory test spike"]
    
    async def test_latency_vs_cost_tradeoffs(self, mock_brain):
        """Test latency vs cost tradeoffs across tiers."""
        brain = mock_brain
        
        # Configure different latencies for providers
        brain.providers["nano"].set_latency(10.0, 2.0)    # Fast, cheap
        brain.providers["mini"].set_latency(50.0, 10.0)   # Medium
        brain.providers["cortex"].set_latency(200.0, 50.0) # Slow, expensive
        
        # Process different spike types
        import time
        
        start = time.time()
        reflex_result = await brain.process_spike("system", "simple reflex")
        reflex_time = time.time() - start
        
        start = time.time()
        template_result = await brain.process_spike("alert", "template task")
        template_time = time.time() - start
        
        start = time.time()
        cortex_result = await brain.process_spike("analysis", "complex task")
        cortex_time = time.time() - start
        
        # Verify latency hierarchy matches cost hierarchy
        assert reflex_time < template_time < cortex_time
        
        # Verify costs match expectations
        stats = brain.get_cost_stats()
        assert stats["nano"]["total_cost"] < stats["mini"]["total_cost"] < stats["cortex"]["total_cost"]
    
    async def test_provider_failure_resilience(self, mock_brain):
        """Test cascade resilience when providers fail."""
        brain = mock_brain
        
        # Configure nano provider to fail
        brain.providers["nano"].set_failure_rate(1.0)
        
        # Should still process but potentially route differently
        # In a real system, this would fallback to next available provider
        with pytest.raises(Exception):
            await brain.process_spike("system", "simple reflex")
        
        # Verify failure was tracked
        stats = brain.get_cost_stats()
        assert stats["nano"]["failure_count"] > 0
    
    async def test_daily_cost_budget_simulation(self, mock_brain):
        """Test daily cost budget simulation with realistic workload."""
        brain = mock_brain
        
        # Simulate realistic daily workload
        daily_spikes = [
            ("system", "cpu usage high", "reflex"),      # 50 per day
            ("system", "memory usage high", "reflex"),   # 30 per day  
            ("alert", "security event", "template"),     # 10 per day
            ("analysis", "performance analysis", "cortex") # 2 per day
        ]
        
        total_daily_cost = 0.0
        
        # Simulate workload distribution
        for sense_type, description, expected_type in daily_spikes:
            # Simulate multiple occurrences
            if expected_type == "reflex":
                count = 20  # High frequency
            elif expected_type == "template":
                count = 5   # Medium frequency
            else:
                count = 1   # Low frequency
            
            for i in range(count):
                result = await brain.process_spike(sense_type, f"{description} {i}")
                if result:  # Not filtered by RAS
                    # Extract cost from result string
                    if "cost: $" in result:
                        cost_str = result.split("cost: $")[1].split(")")[0]
                        total_daily_cost += float(cost_str)
        
        # Verify daily budget compliance
        daily_budget = 0.50  # $0.50/day target
        assert total_daily_cost <= daily_budget
        
        print(f"Simulated daily cost: ${total_daily_cost:.4f}")
        
        # Verify cost distribution follows Protocol Alpha
        stats = brain.get_cost_stats()
        reflex_calls = stats["nano"]["call_count"]
        template_calls = stats["mini"]["call_count"] 
        cortex_calls = stats["cortex"]["call_count"]
        
        # Should be dominated by cheap reflex calls
        assert reflex_calls > template_calls > cortex_calls