"""
Tools Module

Auto-discovers and registers all tools from this directory.
Each tool is self-contained with its implementation and metadata.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type

from .base_tool import BaseTool

# Registry of all available tool classes
_TOOL_REGISTRY: Dict[str, Type[BaseTool]] = {}


def _discover_tools():
    """
    Automatically discover all tool classes in this directory.
    
    Looks for classes that extend BaseTool in all .py files
    (except base_tool.py and __init__.py).
    """
    tools_dir = Path(__file__).parent
    
    for tool_file in tools_dir.glob("*.py"):
        # Skip base_tool.py and __init__.py
        if tool_file.name in ["base_tool.py", "__init__.py"]:
            continue
        
        # Import the module
        module_name = f"tools.{tool_file.stem}"
        try:
            module = importlib.import_module(module_name)
            
            # Find all BaseTool subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool:
                    # Register the tool by its name attribute
                    if hasattr(obj, 'name') and obj.name:
                        _TOOL_REGISTRY[obj.name] = obj
        except Exception as e:
            print(f"Warning: Failed to load tool from {tool_file.name}: {str(e)}")


def get_all_tool_classes() -> Dict[str, Type[BaseTool]]:
    """
    Get all registered tool classes.
    
    Returns:
        Dictionary mapping tool names to tool classes
    """
    if not _TOOL_REGISTRY:
        _discover_tools()
    return _TOOL_REGISTRY.copy()


def get_tool_class(tool_name: str) -> Type[BaseTool]:
    """
    Get a specific tool class by name.
    
    Args:
        tool_name: Name of the tool to get
    
    Returns:
        Tool class
        
    Raises:
        KeyError: If tool not found
    """
    if not _TOOL_REGISTRY:
        _discover_tools()
    return _TOOL_REGISTRY[tool_name]


def get_tool(tool_name: str, workspace_root: Path = None, input_dir: Path = None) -> BaseTool:
    """
    Get an instance of a specific tool by name.
    
    Args:
        tool_name: Name of the tool to get
        workspace_root: Workspace root path (optional for some tools)
        input_dir: Input directory path (optional for some tools)
    
    Returns:
        Tool instance
        
    Raises:
        KeyError: If tool not found
    """
    if not _TOOL_REGISTRY:
        _discover_tools()
    
    tool_class = _TOOL_REGISTRY[tool_name]
    
    # Use dummy paths if not provided
    if workspace_root is None:
        workspace_root = Path(".")
    if input_dir is None:
        input_dir = Path(".")
    
    return tool_class(workspace_root, input_dir)


def get_all_tool_metadata() -> List[Dict]:
    """
    Get metadata for all tools (for prompt generation).
    
    Returns:
        List of tool metadata dictionaries
    """
    if not _TOOL_REGISTRY:
        _discover_tools()
    
    # Create dummy instances to get metadata
    # We use None for paths since we only need metadata
    metadata_list = []
    for tool_class in _TOOL_REGISTRY.values():
        try:
            # Create a mock instance just to get metadata
            # We'll handle the AttributeError from None paths
            try:
                tool = tool_class(Path("."), Path("."))
            except:
                # If initialization fails, try to get metadata directly from class
                metadata = {
                    "name": tool_class.name,
                    "description": tool_class.description,
                    "parameters": tool_class.parameters,
                    "returns": tool_class.returns,
                    "requirements": tool_class.requirements,
                    "example": tool_class.example
                }
                metadata_list.append(metadata)
                continue
            
            metadata_list.append(tool.get_metadata())
        except Exception as e:
            print(f"Warning: Failed to get metadata for {tool_class.name}: {str(e)}")
    
    return metadata_list


# Auto-discover tools on import
_discover_tools()

__all__ = [
    "BaseTool",
    "get_all_tool_classes",
    "get_tool_class",
    "get_tool",
    "get_all_tool_metadata",
]

