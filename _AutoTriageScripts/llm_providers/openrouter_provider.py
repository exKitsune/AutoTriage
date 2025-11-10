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
                - max_retries: Number of retry attempts (default: 3)
                - timeout_seconds: Request timeout in seconds (default: 300)
        
        Environment Variables:
            OPENROUTER_API_KEY: Required API key for OpenRouter
        """
        super().__init__(config)
        
        # Get OpenRouter-specific config
        self.api_base = config.get("api_base", "https://openrouter.ai/api/v1")
        self.model = config.get("model", "anthropic/claude-3.5-sonnet")
        self.max_retries = config.get("max_retries", 3)
        self.timeout = config.get("timeout_seconds", 300)
        
        # Initialize OpenAI-compatible client
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=api_key
        )
    
    def query(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send a message conversation to OpenRouter and get a response.
        
        Includes retry logic with exponential backoff for transient failures.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            **kwargs: Additional parameters passed to the API
        
        Returns:
            The model's response text
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        model_name = model or self.model
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if not completion.choices:
                    raise RuntimeError("LLM returned empty response")
                
                response = completion.choices[0].message.content
                if not response:
                    raise RuntimeError("LLM returned None response")
                    
                return response
                
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Don't retry on certain errors
                if any(keyword in error_msg for keyword in ["invalid", "authentication", "api_key"]):
                    raise RuntimeError(f"OpenRouter query failed (non-retryable): {str(e)}")
                
                # For retryable errors, wait before retrying
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                    print(f"OpenRouter query attempt {attempt + 1} failed: {str(e)}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed
                    raise RuntimeError(
                        f"OpenRouter query failed after {self.max_retries} attempts: {str(last_error)}"
                    )
    
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

