#!/usr/bin/env python3

import os
import time
from typing import Dict, Any, Optional
from openai import OpenAI

def get_ai_client(config: Dict[str, Any]) -> OpenAI:
    """Create an OpenAI client configured for OpenRouter."""
    
    return OpenAI(
        base_url=config["ai_providers"]["openrouter"]["api_base"],
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

def query_model(
    client: OpenAI,
    prompt: str,
    model: Optional[str] = None,
    system_context: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Send a single prompt to the AI model and get the response.
    Includes retry logic for transient failures.
    
    Args:
        client: OpenAI client instance
        prompt: The user prompt to send
        model: Optional model override, otherwise uses config default
        system_context: Optional system context message
        config: AI configuration for default model selection
    
    Returns:
        The model's response text
    
    Raises:
        ValueError: If no model is specified
        RuntimeError: If all retry attempts fail
    """
    if config is None:
        config = {}
    
    messages = []
    if system_context:
        messages.append({"role": "system", "content": system_context})
    
    messages.append({"role": "user", "content": prompt})
    
    # Use specified model or default from config
    model_name = model or config.get("ai_providers", {}).get("openrouter", {}).get("models", {}).get("default")
    if not model_name:
        raise ValueError("No model specified and no default model in config")
    
    # Get retry settings from config
    max_retries = config.get("analysis", {}).get("max_retries", 3)
    timeout = config.get("analysis", {}).get("timeout_seconds", 300)
    
    last_error = None
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                timeout=timeout
            )
            
            if not completion.choices:
                raise RuntimeError("AI returned empty response")
            
            response = completion.choices[0].message.content
            if not response:
                raise RuntimeError("AI returned None response")
                
            return response
            
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # Don't retry on certain errors
            if "invalid" in error_msg or "authentication" in error_msg or "api_key" in error_msg:
                raise RuntimeError(f"AI query failed (non-retryable): {str(e)}")
            
            # For retryable errors, wait before retrying
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                print(f"AI query attempt {attempt + 1} failed: {str(e)}")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # Last attempt failed
                raise RuntimeError(f"AI query failed after {max_retries} attempts: {str(last_error)}")