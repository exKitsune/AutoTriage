#!/usr/bin/env python3
"""
Helper to format tool definitions for LLM prompts.
Uses the modular tool system from the tools/ directory.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from tool_availability import ToolAvailabilityChecker
from tools import get_all_tool_metadata


def format_tools_for_prompt(
    workspace_root: Optional[Path] = None,
    input_dir: Optional[Path] = None
) -> str:
    """
    Load tools from the modular tool system and format them for LLM consumption.
    Only includes tools whose requirements are met.
    
    Args:
        workspace_root: Root directory of workspace (for checking tool availability)
        input_dir: Directory containing analysis inputs like SBOM (for checking tool availability)
    
    Returns:
        Formatted string with available tools documentation
    """
    # Get all tool metadata from modular tool system
    all_tools = get_all_tool_metadata()
    
    # Filter tools based on availability
    if workspace_root and input_dir:
        checker = ToolAvailabilityChecker(workspace_root, input_dir)
        available_tools = checker.get_available_tools(all_tools)
    else:
        # No filtering if paths not provided (backwards compatibility)
        available_tools = all_tools
    
    sections = []
    
    # Tool call format instructions
    sections.append("=" * 60)
    sections.append("TOOL CALLING FORMAT")
    sections.append("=" * 60)
    sections.append("\nTo call a tool, respond with a JSON object in this format:")
    sections.append(json.dumps({
        "tool": "tool_name",
        "parameters": {
            "param1": "value1",
            "param2": "value2"
        }
    }, indent=2))
    sections.append("\nExample:")
    sections.append('{"tool": "read_file", "parameters": {"file_path": "app.py"}}')
    sections.append("")
    
    # Available tools
    sections.append("=" * 60)
    sections.append("AVAILABLE TOOLS")
    sections.append("=" * 60)
    sections.append("")
    
    for tool in available_tools:
        sections.append(f"## {tool['name']}")
        sections.append(f"{tool['description']}\n")
        
        # Parameters
        sections.append("Parameters:")
        for param_name, param_info in tool["parameters"].items():
            required = " (REQUIRED)" if param_info.get("required") else " (optional)"
            default_val = f" [default: {param_info['default']}]" if "default" in param_info else ""
            sections.append(f"  - {param_name}{required}{default_val}")
            sections.append(f"    Type: {param_info['type']}")
            sections.append(f"    {param_info['description']}")
        sections.append("")
        
        # Example call
        if "example" in tool and "call" in tool["example"]:
            sections.append("Example call:")
            sections.append(json.dumps(tool["example"]["call"], indent=2))
            sections.append("")
        
        sections.append("-" * 40)
        sections.append("")
    
    # Important notes
    sections.append("=" * 60)
    sections.append("IMPORTANT NOTES")
    sections.append("=" * 60)
    important_notes = [
        "Always respond with ONLY a JSON object containing 'tool' and 'parameters'. No other text.",
        "Use provide_analysis when you have enough information to make a determination.",
        "Investigate thoroughly before providing analysis - check code, search for usage, examine configurations.",
        "For vulnerabilities, always check if the vulnerable package is actually used and how it's used.",
        "For false positives, provide clear evidence from the codebase.",
        "File paths are relative to the workspace root.",
        "Search operations support regex patterns."
    ]
    for note in important_notes:
        sections.append(f"• {note}")
    sections.append("")
    
    return "\n".join(sections)


def get_tool_summary() -> Dict[str, str]:
    """Get a brief summary of each tool (one line per tool)."""
    all_tools = get_all_tool_metadata()
    return {tool["name"]: tool["description"] for tool in all_tools}


if __name__ == "__main__":
    # Test the formatting
    print(format_tools_for_prompt())
