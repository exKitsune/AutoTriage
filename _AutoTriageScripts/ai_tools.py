#!/usr/bin/env python3

import os
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
    
    Args:
        client: OpenAI client instance
        prompt: The user prompt to send
        model: Optional model override, otherwise uses config default
        system_context: Optional system context message
        config: AI configuration for default model selection
    
    Returns:
        The model's response text
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
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        raise RuntimeError(f"AI query failed: {str(e)}")