"""
LLM Provider Module

This module provides a pluggable interface for different LLM providers.
Users can easily swap between OpenRouter, OpenAI, Anthropic, Azure, etc.
"""

from .base_provider import BaseLLMProvider
from .openrouter_provider import OpenRouterProvider

__all__ = [
    "BaseLLMProvider",
    "OpenRouterProvider",
]

