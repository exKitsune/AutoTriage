"""
OpenRouter LLM Provider

Provides access to various LLM models through the OpenRouter API.
"""

import os
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI

from .base_provider import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """
    LLM provider for OpenRouter API.
    
    OpenRouter provides unified access to multiple LLM providers
    (OpenAI, Anthropic, Google, Meta, etc.) through a single API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenRouter provider.
        
        Args:
            config: Configuration dict containing:
                - api_base: OpenRouter API base URL (default: https://openrouter.ai/api/v1)
                - model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
                - backup_model: Optional backup model for fallback
                - max_retries: Number of retry attempts (default: 3)
                - retry_delay_seconds: Delay between full retry cycles (default: 5)
                - timeout_seconds: Request timeout in seconds (default: 300)
        
        Environment Variables:
            OPENROUTER_API_KEY: Required API key for OpenRouter
        """
        super().__init__(config)
        
        # Get OpenRouter-specific config
        self.api_base = config.get("api_base", "https://openrouter.ai/api/v1")
        self.model = config.get("model", "anthropic/claude-3.5-sonnet")
        self.backup_model = config.get("backup_model", None)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay_seconds", 5)
        self.timeout = config.get("timeout_seconds", 300)
        
        # Initialize OpenAI-compatible client
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=api_key
        )
        
        # Log configuration
        if self.backup_model:
            print(f"🤖 LLM configured: {self.model} (backup: {self.backup_model})")
        else:
            print(f"🤖 LLM configured: {self.model} (no backup)")
    
    def query(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send a message conversation to OpenRouter and get a response.
        
        Implements intelligent retry logic with backup model fallback:
        1. Try main model
        2. On rate limit/provider error, try backup model (if configured)
        3. If both fail, wait and retry the entire sequence
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            **kwargs: Additional parameters passed to the API
        
        Returns:
            The model's response text
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        primary_model = model or self.model
        
        last_error = None
        for attempt in range(self.max_retries):
            # Try primary model
            try:
                result = self._query_single_model(primary_model, messages, **kwargs)
                if result:
                    return result
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check for non-retryable errors (authentication, invalid config, etc.)
                if any(keyword in error_msg for keyword in ["invalid", "authentication", "api_key"]):
                    raise RuntimeError(f"OpenRouter query failed (non-retryable): {str(e)}")
                
                # Check if this is a rate limit or provider error
                is_rate_limit = "429" in str(e) or "rate" in error_msg or "limit" in error_msg
                is_provider_error = "provider" in error_msg or "upstream" in error_msg
                
                # Try backup model if we have one and the error is recoverable
                if self.backup_model and (is_rate_limit or is_provider_error):
                    print(f"  ⚠️  Primary model ({primary_model}) unavailable: {str(e)}")
                    print(f"  🔄 Trying backup model: {self.backup_model}")
                    
                    try:
                        result = self._query_single_model(self.backup_model, messages, **kwargs)
                        if result:
                            print(f"  ✅ Backup model succeeded!")
                            return result
                    except Exception as backup_error:
                        print(f"  ⚠️  Backup model also failed: {str(backup_error)}")
                        last_error = backup_error
                
                # If we're not on the last attempt, wait and retry
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay
                    print(f"  ⏳ Retrying full sequence in {wait_time} seconds... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed
                    models_tried = [primary_model]
                    if self.backup_model:
                        models_tried.append(self.backup_model)
                    
                    raise RuntimeError(
                        f"All models failed after {self.max_retries} attempts. "
                        f"Models tried: {', '.join(models_tried)}. "
                        f"Last error: {str(last_error)}"
                    )
        
        # Should never reach here, but just in case
        raise RuntimeError(f"Query failed unexpectedly: {str(last_error)}")
    
    def _query_single_model(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Query a single model without retry logic.
        
        Args:
            model_name: The model to query
            messages: List of message dicts
            **kwargs: Additional parameters
        
        Returns:
            The model's response text
            
        Raises:
            Exception: If the query fails
        """
        completion = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=self.timeout,
            **kwargs
        )
        
        if not completion.choices:
            raise RuntimeError(f"Model {model_name} returned empty response")
        
        response = completion.choices[0].message.content
        if not response:
            raise RuntimeError(f"Model {model_name} returned None response")
            
        return response
    
    def validate_config(self) -> bool:
        """
        Validate OpenRouter configuration.
        
        Returns:
            True if configuration is valid
        """
        # Check API key
        if not os.getenv("OPENROUTER_API_KEY"):
            print("Error: OPENROUTER_API_KEY environment variable not set")
            return False
        
        # Check required config
        if not self.api_base:
            print("Error: api_base not configured")
            return False
        
        if not self.model:
            print("Error: model not configured")
            return False
        
        return True
    
    def get_model_name(self) -> str:
        """Get the OpenRouter model identifier."""
        return self.model

