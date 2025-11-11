#!/usr/bin/env python3
"""
Read File Lines Tool

Reads a specific range of lines from a file (useful for large files).
"""

from pathlib import Path
from typing import Dict, Any

from .base_tool import BaseTool


class ReadFileLinesTool(BaseTool):
    """Tool for reading specific line ranges from files."""
    
    # Tool metadata
    name = "read_file_lines"
    description = "Read a specific range of lines from a file (useful for large files)"
    
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Path to the file relative to workspace root",
            "required": True
        },
        "start_line": {
            "type": "integer",
            "description": "Starting line number (1-indexed)",
            "required": True
        },
        "end_line": {
            "type": "integer",
            "description": "Ending line number (inclusive)",
            "required": True
        }
    }
    
    returns = {
        "success": "boolean",
        "file_path": "string",
        "start_line": "integer",
        "end_line": "integer",
        "content": "string - the requested lines",
        "total_lines": "integer - total lines in file",
        "error": "string"
    }
    
    requirements = []
    
    example = {
        "call": {
            "tool": "read_file_lines",
            "parameters": {
                "file_path": "container_security/vulnerable/Dockerfile",
                "start_line": 1,
                "end_line": 10
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific range of lines from a file."""
        file_path = params.get("file_path")
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        
        if not file_path or start_line is None or end_line is None:
            return {
                "success": False,
                "error": "file_path, start_line, and end_line parameters required"
            }
        
        # Strip SonarQube project prefix
        if ':' in file_path and ('/' in file_path or '\\' in file_path):
            file_path = file_path.split(':', 1)[1]
        
        try:
            full_path = self.workspace_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "file_path": file_path,
                    "error": "File not found"
                }
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            
            # Convert to 0-indexed for Python
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)
            
            selected_lines = all_lines[start_idx:end_idx]
            content = ''.join(selected_lines)
            
            return {
                "success": True,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "content": content,
                "total_lines": total_lines
            }
        
        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e)
            }

