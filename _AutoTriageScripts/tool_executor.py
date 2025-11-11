#!/usr/bin/env python3
"""
Tool executor for the agentic analysis system.
Uses the modular tool system from the tools/ directory.
"""

from pathlib import Path
from typing import Dict, Any

from tools import get_tool


class ToolExecutor:
    """Executes tools requested by the analysis agent."""
    
    def __init__(self, workspace_root: Path, input_dir: Path):
        self.workspace_root = workspace_root
        self.input_dir = input_dir
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return results.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
        
        Returns:
            Dictionary with tool results
        """
        try:
            # Get the tool instance from the modular tool system
            tool = get_tool(tool_name, self.workspace_root, self.input_dir)
            
            # Execute the tool (tool has access to workspace_root and input_dir via self)
            result = tool.execute(parameters)
            
            return result
        
        except KeyError:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
