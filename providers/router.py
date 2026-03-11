"""
🧠 NSA Model Router
Dynamic, cost-weighted provider selection with automatic fallback.

On startup:
  1. Authenticates with each configured provider
  2. Fetches available models from each
  3. Matches models to the pricing catalog
  4. Auto-builds tier configurations (nano/mini/cortex) by cost

Strategies:
  - "cheapest"  : Always pick the lowest cost-per-token available provider
  - "weighted"  : Weighted random selection based on configured weights
  - "priority"  : Use first available in ranked order
"""

import os
import json
import time
import random
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import defaultdict

from providers.base import BaseProvider, StandardResponse, ProviderConfig, ModelInfo
from providers.pricing import PRICING_CATALOG, classify_tier
from providers.circuit_breaker import get_circuit_breaker_manager
from utils.logging_config import get_logger
from pybreaker import CircuitBreakerError

logger = get_logger(__name__)

# ──────────────────────────────────────────────────
# Provider Registry: Add new providers here
# ──────────────────────────────────────────────────
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from providers.gemini_provider import GeminiProvider
from providers.bedrock_provider import BedrockProvider

PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "bedrock": BedrockProvider,
}

CONFIG_FILE = "memory/providers.json"


class ModelRouter:
    """
    Cost-weighted, multi-provider model router with dynamic discovery.

    On init:
      1. Instantiates all registered providers
      2. Authenticates with each (verifies API keys work)
      3. Lists available models from each
      4. Auto-builds tier configs sorted by cost

    Usage:
        router = ModelRouter()
        response = router.route("nano", messages=[...])
        print(response.content, response.provider, response.cost)
    """

    def __init__(self, config_path: str = None, auto_discover: bool = True):
        self._config_path = config_path or CONFIG_FILE
        self._providers = {}          # name -> BaseProvider instance
        self._discovered_models = []  # all ModelInfo from all providers
        self._config = None
        self._strategy = "cheapest"
        self._circuit_breaker = get_circuit_breaker_manager()

        self._init_providers()

        if auto_discover:
            self._auto_discover()
        else:
            self._load_config()

    def _init_providers(self) -> None:
        """Initialize all registered providers (lazy — no API calls yet)."""
        for name, cls in PROVIDER_REGISTRY.items():
            try:
                self._providers[name] = cls()
            except Exception as e:
                logger.warning("provider_init_failed",
                              provider=name,
                              error=str(e))

    def _auto_discover(self) -> None:
        """
        Authenticate with each provider, discover models, and auto-build tiers.
        Falls back to static config if no providers authenticate.
        Uses cached results if available and not expired.
        """
        # Check for cached discovery results
        cache_file = "memory/provider_cache.json"
        cache_ttl = 86400  # 24 hours in seconds
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)
                
                cache_time = cache_data.get("discovery_time", 0)
                cache_age = time.time() - cache_time
                
                if cache_age < cache_ttl:
                    # Use cached results
                    self._discovered_models = [
                        ModelInfo(**m) for m in cache_data.get("models", [])
                    ]
                    self._config = cache_data.get("config", {})
                    
                    logger.info("provider_discovery_cached",
                               cache_age_hours=round(cache_age / 3600, 1),
                               total_models=len(self._discovered_models))
                    return
            except (json.JSONDecodeError, IOError, KeyError) as e:
                logger.warning("cache_load_failed", error=str(e))
        
        logger.info("provider_discovery_start")

        all_models = []
        authenticated_providers = []

        for name, provider in self._providers.items():
            if not provider.is_available():
                logger.debug("provider_no_credentials", provider=name)
                continue

            # Step 1: Authenticate
            if provider.authenticate():
                authenticated_providers.append(name)

                # Step 2: List models
                models = provider.list_models()
                all_models.extend(models)

        if not authenticated_providers:
            logger.warning("no_providers_authenticated",
                          message="Loading static config")
            self._load_static_fallback()
            return

        self._discovered_models = all_models

        # Step 3: Auto-build tiers from discovered models
        self._build_tiers_from_models(all_models)

        # Save the discovered config
        self._save_config()
        
        # Save to cache
        self._save_cache(cache_file)

        total = len(all_models)
        logger.info("provider_discovery_complete",
                   total_models=total,
                   num_providers=len(authenticated_providers),
                   providers=authenticated_providers)

    def _build_tiers_from_models(self, models: List[ModelInfo]) -> None:
        """
        Auto-categorize discovered models into nano/mini/cortex tiers,
        sorted by cost within each tier.
        """
        tiers = defaultdict(list)

        for model in models:
            entry = {
                "provider": model.provider,
                "model": model.model_id,
                "cost_per_1k_input": model.cost_per_1k_input,
                "cost_per_1k_output": model.cost_per_1k_output,
                "weight": 1.0,
                "context_window": model.context_window,
                "enabled": True,
            }
            tiers[model.tier].append(entry)

        # Sort each tier by cost (cheapest first)
        for tier_name in tiers:
            tiers[tier_name].sort(key=lambda e: e["cost_per_1k_input"])

        # Ensure all three tiers exist
        for t in ["nano", "mini", "cortex"]:
            if t not in tiers:
                tiers[t] = []

        # If a tier is empty, promote from a lower tier
        if not tiers["mini"] and tiers["nano"]:
            # Use the most expensive nano as mini fallback
            tiers["mini"] = [tiers["nano"][-1].copy()]
        if not tiers["cortex"] and tiers["mini"]:
            tiers["cortex"] = [tiers["mini"][-1].copy()]

        self._config = {
            "strategy": self._strategy,
            "auto_discovered": True,
            "discovery_time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tiers": dict(tiers),
        }

    def _load_static_fallback(self) -> None:
        """Load config from disk as fallback when no providers authenticate."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r") as f:
                    self._config = json.load(f)
                logger.info("static_config_loaded", path=self._config_path)
                return
            except (json.JSONDecodeError, IOError):
                pass

        # Minimal empty config
        self._config = {
            "strategy": "cheapest",
            "auto_discovered": False,
            "tiers": {"nano": [], "mini": [], "cortex": []},
        }

    def _load_config(self) -> None:
        """Load config from disk (for manual/static mode)."""
        self._load_static_fallback()

    def _save_config(self) -> None:
        """Save the current config to disk."""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self._config, f, indent=2)
    
    def _save_cache(self, cache_file: str) -> None:
        """Save discovery results to cache."""
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            cache_data = {
                "discovery_time": time.time(),
                "models": [
                    {
                        "provider": m.provider,
                        "model_id": m.model_id,
                        "tier": m.tier,
                        "cost_per_1k_input": m.cost_per_1k_input,
                        "cost_per_1k_output": m.cost_per_1k_output,
                        "context_window": m.context_window,
                    }
                    for m in self._discovered_models
                ],
                "config": self._config,
            }
            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            logger.info("provider_cache_saved", path=cache_file)
        except IOError as e:
            logger.warning("cache_save_failed", error=str(e))

    def reload_config(self) -> None:
        """Reload config from disk."""
        self._load_config()

    def rediscover(self) -> None:
        """Re-run the full discovery process and invalidate cache."""
        # Invalidate cache by removing it
        cache_file = "memory/provider_cache.json"
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                logger.info("provider_cache_invalidated")
            except OSError as e:
                logger.warning("cache_invalidation_failed", error=str(e))
        
        self._auto_discover()

    def get_available_providers(self) -> List[str]:
        """Return names of providers that have valid API keys configured."""
        return [name for name, prov in self._providers.items() if prov.is_available()]

    def get_authenticated_providers(self) -> List[str]:
        """Return names of providers that successfully authenticated."""
        return [name for name, prov in self._providers.items()
                if getattr(prov, '_authenticated', False)]

    def get_discovered_models(self) -> List[ModelInfo]:
        """Return all discovered models across all providers."""
        return self._discovered_models

    def get_tier_config(self, tier: str) -> List[Dict]:
        """Get the ranked provider list for a tier."""
        return self._config.get("tiers", {}).get(tier, [])

    def route(self, tier: str, messages: List[Dict],
              max_tokens: int = 200, tools: Optional[List[Dict]] = None) -> StandardResponse:
        """
        Route a request to the best available provider for the given tier.

        Args:
            tier: Model tier ("nano", "mini", "cortex").
            messages: OpenAI-style message list.
            max_tokens: Max response tokens.
            tools: Optional array of JSON schema tool definitions.

        Returns:
            StandardResponse from whichever provider handled it.
        """
        tier_models = self.get_tier_config(tier)
        if not tier_models:
            # Fallback: try any available tier
            for fallback_tier in ["nano", "mini", "cortex"]:
                tier_models = self.get_tier_config(fallback_tier)
                if tier_models:
                    logger.warning("tier_fallback",
                                  requested_tier=tier,
                                  fallback_tier=fallback_tier)
                    break

        if not tier_models:
            raise RuntimeError(
                f"No models configured for tier '{tier}'. "
                f"Available providers: {self.get_available_providers()}. "
                f"Run rediscover() or check API keys."
            )

        strategy = self._config.get("strategy", "cheapest")

        # Filter to available providers
        available = []
        for entry in tier_models:
            provider_name = entry["provider"]
            prov = self._providers.get(provider_name)
            if prov and prov.is_available() and entry.get("enabled", True):
                available.append((entry, prov))

        if not available:
            raise RuntimeError(
                f"No available providers for tier '{tier}'. "
                f"Authenticated: {self.get_authenticated_providers()}"
            )

        # Select based on strategy
        ordered = self._select(available, strategy)

        # Try each in order (auto-fallback on failure)
        last_error = None
        for entry, prov in ordered:
            model = entry["model"]
            provider_name = entry["provider"]
            config = ProviderConfig(
                provider=provider_name,
                model=model,
                cost_per_1k_input=entry.get("cost_per_1k_input", 0),
                cost_per_1k_output=entry.get("cost_per_1k_output", 0),
                weight=entry.get("weight", 1.0),
            )

            try:
                # Check circuit breaker state before attempting call
                breaker_state = self._circuit_breaker.get_state(provider_name)
                if breaker_state == "open":
                    backoff = self._circuit_breaker._calculate_backoff(provider_name)
                    logger.warning("provider_circuit_open",
                                  provider=provider_name,
                                  backoff_seconds=backoff,
                                  action="skipping")
                    continue
                
                # Wrap provider call with circuit breaker
                def _call_provider():
                    import inspect
                    sig = inspect.signature(prov.chat)
                    if "tools" in sig.parameters:
                        return prov.chat(messages, model, max_tokens, tools=tools)
                    else:
                        return prov.chat(messages, model, max_tokens)
                
                response = self._circuit_breaker.call(provider_name, _call_provider)
                    
                response.cost = config.estimate_cost(
                    response.prompt_tokens, response.completion_tokens
                )

                logger.info("model_routed",
                           tier=tier,
                           provider=response.provider,
                           model=response.model,
                           prompt_tokens=response.prompt_tokens,
                           completion_tokens=response.completion_tokens,
                           cost=response.cost,
                           latency=response.latency,
                           tool_calls=len(response.tool_calls) if response.tool_calls else 0,
                           circuit_state=breaker_state)
                
                return response

            except CircuitBreakerError as e:
                last_error = e
                logger.warning("provider_circuit_breaker_triggered",
                              provider=provider_name,
                              model=model,
                              action="falling_back")
                continue
            except Exception as e:
                last_error = e
                logger.warning("provider_failed",
                              provider=provider_name,
                              model=model,
                              error=str(e),
                              action="falling_back")
                continue

        raise RuntimeError(
            f"All providers failed for tier '{tier}'. Last error: {last_error}"
        )

    def pre_allocate(self, tier: str) -> bool:
        """
        Anticipatory sensing pre-allocation.
        Sends a minimal 1-token prompt to the primary provider in the tier
        to establish TLS handshakes and warm up the deployment endpoint.
        """
        tier_models = self.get_tier_config(tier)
        if not tier_models:
            return False

        strategy = self._config.get("strategy", "cheapest")
        available = []
        for entry in tier_models:
            provider_name = entry["provider"]
            prov = self._providers.get(provider_name)
            if prov and prov.is_available() and entry.get("enabled", True):
                available.append((entry, prov))

        if not available:
            return False

        ordered = self._select(available, strategy)
        for entry, prov in ordered:
            model = entry["model"]
            logger.info("pre_allocating_capacity",
                       tier=tier,
                       provider=entry['provider'],
                       model=model)
            try:
                # Send minimum payload to wake up the model
                prov.chat([{"role": "user", "content": "Ack"}], model, max_tokens=1)
                return True
            except Exception as e:
                logger.warning("pre_allocation_failed",
                              provider=entry['provider'],
                              model=model,
                              error=str(e))
                pass
        return False

    def _select(self, available: List[Tuple[Dict[str, Any], BaseProvider]], strategy: str) -> List[Tuple[Dict[str, Any], BaseProvider]]:
        """Order providers by strategy."""
        if strategy == "cheapest":
            return sorted(
                available,
                key=lambda x: x[0].get("cost_per_1k_input", float("inf"))
            )
        elif strategy == "weighted":
            weights = [entry.get("weight", 1.0) for entry, _ in available]
            result = []
            items = list(available)
            w = list(weights)
            while items:
                chosen = random.choices(range(len(items)), weights=w, k=1)[0]
                result.append(items.pop(chosen))
                w.pop(chosen)
            return result
        elif strategy == "priority":
            return available
        else:
            return sorted(
                available,
                key=lambda x: x[0].get("cost_per_1k_input", float("inf"))
            )

    def add_provider(self, name: str, provider_instance: BaseProvider) -> None:
        """Register a custom provider at runtime."""
        self._providers[name] = provider_instance
        logger.info("custom_provider_registered", provider=name)

    def get_status(self) -> Dict:
        """Get a summary of the router's current state."""
        authenticated = self.get_authenticated_providers()
        circuit_metrics = self._circuit_breaker.get_metrics()
        
        tiers = {}
        for tier_name, models in self._config.get("tiers", {}).items():
            tier_info = []
            for entry in models:
                prov = self._providers.get(entry["provider"])
                provider_name = entry["provider"]
                circuit_info = circuit_metrics.get(provider_name, {})
                
                tier_info.append({
                    "provider": provider_name,
                    "model": entry["model"],
                    "available": prov.is_available() if prov else False,
                    "authenticated": provider_name in authenticated,
                    "cost_1k_in": entry.get("cost_per_1k_input", 0),
                    "cost_1k_out": entry.get("cost_per_1k_output", 0),
                    "weight": entry.get("weight", 1.0),
                    "circuit_state": circuit_info.get("state", "closed"),
                    "circuit_failures": circuit_info.get("failure_count", 0),
                })
            tiers[tier_name] = tier_info

        return {
            "strategy": self._config.get("strategy", "cheapest"),
            "auto_discovered": self._config.get("auto_discovered", False),
            "discovery_time": self._config.get("discovery_time", "N/A"),
            "providers_authenticated": authenticated,
            "providers_total": len(self._providers),
            "total_models_discovered": len(self._discovered_models),
            "tiers": tiers,
            "circuit_breakers": circuit_metrics,
        }
