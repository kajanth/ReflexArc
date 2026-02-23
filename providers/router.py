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
from typing import List, Dict, Optional
from collections import defaultdict

from providers.base import BaseProvider, StandardResponse, ProviderConfig, ModelInfo
from providers.pricing import PRICING_CATALOG, classify_tier

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

        self._init_providers()

        if auto_discover:
            self._auto_discover()
        else:
            self._load_config()

    def _init_providers(self):
        """Initialize all registered providers (lazy — no API calls yet)."""
        for name, cls in PROVIDER_REGISTRY.items():
            try:
                self._providers[name] = cls()
            except Exception as e:
                print(f"[Router] Warning: Failed to init provider '{name}': {e}")

    def _auto_discover(self):
        """
        Authenticate with each provider, discover models, and auto-build tiers.
        Falls back to static config if no providers authenticate.
        """
        print("\n--- Provider Discovery ---")

        all_models = []
        authenticated_providers = []

        for name, provider in self._providers.items():
            if not provider.is_available():
                print(f"  ⊘ {name}: No credentials configured")
                continue

            # Step 1: Authenticate
            if provider.authenticate():
                authenticated_providers.append(name)

                # Step 2: List models
                models = provider.list_models()
                all_models.extend(models)

        if not authenticated_providers:
            print("\n[Router] No providers authenticated. Loading static config...")
            self._load_static_fallback()
            return

        self._discovered_models = all_models

        # Step 3: Auto-build tiers from discovered models
        self._build_tiers_from_models(all_models)

        # Save the discovered config
        self._save_config()

        total = len(all_models)
        print(f"\n--- Discovery Complete: {total} models across {len(authenticated_providers)} providers ---")

    def _build_tiers_from_models(self, models: List[ModelInfo]):
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

    def _load_static_fallback(self):
        """Load config from disk as fallback when no providers authenticate."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r") as f:
                    self._config = json.load(f)
                print(f"[Router] Loaded static config from {self._config_path}")
                return
            except (json.JSONDecodeError, IOError):
                pass

        # Minimal empty config
        self._config = {
            "strategy": "cheapest",
            "auto_discovered": False,
            "tiers": {"nano": [], "mini": [], "cortex": []},
        }

    def _load_config(self):
        """Load config from disk (for manual/static mode)."""
        self._load_static_fallback()

    def _save_config(self):
        """Save the current config to disk."""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def reload_config(self):
        """Reload config from disk."""
        self._load_config()

    def rediscover(self):
        """Re-run the full discovery process."""
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
                    print(f"[Router] No models for '{tier}', falling back to '{fallback_tier}'")
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
            config = ProviderConfig(
                provider=entry["provider"],
                model=model,
                cost_per_1k_input=entry.get("cost_per_1k_input", 0),
                cost_per_1k_output=entry.get("cost_per_1k_output", 0),
                weight=entry.get("weight", 1.0),
            )

            try:
                # Pass tools if the provider supports them
                import inspect
                sig = inspect.signature(prov.chat)
                if "tools" in sig.parameters:
                    response = prov.chat(messages, model, max_tokens, tools=tools)
                else:
                    # Some existing providers (Bedrock/Gemini) might not support tools yet
                    # We'll just gracefully ignore tools for them for now rather than crashing
                    response = prov.chat(messages, model, max_tokens)
                    
                response.cost = config.estimate_cost(
                    response.prompt_tokens, response.completion_tokens
                )

                print(
                    f"[Router] {tier.upper()} → {response.provider}:{response.model} "
                    f"| {response.prompt_tokens}+{response.completion_tokens} tokens "
                    f"| ${response.cost:.6f} | {response.latency:.2f}s"
                )
                if response.tool_calls:
                    print(f"[Router] 🔨 Model requested {len(response.tool_calls)} tool call(s)")
                
                return response

            except Exception as e:
                last_error = e
                print(
                    f"[Router] {entry['provider']}:{model} failed: {e}. "
                    f"Falling back..."
                )
                continue

        raise RuntimeError(
            f"All providers failed for tier '{tier}'. Last error: {last_error}"
        )

    def _select(self, available, strategy):
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

    def add_provider(self, name: str, provider_instance: BaseProvider):
        """Register a custom provider at runtime."""
        self._providers[name] = provider_instance
        print(f"[Router] Registered custom provider: {name}")

    def get_status(self) -> Dict:
        """Get a summary of the router's current state."""
        authenticated = self.get_authenticated_providers()
        tiers = {}
        for tier_name, models in self._config.get("tiers", {}).items():
            tier_info = []
            for entry in models:
                prov = self._providers.get(entry["provider"])
                tier_info.append({
                    "provider": entry["provider"],
                    "model": entry["model"],
                    "available": prov.is_available() if prov else False,
                    "authenticated": entry["provider"] in authenticated,
                    "cost_1k_in": entry.get("cost_per_1k_input", 0),
                    "cost_1k_out": entry.get("cost_per_1k_output", 0),
                    "weight": entry.get("weight", 1.0),
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
        }
