"""
🧠 NSA Provider: AWS Bedrock
Supports Claude on Bedrock, Titan, Llama, and all Bedrock models.
Authenticates via STS and discovers available models via list_foundation_models.
"""

import json
import time
from typing import List, Dict
from providers.base import BaseProvider, StandardResponse, ModelInfo
from providers.pricing import BEDROCK_PRICING, classify_tier


class BedrockProvider(BaseProvider):

    def __init__(self, region: str = None):
        self._runtime_client = None
        self._mgmt_client = None
        self._region = region or self._get_env_key("AWS_DEFAULT_REGION") or "us-east-1"
        self._access_key = self._get_env_key("AWS_ACCESS_KEY_ID")
        self._secret_key = self._get_env_key("AWS_SECRET_ACCESS_KEY")
        self._session_token = self._get_env_key("AWS_SESSION_TOKEN")
        self._authenticated = False
        self._models = []

    @property
    def provider_name(self) -> str:
        return "bedrock"

    def is_available(self) -> bool:
        import os
        has_env_keys = self._access_key is not None and self._secret_key is not None
        has_profile = os.path.exists(os.path.expanduser("~/.aws/credentials"))
        return has_env_keys or has_profile

    def _get_runtime_client(self):
        if self._runtime_client is None:
            import boto3
            session_kwargs = {"region_name": self._region}
            if self._access_key and self._secret_key:
                session_kwargs["aws_access_key_id"] = self._access_key
                session_kwargs["aws_secret_access_key"] = self._secret_key
            if self._session_token:
                session_kwargs["aws_session_token"] = self._session_token
            
            self._runtime_client = boto3.client("bedrock-runtime", **session_kwargs)
        return self._runtime_client

    def _get_mgmt_client(self):
        if self._mgmt_client is None:
            import boto3
            session_kwargs = {"region_name": self._region}
            if self._access_key and self._secret_key:
                session_kwargs["aws_access_key_id"] = self._access_key
                session_kwargs["aws_secret_access_key"] = self._secret_key
            if self._session_token:
                session_kwargs["aws_session_token"] = self._session_token
                
            self._mgmt_client = boto3.client("bedrock", **session_kwargs)
        return self._mgmt_client

    def authenticate(self) -> bool:
        """Verify AWS credentials via STS get_caller_identity."""
        if not self.is_available():
            print(f"  ✗ Bedrock: No AWS credentials found")
            return False

        try:
            import boto3
            session_kwargs = {"region_name": self._region}
            if self._access_key and self._secret_key:
                session_kwargs["aws_access_key_id"] = self._access_key
                session_kwargs["aws_secret_access_key"] = self._secret_key
            if self._session_token:
                session_kwargs["aws_session_token"] = self._session_token
                
            sts = boto3.client("sts", **session_kwargs)
            identity = sts.get_caller_identity()
            account = identity.get("Account", "unknown")
            arn = identity.get("Arn", "unknown")
            self._authenticated = True
            print(f"  ✓ Bedrock: Authenticated (account: {account})")
            return True
        except Exception as e:
            print(f"  ✗ Bedrock: Auth failed — {e}")
            self._authenticated = False
            return False

    def list_models(self) -> List[ModelInfo]:
        """Discover available foundation models from Bedrock API."""
        if not self._authenticated:
            return []

        try:
            mgmt = self._get_mgmt_client()
            response = mgmt.list_foundation_models(
                byOutputModality="TEXT",
                byInferenceType="ON_DEMAND",
            )

            discovered = []
            for model in response.get("modelSummaries", []):
                model_id = model.get("modelId", "")

                # Match against our pricing catalog
                if model_id in BEDROCK_PRICING:
                    pricing = BEDROCK_PRICING[model_id]
                    discovered.append(ModelInfo(
                        model_id=model_id,
                        provider=self.provider_name,
                        cost_per_1k_input=pricing["cost_per_1k_input"],
                        cost_per_1k_output=pricing["cost_per_1k_output"],
                        tier=pricing["tier"],
                        context_window=pricing.get("context_window", 4096),
                    ))

            discovered.sort(key=lambda m: m.blended_cost)
            self._models = discovered

            model_names = [m.model_id for m in discovered]
            print(f"  ✓ Bedrock: {len(discovered)} models available: {model_names}")
            return discovered

        except Exception as e:
            print(f"  ✗ Bedrock: Failed to list models — {e}")
            return []

    def chat(self, messages: List[Dict], model: str,
             max_tokens: int = 200) -> StandardResponse:
        client = self._get_runtime_client()
        start = time.time()

        # Convert to Bedrock Converse API format
        system_parts = []
        converse_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_parts.append({"text": msg["content"]})
            else:
                converse_messages.append({
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}],
                })

        if not converse_messages:
            converse_messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        kwargs = {
            "modelId": model,
            "messages": converse_messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
            },
        }
        if system_parts:
            kwargs["system"] = system_parts

        response = client.converse(**kwargs)
        latency = time.time() - start

        content = ""
        output = response.get("output", {})
        message = output.get("message", {})
        for block in message.get("content", []):
            if "text" in block:
                content += block["text"]

        usage = response.get("usage", {})
        prompt_tokens = usage.get("inputTokens", 0)
        completion_tokens = usage.get("outputTokens", 0)

        return StandardResponse(
            content=content.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            provider=self.provider_name,
            latency=latency,
        )
