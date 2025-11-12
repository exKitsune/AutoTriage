#!/usr/bin/env python3
"""
LLM Client Module

This module provides a convenient interface for creating and using LLM providers.
It acts as a factory for different provider implementations.
"""

import os
from typing import Dict, Any, Optional, List

from llm_providers import BaseLLMProvider, OpenRouterProvider


# Registry of available providers
PROVIDER_REGISTRY = {
    "openrouter": OpenRouterProvider,
    # Add more providers here as they are implemented:
    # "openai": OpenAIProvider,
    # "anthropic": AnthropicProvider,
    # "azure": AzureOpenAIProvider,
}


def get_ai_client(config: Dict[str, Any]) -> BaseLLMProvider:
    """
    Create an LLM provider client based on configuration.
    
    This is a factory function that creates the appropriate provider
    based on the config. Currently defaults to OpenRouter.
    
    Args:
        config: Configuration dictionary containing:
            - ai_providers: Dict with provider configurations
            
    Returns:
        An instance of BaseLLMProvider
        
    Raises:
        ValueError: If provider is not configured or unknown
    
    Example config:
        {
            "ai_providers": {
                "openrouter": {
                    "api_base": "https://openrouter.ai/api/v1",
                    "models": {
                        "default": "anthropic/claude-3.5-sonnet"
                    }
                }
            },
            "analysis": {
                "max_retries": 3,
                "timeout_seconds": 300
            }
        }
    """
    # Determine which provider to use
    # For now, we default to OpenRouter if configured
    ai_providers = config.get("ai_providers", {})
    
    if "openrouter" in ai_providers:
        provider_config = ai_providers["openrouter"].copy()
        
        # Merge analysis settings into provider config
        if "analysis" in config:
            provider_config.update({
                "max_retries": config["analysis"].get("max_retries", 3),
                "retry_delay_seconds": config["analysis"].get("retry_delay_seconds", 5),
                "timeout_seconds": config["analysis"].get("timeout_seconds", 300),
            })
        
        # Get models from nested structure
        if "models" in provider_config:
            if "default" in provider_config["models"]:
                provider_config["model"] = provider_config["models"]["default"]
            if "backup" in provider_config["models"]:
                provider_config["backup_model"] = provider_config["models"]["backup"]
        
        provider = OpenRouterProvider(provider_config)
        
        if not provider.validate_config():
            raise ValueError("OpenRouter provider configuration is invalid")
        
        return provider
    
    # Future: Check for other providers
    # elif "openai" in ai_providers:
    #     return OpenAIProvider(ai_providers["openai"])
    
    raise ValueError("No LLM provider configured. Please configure a provider in ai_config.json")


def query_model(
    client: BaseLLMProvider,
    prompt: str = None,
    model: Optional[str] = None,
    system_context: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    messages: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Send a prompt or message history to the LLM and get the response.
    
    This is a convenience wrapper that maintains backward compatibility
    with the old interface while using the new provider system.
    
    Args:
        client: LLM provider instance
        prompt: The user prompt to send (legacy single-turn mode)
        model: Optional model override
        system_context: Optional system context message (legacy single-turn mode)
        config: AI configuration (currently unused, kept for compatibility)
        messages: Optional full message history for multi-turn conversations
    
    Returns:
        The model's response text
    
    Raises:
        RuntimeError: If the query fails
    """
    # Build messages if not provided
    if messages is None:
        messages = []
        if system_context:
            messages.append({"role": "system", "content": system_context})
        
        if prompt:
            messages.append({"role": "user", "content": prompt})
    
    # Use the provider's query method
    return client.query(messages=messages, model=model)
