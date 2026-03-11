"""
🧠 NSA Provider: Base Provider ABC + StandardResponse

Defines the contract all providers must implement and a normalized
response format so the rest of the system is provider-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
import time


@dataclass
class StandardResponse:
    """Normalized response from any provider."""
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    cost: float = 0.0
    latency: float = 0.0
    tool_calls: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class ModelInfo:
    """Metadata about a discovered model."""
    model_id: str
    provider: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    tier: str = "nano"  # nano, mini, cortex
    context_window: int = 4096
    available: bool = True

    @property
    def blended_cost(self) -> float:
        """Average cost per 1K tokens (input+output) for sorting."""
        return (self.cost_per_1k_input + self.cost_per_1k_output) / 2


@dataclass
class ProviderConfig:
    """Configuration for a single provider+model combination."""
    provider: str
    model: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    weight: float = 1.0
    enabled: bool = True
    max_tokens_limit: int = 4096

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate the cost of a request."""
        input_cost = (prompt_tokens / 1000) * self.cost_per_1k_input
        output_cost = (completion_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.

    To add a new provider:
    1. Create a new file in providers/
    2. Subclass BaseProvider
    3. Implement chat(), authenticate(), list_models(), is_available(), provider_name
    4. Add it to the PROVIDER_REGISTRY in router.py
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name for this provider."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured (API key present, etc.)."""
        ...

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Verify credentials by making a lightweight API call.
        Returns True if authentication succeeds, False otherwise.
        Should set self._authenticated and print status.
        """
        ...

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """
        Fetch the list of available models from the provider.
        Returns a list of ModelInfo objects with pricing from the catalog.
        Only returns models the account has access to.
        """
        ...

    @abstractmethod
    def chat(self, messages: List[Dict], model: str,
             max_tokens: int = 200, tools: Optional[List[Dict]] = None) -> StandardResponse:
        """Send a chat completion request."""
        ...

    def _get_env_key(self, *env_names) -> Optional[str]:
        """Helper to check multiple environment variable names for an API key."""
        for name in env_names:
            val = os.environ.get(name)
            if val:
                return val
        return None
