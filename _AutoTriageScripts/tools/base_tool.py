#!/usr/bin/env python3
"""
Base Tool Class

All tools must extend this base class and implement the required methods.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Each tool is self-contained with:
    - Metadata (name, description, parameters)
    - Requirements (files, executables)
    - Implementation
    - Examples
    """
    
    # Metadata - MUST be defined by subclasses
    name: str = None
    description: str = None
    parameters: Dict[str, Dict[str, Any]] = {}
    returns: Dict[str, str] = {}
    requirements: List[Dict[str, Any]] = []
    example: Dict[str, Any] = {}
    
    def __init__(self, workspace_root: Path, input_dir: Path):
        """
        Initialize the tool with workspace paths.
        
        Args:
            workspace_root: Root directory of the workspace being analyzed
            input_dir: Directory containing analysis inputs (SBOM, etc.)
        """
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        
        # Validate that subclass defined required metadata
        if self.name is None:
            raise ValueError(f"{self.__class__.__name__} must define 'name' class attribute")
        if self.description is None:
            raise ValueError(f"{self.__class__.__name__} must define 'description' class attribute")
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Dictionary of parameters for the tool
        
        Returns:
            Dictionary with tool results, always includes 'success' key
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata for prompt generation.
        
        Returns:
            Dictionary with tool definition
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns,
            "requirements": self.requirements,
            "example": self.example
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate that required parameters are present.
        
        Args:
            params: Parameters to validate
        
        Returns:
            True if valid, False otherwise
        """
        for param_name, param_info in self.parameters.items():
            if param_info.get("required", False):
                if param_name not in params:
                    return False
        return True
    
    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
    
    def __repr__(self) -> str:
        return self.__str__()

