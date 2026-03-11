"""
🧠 NSA Provider: Anthropic Claude
Supports Claude 3.5, Claude 4, and all Anthropic models.
Authenticates with a minimal test call and discovers models from catalog.
"""

import time
from typing import List, Dict, Optional
from providers.base import BaseProvider, StandardResponse, ModelInfo
from providers.pricing import ANTHROPIC_PRICING


class AnthropicProvider(BaseProvider):

    def __init__(self):
        self._client = None
        self._api_key = self._get_env_key("ANTHROPIC_API_KEY")
        self._authenticated = False
        self._models = []

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return self._api_key is not None

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def authenticate(self) -> bool:
        """Verify credentials with a minimal API call."""
        if not self.is_available():
            print(f"  ✗ Anthropic: No API key found")
            return False

        try:
            client = self._get_client()
            # Minimal auth check — 1 token response
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            self._authenticated = True
            print(f"  ✓ Anthropic: Authenticated")
            return True
        except Exception as e:
            error_str = str(e).lower()
            # If it's a "model not found" error, auth itself worked
            if "not_found" in error_str or "model" in error_str:
                self._authenticated = True
                print(f"  ✓ Anthropic: Authenticated (haiku not available, trying others)")
                return True
            print(f"  ✗ Anthropic: Auth failed — {e}")
            self._authenticated = False
            return False

    def list_models(self) -> List[ModelInfo]:
        """
        Discover available models by probing known models from the catalog.
        Anthropic doesn't have a list models API, so we test each known model.
        """
        if not self._authenticated:
            return []

        client = self._get_client()
        discovered = []

        for model_id, pricing in ANTHROPIC_PRICING.items():
            try:
                # Probe with 1 token to check availability
                client.messages.create(
                    model=model_id,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
                discovered.append(ModelInfo(
                    model_id=model_id,
                    provider=self.provider_name,
                    cost_per_1k_input=pricing["cost_per_1k_input"],
                    cost_per_1k_output=pricing["cost_per_1k_output"],
                    tier=pricing["tier"],
                    context_window=pricing.get("context_window", 200000),
                ))
            except Exception:
                # Model not available for this API key
                pass

        discovered.sort(key=lambda m: m.blended_cost)
        self._models = discovered

        model_names = [m.model_id for m in discovered]
        print(f"  ✓ Anthropic: {len(discovered)} models available: {model_names}")
        return discovered

    def chat(self, messages: List[Dict], model: str,
             max_tokens: int = 200, tools: Optional[List[Dict]] = None) -> StandardResponse:
        client = self._get_client()
        start = time.time()

        # Anthropic uses a separate system parameter
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        if not chat_messages:
            chat_messages = [{"role": "user", "content": system_msg}]
            system_msg = ""

        kwargs = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg

        if tools:
            # Convert OpenAI format (used by MCP manager) to Anthropic format
            anthropic_tools = []
            for t in tools:
                if t.get("type") == "function":
                    func = t["function"]
                    anthropic_tools.append({
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                    })
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools

        response = client.messages.create(**kwargs)
        latency = time.time() - start

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                # Standardize to OpenAI format which the core expects
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": block.input
                    }
                })

        return StandardResponse(
            content=content.strip(),
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=model,
            provider=self.provider_name,
            latency=latency,
            tool_calls=tool_calls
        )
