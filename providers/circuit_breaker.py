"""
🧠 NSA Circuit Breaker for Provider Resilience

Implements circuit breaker pattern to prevent cascading failures
when AI providers are unavailable or experiencing issues.
"""

import time
from typing import Dict, Optional, Callable, Any
from pybreaker import CircuitBreaker, CircuitBreakerError
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ProviderCircuitBreaker:
    """
    Circuit breaker manager for AI providers.
    
    Prevents repeated calls to failing providers and implements
    exponential backoff for recovery attempts.
    """
    
    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: int = 60
    ):
        """
        Initialize circuit breaker manager.
        
        Args:
            fail_max: Number of failures before opening circuit
            reset_timeout: Seconds to wait before attempting recovery
        """
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        
    def get_breaker(self, provider_name: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a provider.
        
        Args:
            provider_name: Name of the AI provider
            
        Returns:
            CircuitBreaker instance for the provider
        """
        if provider_name not in self._breakers:
            breaker = CircuitBreaker(
                fail_max=self.fail_max,
                reset_timeout=self.reset_timeout,
                name=f"{provider_name}_breaker",
                listeners=[self._create_listener(provider_name)]
            )
            self._breakers[provider_name] = breaker
            self._failure_counts[provider_name] = 0
            logger.info("circuit_breaker_created",
                       provider=provider_name,
                       fail_max=self.fail_max,
                       timeout=self.reset_timeout)
        
        return self._breakers[provider_name]
    
    def _create_listener(self, provider_name: str):
        """Create a listener for circuit breaker state changes."""
        class BreakerListener:
            def __init__(self, manager, provider):
                self.manager = manager
                self.provider = provider
            
            def state_change(self, breaker, old_state, new_state):
                """Called when circuit breaker changes state."""
                logger.warning("circuit_breaker_state_change",
                              provider=self.provider,
                              old_state=str(old_state),
                              new_state=str(new_state),
                              failure_count=breaker.fail_counter)
                
                if str(new_state) == "open":
                    self.manager._last_failure_time[self.provider] = time.time()
            
            def before_call(self, breaker, func, *args, **kwargs):
                """Called before executing protected function."""
                pass
            
            def success(self, breaker):
                """Called on successful execution."""
                if self.provider in self.manager._failure_counts:
                    self.manager._failure_counts[self.provider] = 0
                logger.debug("circuit_breaker_success",
                            provider=self.provider)
            
            def failure(self, breaker, exception):
                """Called on failed execution."""
                self.manager._failure_counts[self.provider] = breaker.fail_counter
                logger.warning("circuit_breaker_failure",
                              provider=self.provider,
                              failure_count=breaker.fail_counter,
                              error=str(exception))
        
        return BreakerListener(self, provider_name)
    
    def call(self, provider_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            provider_name: Name of the provider
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result of function execution
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function execution fails
        """
        breaker = self.get_breaker(provider_name)
        
        try:
            return breaker.call(func, *args, **kwargs)
        except CircuitBreakerError as e:
            # Circuit is open, calculate backoff time
            backoff_time = self._calculate_backoff(provider_name)
            logger.error("circuit_breaker_open",
                        provider=provider_name,
                        backoff_seconds=backoff_time,
                        message="Provider temporarily unavailable")
            raise
    
    def _calculate_backoff(self, provider_name: str) -> float:
        """
        Calculate exponential backoff time for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Backoff time in seconds
        """
        failure_count = self._failure_counts.get(provider_name, 0)
        last_failure = self._last_failure_time.get(provider_name, 0)
        
        # Exponential backoff: 2^failures seconds, capped at 5 minutes
        backoff = min(2 ** failure_count, 300)
        
        # Calculate remaining backoff time
        elapsed = time.time() - last_failure
        remaining = max(0, backoff - elapsed)
        
        return remaining
    
    def get_state(self, provider_name: str) -> str:
        """
        Get the current state of a provider's circuit breaker.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            State name: "closed", "open", or "half_open"
        """
        if provider_name not in self._breakers:
            return "closed"
        
        return str(self._breakers[provider_name].current_state)
    
    def reset(self, provider_name: str) -> None:
        """
        Manually reset a provider's circuit breaker.
        
        Args:
            provider_name: Name of the provider
        """
        if provider_name in self._breakers:
            self._breakers[provider_name].close()
            self._failure_counts[provider_name] = 0
            logger.info("circuit_breaker_reset",
                       provider=provider_name)
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all circuit breakers.
        
        Returns:
            Dict mapping provider names to their metrics
        """
        metrics = {}
        for provider_name, breaker in self._breakers.items():
            metrics[provider_name] = {
                "state": str(breaker.current_state),
                "failure_count": breaker.fail_counter,
                "last_failure_time": self._last_failure_time.get(provider_name, 0),
                "backoff_seconds": self._calculate_backoff(provider_name)
            }
        return metrics


# Global circuit breaker manager instance
_circuit_breaker_manager: Optional[ProviderCircuitBreaker] = None


def get_circuit_breaker_manager() -> ProviderCircuitBreaker:
    """Get or create the global circuit breaker manager."""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = ProviderCircuitBreaker(
            fail_max=5,
            reset_timeout=60
        )
    return _circuit_breaker_manager
