"""
🧠 NSA Provider: Pricing Catalog

Built-in pricing data for all supported providers.
Most providers don't expose pricing via API, so we maintain
a comprehensive table here. Updated periodically.

Prices are per 1K tokens. Each model entry includes:
  - cost_per_1k_input: Price for 1K input/prompt tokens
  - cost_per_1k_output: Price for 1K output/completion tokens
  - tier: Suggested tier classification (nano/mini/cortex)
  - context_window: Max context length

Last updated: 2025-06
"""

# ──────────────────────────────────────────────────
# OpenAI Pricing
# ──────────────────────────────────────────────────
OPENAI_PRICING = {
    # GPT-4o family
    "gpt-4o": {
        "cost_per_1k_input": 0.0025,
        "cost_per_1k_output": 0.01,
        "tier": "mini",
        "context_window": 128000,
    },
    "gpt-4o-mini": {
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "tier": "nano",
        "context_window": 128000,
    },
    "gpt-4o-mini-2024-07-18": {
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "tier": "nano",
        "context_window": 128000,
    },
    # GPT-4.1 family
    "gpt-4.1": {
        "cost_per_1k_input": 0.002,
        "cost_per_1k_output": 0.008,
        "tier": "mini",
        "context_window": 1047576,
    },
    "gpt-4.1-mini": {
        "cost_per_1k_input": 0.0004,
        "cost_per_1k_output": 0.0016,
        "tier": "nano",
        "context_window": 1047576,
    },
    "gpt-4.1-nano": {
        "cost_per_1k_input": 0.0001,
        "cost_per_1k_output": 0.0004,
        "tier": "nano",
        "context_window": 1047576,
    },
    # o-series (reasoning)
    "o3-mini": {
        "cost_per_1k_input": 0.0011,
        "cost_per_1k_output": 0.0044,
        "tier": "cortex",
        "context_window": 200000,
    },
    "o3": {
        "cost_per_1k_input": 0.01,
        "cost_per_1k_output": 0.04,
        "tier": "cortex",
        "context_window": 200000,
    },
    "o4-mini": {
        "cost_per_1k_input": 0.0011,
        "cost_per_1k_output": 0.0044,
        "tier": "cortex",
        "context_window": 200000,
    },
}

# ──────────────────────────────────────────────────
# Anthropic Pricing
# ──────────────────────────────────────────────────
ANTHROPIC_PRICING = {
    "claude-3-5-haiku-20241022": {
        "cost_per_1k_input": 0.0008,
        "cost_per_1k_output": 0.004,
        "tier": "nano",
        "context_window": 200000,
    },
    "claude-3-5-sonnet-20241022": {
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "tier": "mini",
        "context_window": 200000,
    },
    "claude-sonnet-4-20250514": {
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "tier": "mini",
        "context_window": 200000,
    },
    "claude-opus-4-20250514": {
        "cost_per_1k_input": 0.015,
        "cost_per_1k_output": 0.075,
        "tier": "cortex",
        "context_window": 200000,
    },
}

# ──────────────────────────────────────────────────
# Google Gemini Pricing
# ──────────────────────────────────────────────────
GEMINI_PRICING = {
    "gemini-2.0-flash": {
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "tier": "nano",
        "context_window": 1048576,
    },
    "gemini-2.0-flash-lite": {
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "tier": "nano",
        "context_window": 1048576,
    },
    "gemini-2.5-flash-preview-05-20": {
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "tier": "nano",
        "context_window": 1048576,
    },
    "gemini-2.5-pro-preview-06-05": {
        "cost_per_1k_input": 0.00125,
        "cost_per_1k_output": 0.01,
        "tier": "cortex",
        "context_window": 1048576,
    },
}

# ──────────────────────────────────────────────────
# AWS Bedrock Pricing (us-east-1, on-demand)
# ──────────────────────────────────────────────────
BEDROCK_PRICING = {
    "anthropic.claude-3-5-haiku-20241022-v1:0": {
        "cost_per_1k_input": 0.0008,
        "cost_per_1k_output": 0.004,
        "tier": "nano",
        "context_window": 200000,
    },
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "tier": "mini",
        "context_window": 200000,
    },
    "anthropic.claude-sonnet-4-20250514-v1:0": {
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "tier": "mini",
        "context_window": 200000,
    },
    "anthropic.claude-opus-4-20250514-v1:0": {
        "cost_per_1k_input": 0.015,
        "cost_per_1k_output": 0.075,
        "tier": "cortex",
        "context_window": 200000,
    },
    "amazon.titan-text-lite-v1": {
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0002,
        "tier": "nano",
        "context_window": 4096,
    },
    "amazon.titan-text-express-v1": {
        "cost_per_1k_input": 0.0002,
        "cost_per_1k_output": 0.0006,
        "tier": "nano",
        "context_window": 8192,
    },
    "meta.llama3-1-70b-instruct-v1:0": {
        "cost_per_1k_input": 0.00099,
        "cost_per_1k_output": 0.00099,
        "tier": "mini",
        "context_window": 128000,
    },
}

# ──────────────────────────────────────────────────
# Master lookup
# ──────────────────────────────────────────────────
PRICING_CATALOG = {
    "openai": OPENAI_PRICING,
    "anthropic": ANTHROPIC_PRICING,
    "gemini": GEMINI_PRICING,
    "bedrock": BEDROCK_PRICING,
}


def get_model_pricing(provider: str, model: str) -> dict:
    """Look up pricing for a specific provider+model."""
    provider_pricing = PRICING_CATALOG.get(provider, {})
    return provider_pricing.get(model, None)


def get_all_models_for_provider(provider: str) -> dict:
    """Get all known models + pricing for a provider."""
    return PRICING_CATALOG.get(provider, {})


def classify_tier(cost_per_1k_input: float) -> str:
    """Auto-classify a model into a tier based on input cost."""
    if cost_per_1k_input <= 0.0005:
        return "nano"
    elif cost_per_1k_input <= 0.005:
        return "mini"
    else:
        return "cortex"
