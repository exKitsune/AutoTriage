"""
Base LLM Provider Interface

Abstract base class that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers must implement this interface to be compatible
    with the AutoTriage analysis system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
    
    @abstractmethod
    def query(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Send a message conversation to the LLM and get a response.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Example: [{"role": "system", "content": "..."}, 
                              {"role": "user", "content": "..."}]
            **kwargs: Additional provider-specific parameters
        
        Returns:
            The LLM's response text
            
        Raises:
            RuntimeError: If the query fails after all retries
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the provider is properly configured.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    def get_model_name(self) -> str:
        """
        Get the name of the model being used.
        
        Returns:
            Model name/identifier string
        """
        return self.config.get("model", "unknown")
    
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.
        
        Returns:
            Provider name string
        """
        return self.__class__.__name__

