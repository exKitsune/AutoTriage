"""
list_directory tool - List files and directories in a directory
"""

from pathlib import Path
from typing import Dict, Any, List

from .base_tool import BaseTool


class ListDirectoryTool(BaseTool):
    """List files and directories in a directory."""
    
    # Tool metadata
    name = "list_directory"
    description = "List files and directories in a directory"
    
    parameters = {
        "directory": {
            "type": "string",
            "description": "Directory path to list (relative to workspace root). Default: '.'",
            "required": False,
            "default": "."
        },
        "recursive": {
            "type": "boolean",
            "description": "Whether to recursively list subdirectories. Default: false",
            "required": False,
            "default": False
        }
    }
    
    returns = {
        "success": "boolean",
        "directory": "string",
        "files": "array of file paths",
        "directories": "array of directory paths",
        "error": "string"
    }
    
    requirements = []  # No special requirements
    
    example = {
        "call": {
            "tool": "list_directory",
            "parameters": {
                "directory": "src",
                "recursive": False
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List files and directories in a directory."""
        directory = params.get("directory", ".")
        recursive = params.get("recursive", False)
        
        try:
            dir_path = self.workspace_root / directory
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "directory": directory,
                    "error": "Directory not found"
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "directory": directory,
                    "error": "Path is not a directory"
                }
            
            files = []
            directories = []
            
            if recursive:
                for item in dir_path.rglob('*'):
                    rel_path = str(item.relative_to(self.workspace_root))
                    if item.is_file():
                        files.append(rel_path)
                    elif item.is_dir():
                        directories.append(rel_path)
            else:
                for item in dir_path.iterdir():
                    rel_path = str(item.relative_to(self.workspace_root))
                    if item.is_file():
                        files.append(rel_path)
                    elif item.is_dir():
                        directories.append(rel_path)
            
            return {
                "success": True,
                "directory": directory,
                "files": sorted(files),
                "directories": sorted(directories)
            }
        
        except Exception as e:
            return {
                "success": False,
                "directory": directory,
                "error": str(e)
            }

