#!/usr/bin/env python3
"""
Tool Availability Checker

Determines which tools are available based on their requirements.
Prevents the LLM from trying to use tools that can't function.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Set


class ToolAvailabilityChecker:
    """
    Checks tool requirements and filters available tools.
    
    Tools can have requirements like:
    - File existence (e.g., SBOM file must exist)
    - Executable availability (e.g., grep, git)
    - Configuration settings
    """
    
    def __init__(self, workspace_root: Path, input_dir: Path):
        """
        Initialize the availability checker.
        
        Args:
            workspace_root: Root directory of the workspace being analyzed
            input_dir: Directory containing analysis inputs (SBOM, etc.)
        """
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        
        # Cache of checked requirements
        self._requirement_cache = {}
    
    def check_file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path relative to input_dir or workspace_root
                      Can use {input_dir} or {workspace_root} placeholders
        
        Returns:
            True if file exists, False otherwise
        """
        # Replace placeholders with actual paths
        if "{input_dir}" in file_path:
            # Replace placeholder and check directly
            resolved_path = file_path.replace("{input_dir}", str(self.input_dir))
            return Path(resolved_path).exists()
        
        if "{workspace_root}" in file_path:
            # Replace placeholder and check directly
            resolved_path = file_path.replace("{workspace_root}", str(self.workspace_root))
            return Path(resolved_path).exists()
        
        # No placeholders - try relative paths
        path = Path(file_path)
        
        if path.is_absolute():
            return path.exists()
        
        # Try relative to input_dir first
        input_path = self.input_dir / path
        if input_path.exists():
            return True
        
        # Then try relative to workspace_root
        workspace_path = self.workspace_root / path
        if workspace_path.exists():
            return True
        
        return False
    
    def check_requirement(self, requirement: Dict[str, Any]) -> bool:
        """
        Check if a single requirement is met.
        
        Args:
            requirement: Requirement dict with 'type' and type-specific fields
        
        Returns:
            True if requirement is met, False otherwise
        """
        req_type = requirement.get("type")
        
        if req_type == "file_exists":
            file_path = requirement.get("path", "")
            return self.check_file_exists(file_path)
        
        elif req_type == "executable":
            # Check if executable is available in PATH
            import shutil
            executable = requirement.get("name", "")
            return shutil.which(executable) is not None
        
        elif req_type == "optional":
            # Optional requirements always pass (tool works better with it but doesn't need it)
            return True
        
        else:
            # Unknown requirement type - fail safe (don't include tool)
            print(f"Warning: Unknown requirement type '{req_type}'")
            return False
    
    def check_tool_available(self, tool_def: Dict[str, Any]) -> bool:
        """
        Check if a tool is available based on its requirements.
        
        Args:
            tool_def: Tool definition dict with optional 'requirements' field
        
        Returns:
            True if all requirements are met (or no requirements), False otherwise
        """
        requirements = tool_def.get("requirements", [])
        
        # No requirements = always available
        if not requirements:
            return True
        
        # All requirements must be met
        for req in requirements:
            cache_key = f"{req.get('type')}:{req.get('path', req.get('name', ''))}"
            
            # Check cache first
            if cache_key not in self._requirement_cache:
                self._requirement_cache[cache_key] = self.check_requirement(req)
            
            if not self._requirement_cache[cache_key]:
                return False
        
        return True
    
    def get_available_tools(self, all_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter tools to only those that are available.
        
        Args:
            all_tools: List of all tool definitions
        
        Returns:
            List of available tool definitions
        """
        available = []
        unavailable_tools = []
        
        for tool in all_tools:
            if self.check_tool_available(tool):
                available.append(tool)
            else:
                unavailable_tools.append(tool["name"])
        
        if unavailable_tools:
            print(f"  ℹ️  Tools filtered out (requirements not met): {', '.join(unavailable_tools)}")
        
        return available
    
    def get_unavailable_tool_names(self, all_tools: List[Dict[str, Any]]) -> Set[str]:
        """
        Get names of tools that are NOT available.
        
        Args:
            all_tools: List of all tool definitions
        
        Returns:
            Set of tool names that are unavailable
        """
        unavailable = set()
        
        for tool in all_tools:
            if not self.check_tool_available(tool):
                unavailable.add(tool["name"])
        
        return unavailable


def load_tools_with_requirements() -> List[Dict[str, Any]]:
    """
    Load tool definitions from the modular tool system.
    
    Returns:
        List of tool definition dicts
    """
    from tools import get_all_tool_metadata
    return get_all_tool_metadata()

