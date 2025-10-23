#!/usr/bin/env python3
"""
Helper to format tool definitions for LLM prompts.
"""

import json
from pathlib import Path
from typing import Dict, List


def format_tools_for_prompt() -> str:
    """
    Load tools from tools_definition.json and format them for LLM consumption.
    Includes all necessary details: parameters, returns, examples.
    """
    tools_file = Path(__file__).parent / "tools_definition.json"
    with open(tools_file) as f:
        tools_data = json.load(f)
    
    sections = []
    
    # Tool call format instructions
    sections.append("=" * 60)
    sections.append("TOOL CALLING FORMAT")
    sections.append("=" * 60)
    sections.append("\nTo call a tool, respond with a JSON object in this format:")
    sections.append(json.dumps(tools_data["tool_call_format"]["format"], indent=2))
    sections.append("\nExample:")
    sections.append(tools_data["tool_call_format"]["example"])
    sections.append("")
    
    # Available tools
    sections.append("=" * 60)
    sections.append("AVAILABLE TOOLS")
    sections.append("=" * 60)
    sections.append("")
    
    for tool in tools_data["tools"]:
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
    for note in tools_data["important_notes"]:
        sections.append(f"• {note}")
    sections.append("")
    
    return "\n".join(sections)


def get_tool_summary() -> Dict[str, str]:
    """Get a brief summary of each tool (one line per tool)."""
    tools_file = Path(__file__).parent / "tools_definition.json"
    with open(tools_file) as f:
        tools_data = json.load(f)
    
    return {tool["name"]: tool["description"] for tool in tools_data["tools"]}


if __name__ == "__main__":
    # Test the formatting
    print(format_tools_for_prompt())

