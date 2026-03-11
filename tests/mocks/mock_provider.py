"""
Mock AI provider for testing without API costs.

Provides deterministic responses for testing the neural cascade
without making actual API calls to OpenAI, Anthropic, etc.

Features:
- Deterministic responses based on prompt patterns
- Cost tracking for Protocol Alpha testing
- Latency simulation for performance testing
- Configurable failure modes for resilience testing
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from providers.base import BaseProvider, StandardResponse, ModelInfo


class MockProvider(BaseProvider):
    """Mock provider that returns deterministic responses with cost and latency simulation."""
    
    def __init__(
        self, 
        name: str = "mock", 
        responses: Optional[Dict[str, str]] = None,
        base_latency_ms: float = 50.0,
        latency_variance: float = 20.0,
        cost_per_token: float = 0.0001,
        failure_rate: float = 0.0
    ):
        """
        Initialize mock provider with configurable behavior.
        
        Args:
            name: Provider name
            responses: Predefined responses for specific prompts
            base_latency_ms: Base latency in milliseconds
            latency_variance: Random variance in latency (±ms)
            cost_per_token: Cost per token for testing cost optimization
            failure_rate: Probability of failure (0.0-1.0) for resilience testing
        """
        self.name = name
        self.responses = responses or {}
        self.call_count = 0
        self.last_request = None
        self.total_cost = 0.0
        self.total_tokens = 0
        
        # Latency simulation
        self.base_latency_ms = base_latency_ms
        self.latency_variance = latency_variance
        
        # Cost simulation
        self.cost_per_token = cost_per_token
        
        # Failure simulation
        self.failure_rate = failure_rate
        self.failure_count = 0
        
    async def get_available_models(self) -> List[ModelInfo]:
        """Return mock model info with realistic cost tiers."""
        return [
            ModelInfo(
                name="mock-nano",
                tier="nano", 
                cost_per_token=0.0001,  # Cheapest tier
                context_window=4096
            ),
            ModelInfo(
                name="mock-mini",
                tier="mini",
                cost_per_token=0.001,   # Mid tier
                context_window=8192
            ),
            ModelInfo(
                name="mock-cortex",
                tier="cortex",
                cost_per_token=0.01,    # Most expensive
                context_window=32768
            )
        ]
    
    async def generate_response(
        self, 
        prompt: str, 
        model: str = "mock-nano",
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs
    ) -> StandardResponse:
        """Generate mock response with latency and cost simulation."""
        start_time = time.time()
        
        # Simulate failure if configured
        if self.failure_rate > 0:
            import random
            if random.random() < self.failure_rate:
                self.failure_count += 1
                raise Exception(f"Mock provider failure #{self.failure_count}")
        
        self.call_count += 1
        self.last_request = {
            "prompt": prompt,
            "model": model, 
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        # Simulate latency
        await self._simulate_latency()
        
        # Generate response content
        content = self._generate_content(prompt)
        
        # Calculate tokens and cost
        prompt_tokens = len(prompt.split())
        completion_tokens = len(content.split())
        total_tokens = prompt_tokens + completion_tokens
        
        # Get model-specific cost
        model_cost = self._get_model_cost(model)
        cost = total_tokens * model_cost
        
        # Track totals
        self.total_tokens += total_tokens
        self.total_cost += cost
        
        # Calculate actual latency
        actual_latency = (time.time() - start_time) * 1000
        
        return StandardResponse(
            content=content,
            model=model,
            usage_tokens=total_tokens,
            cost=cost,
            latency_ms=actual_latency
        )
    
    async def _simulate_latency(self):
        """Simulate realistic API latency."""
        import random
        
        # Add random variance to base latency
        variance = random.uniform(-self.latency_variance, self.latency_variance)
        latency_ms = max(1.0, self.base_latency_ms + variance)
        
        # Convert to seconds and sleep
        await asyncio.sleep(latency_ms / 1000.0)
    
    def _generate_content(self, prompt: str) -> str:
        """Generate deterministic response content."""
        # Return predefined response if available
        if prompt in self.responses:
            return self.responses[prompt]
        
        # Generate response based on prompt patterns
        prompt_lower = prompt.lower()
        
        if "threat" in prompt_lower or "security" in prompt_lower:
            return "SECURITY ALERT: Potential threat detected. Initiating containment protocols."
        elif "cpu" in prompt_lower or "memory" in prompt_lower:
            return "SYSTEM VITALS: Resource usage spike detected. Monitoring for patterns."
        elif "error" in prompt_lower or "exception" in prompt_lower:
            return "ERROR ANALYSIS: Exception traced to module interaction. Suggesting remediation."
        elif "webhook" in prompt_lower or "github" in prompt_lower:
            return "WEBHOOK PROCESSED: Repository event analyzed. No action required."
        elif "reflex" in prompt_lower:
            return "REFLEX_RESPONSE"  # Indicates should route to Cerebellum
        elif "template" in prompt_lower:
            return "TEMPLATE_RESPONSE"  # Indicates should route to Template Engine
        else:
            # Default response for unknown patterns
            return f"Mock response for: {prompt[:50]}..."
    
    def _get_model_cost(self, model: str) -> float:
        """Get cost per token for specific model."""
        cost_map = {
            "mock-nano": 0.0001,
            "mock-mini": 0.001,
            "mock-cortex": 0.01
        }
        return cost_map.get(model, self.cost_per_token)
    
    def reset_stats(self):
        """Reset call statistics and costs."""
        self.call_count = 0
        self.last_request = None
        self.total_cost = 0.0
        self.total_tokens = 0
        self.failure_count = 0
        
    def set_response(self, prompt: str, response: str):
        """Set a specific response for a prompt."""
        self.responses[prompt] = response
    
    def set_latency(self, base_ms: float, variance_ms: float = 0.0):
        """Configure latency simulation."""
        self.base_latency_ms = base_ms
        self.latency_variance = variance_ms
    
    def set_failure_rate(self, rate: float):
        """Configure failure rate for resilience testing."""
        self.failure_rate = max(0.0, min(1.0, rate))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics for testing."""
        return {
            "call_count": self.call_count,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "failure_count": self.failure_count,
            "avg_cost_per_call": self.total_cost / max(1, self.call_count),
            "avg_tokens_per_call": self.total_tokens / max(1, self.call_count)
        }