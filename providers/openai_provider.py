"""
🧠 NSA Provider: OpenAI
Supports GPT-4o, GPT-4.1, o3, o4-mini, and all OpenAI models.
Authenticates via models.list() and discovers available models dynamically.
"""

import time
from typing import List, Dict, Optional
from providers.base import BaseProvider, StandardResponse, ModelInfo
from providers.pricing import OPENAI_PRICING, classify_tier


class OpenAIProvider(BaseProvider):

    def __init__(self):
        self._client = None
        self._api_key = self._get_env_key("OPENAI_API_KEY")
        self._authenticated = False
        self._models = []

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return self._api_key is not None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def authenticate(self) -> bool:
        """Verify credentials by listing models."""
        if not self.is_available():
            print(f"  ✗ OpenAI: No API key found")
            return False

        try:
            client = self._get_client()
            # Lightweight auth check — list first page of models
            models = client.models.list()
            self._authenticated = True
            print(f"  ✓ OpenAI: Authenticated")
            return True
        except Exception as e:
            print(f"  ✗ OpenAI: Auth failed — {e}")
            self._authenticated = False
            return False

    def list_models(self) -> List[ModelInfo]:
        """Fetch available models from OpenAI API and match with pricing."""
        if not self._authenticated:
            return []

        try:
            client = self._get_client()
            api_models = client.models.list()

            discovered = []
            for model in api_models.data:
                model_id = model.id

                # Match against our pricing catalog
                if model_id in OPENAI_PRICING:
                    pricing = OPENAI_PRICING[model_id]
                    discovered.append(ModelInfo(
                        model_id=model_id,
                        provider=self.provider_name,
                        cost_per_1k_input=pricing["cost_per_1k_input"],
                        cost_per_1k_output=pricing["cost_per_1k_output"],
                        tier=pricing["tier"],
                        context_window=pricing.get("context_window", 128000),
                    ))

            # Sort by cost (cheapest first)
            discovered.sort(key=lambda m: m.blended_cost)
            self._models = discovered

            model_names = [m.model_id for m in discovered]
            print(f"  ✓ OpenAI: {len(discovered)} models available: {model_names}")
            return discovered

        except Exception as e:
            print(f"  ✗ OpenAI: Failed to list models — {e}")
            return []

    # Models that require max_completion_tokens instead of max_tokens
    # and don't support the system role
    REASONING_PREFIXES = ("o1", "o3", "o4")

    def chat(self, messages: List[Dict], model: str,
             max_tokens: int = 200, tools: Optional[List[Dict]] = None) -> StandardResponse:
        client = self._get_client()
        start = time.time()

        is_reasoning = any(model.startswith(p) for p in self.REASONING_PREFIXES)
        
        kwargs = {
            "model": model,
            "messages": messages,
        }
        
        if tools and not is_reasoning:
            # Note: o1/o3 currently don't support tools in the same way,
            # but standard GPT-4/o4-mini do. The manager already passes OpenAI format.
            kwargs["tools"] = tools

        if is_reasoning:
            # o-series: merge system into user, use max_completion_tokens
            merged_messages = []
            system_content = ""
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    merged_messages.append(msg)

            # Prepend system content to first user message
            if system_content and merged_messages:
                merged_messages[0] = {
                    "role": merged_messages[0]["role"],
                    "content": f"{system_content}\n\n{merged_messages[0]['content']}"
                }

            kwargs["messages"] = merged_messages
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        response = client.chat.completions.create(**kwargs)

        latency = time.time() - start
        choice = response.choices[0]
        usage = response.usage
        
        content = choice.message.content or ""
        
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })

        return StandardResponse(
            content=content.strip(),
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            model=model,
            provider=self.provider_name,
            latency=latency,
            tool_calls=tool_calls
        )
