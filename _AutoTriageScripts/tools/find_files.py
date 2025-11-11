"""
find_files tool - Find files matching a pattern
"""

from pathlib import Path
from typing import Dict, Any, List

from .base_tool import BaseTool


class FindFilesTool(BaseTool):
    """Find files matching a pattern."""
    
    # Tool metadata
    name = "find_files"
    description = "Find files matching a glob pattern"
    
    parameters = {
        "pattern": {
            "type": "string",
            "description": "Glob pattern to match (e.g., '*.py', '**/*.json')",
            "required": True
        },
        "directory": {
            "type": "string",
            "description": "Directory to search in (relative to workspace root). Default: '.'",
            "required": False,
            "default": "."
        }
    }
    
    returns = {
        "success": "boolean",
        "pattern": "string",
        "files": "array of matching file paths",
        "count": "integer",
        "error": "string"
    }
    
    requirements = []  # No special requirements
    
    example = {
        "call": {
            "tool": "find_files",
            "parameters": {
                "pattern": "*.py",
                "directory": "src"
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find files matching a pattern."""
        pattern = params.get("pattern")
        directory = params.get("directory", ".")
        
        if not pattern:
            return {"success": False, "error": "pattern parameter required"}
        
        try:
            search_dir = self.workspace_root / directory
            
            if not search_dir.exists():
                return {
                    "success": False,
                    "pattern": pattern,
                    "error": f"Directory not found: {directory}"
                }
            
            # Use glob to find matching files
            matches = []
            for filepath in search_dir.rglob(pattern):
                if filepath.is_file():
                    rel_path = str(filepath.relative_to(self.workspace_root))
                    matches.append(rel_path)
            
            return {
                "success": True,
                "pattern": pattern,
                "files": sorted(matches),
                "count": len(matches)
            }
        
        except Exception as e:
            return {
                "success": False,
                "pattern": pattern,
                "error": str(e)
            }

