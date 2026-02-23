"""
🧠 NSA Provider: Google Gemini
Supports Gemini 2.0 Flash, 2.5 Pro, and all Google AI models.
Authenticates via models.list() and discovers available models dynamically.
"""

import time
from typing import List, Dict
from providers.base import BaseProvider, StandardResponse, ModelInfo
from providers.pricing import GEMINI_PRICING, classify_tier


class GeminiProvider(BaseProvider):

    def __init__(self):
        self._client = None
        self._api_key = self._get_env_key("GOOGLE_API_KEY", "GEMINI_API_KEY")
        self._authenticated = False
        self._models = []

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return self._api_key is not None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def authenticate(self) -> bool:
        """Verify credentials by listing models."""
        if not self.is_available():
            print(f"  ✗ Gemini: No API key found")
            return False

        try:
            client = self._get_client()
            # List models as auth check
            models = client.models.list()
            # Consume the iterator to verify it works
            first = next(iter(models), None)
            if first:
                self._authenticated = True
                print(f"  ✓ Gemini: Authenticated")
                return True
            else:
                print(f"  ✗ Gemini: No models returned")
                return False
        except Exception as e:
            print(f"  ✗ Gemini: Auth failed — {e}")
            self._authenticated = False
            return False

    def list_models(self) -> List[ModelInfo]:
        """Fetch available models from Gemini API and match with pricing."""
        if not self._authenticated:
            return []

        try:
            client = self._get_client()
            api_models = client.models.list()

            discovered = []
            seen = set()

            for model in api_models:
                # Model name comes as "models/gemini-2.0-flash" — strip prefix
                model_id = model.name
                if model_id.startswith("models/"):
                    model_id = model_id[len("models/"):]

                if model_id in seen:
                    continue
                seen.add(model_id)

                # Only include models that support generateContent
                methods = getattr(model, 'supported_generation_methods', []) or []
                if methods and 'generateContent' not in methods:
                    continue

                # Match against pricing catalog
                if model_id in GEMINI_PRICING:
                    pricing = GEMINI_PRICING[model_id]
                    discovered.append(ModelInfo(
                        model_id=model_id,
                        provider=self.provider_name,
                        cost_per_1k_input=pricing["cost_per_1k_input"],
                        cost_per_1k_output=pricing["cost_per_1k_output"],
                        tier=pricing["tier"],
                        context_window=pricing.get("context_window", 1048576),
                    ))

            discovered.sort(key=lambda m: m.blended_cost)
            self._models = discovered

            model_names = [m.model_id for m in discovered]
            print(f"  ✓ Gemini: {len(discovered)} models available: {model_names}")
            return discovered

        except Exception as e:
            print(f"  ✗ Gemini: Failed to list models — {e}")
            return []

    def chat(self, messages: List[Dict], model: str,
             max_tokens: int = 200) -> StandardResponse:
        client = self._get_client()
        from google.genai import types
        start = time.time()

        # Convert OpenAI-style messages to Gemini format
        system_instruction = None
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )
            elif msg["role"] == "assistant":
                contents.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        latency = time.time() - start
        content = response.text or ""

        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

        return StandardResponse(
            content=content.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            provider=self.provider_name,
            latency=latency,
        )
