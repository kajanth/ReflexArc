"""
🧠 NSA Provider Package

Multi-provider model routing for the Neuro-Synthetic Orchestrator.
Supports OpenAI, Anthropic, Gemini, and AWS Bedrock with
cost-weighted dynamic selection.
"""

from providers.base import BaseProvider, StandardResponse, ModelInfo
from providers.router import ModelRouter

__all__ = ["BaseProvider", "StandardResponse", "ModelInfo", "ModelRouter"]
