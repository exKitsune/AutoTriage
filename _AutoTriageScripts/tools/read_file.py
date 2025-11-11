#!/usr/bin/env python3
"""
Read File Tool

Reads the complete contents of a file from the workspace.
"""

from pathlib import Path
from typing import Dict, Any

from .base_tool import BaseTool


class ReadFileTool(BaseTool):
    """Tool for reading complete file contents."""
    
    # Tool metadata
    name = "read_file"
    description = "Read the complete contents of a file from the workspace"
    
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Path to the file relative to workspace root (e.g., 'container_security/app/app.py')",
            "required": True
        }
    }
    
    returns = {
        "success": "boolean - whether the file was read successfully",
        "file_path": "string - the file path that was read",
        "content": "string - full file contents",
        "lines": "integer - number of lines in file",
        "error": "string - error message if success is false"
    }
    
    requirements = []  # No requirements - always available
    
    example = {
        "call": {
            "tool": "read_file",
            "parameters": {
                "file_path": "container_security/app/app.py"
            }
        },
        "response": {
            "success": True,
            "file_path": "container_security/app/app.py",
            "content": "from flask import Flask...",
            "lines": 43
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read the complete contents of a file."""
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path parameter required"}
        
        # Strip SonarQube project prefix (e.g., "AutoTriage:path" → "path")
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
                content = f.read()
            
            lines = content.split('\n')
            
            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "lines": len(lines)
            }
        
        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e)
            }

