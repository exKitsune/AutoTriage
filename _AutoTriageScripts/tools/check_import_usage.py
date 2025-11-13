"""
check_import_usage tool - Check if a Python package is imported in the codebase
"""

from pathlib import Path
from typing import Dict, Any, List

from .base_tool import BaseTool


class CheckImportUsageTool(BaseTool):
    """Check if a Python package is imported anywhere in the codebase."""
    
    # Tool metadata
    name = "check_import_usage"
    description = "Check if a Python package is imported anywhere in the codebase (Python-specific: searches for 'import' statements in .py files)"
    
    parameters = {
        "package_name": {
            "type": "string",
            "description": "Name of the Python package to search for",
            "required": True
        }
    }
    
    returns = {
        "success": "boolean",
        "package_name": "string",
        "is_imported": "boolean - whether package is imported anywhere",
        "import_locations": "array of locations where package is imported",
        "import_patterns": "array of actual import statements found",
        "error": "string"
    }
    
    requirements = []  # No special requirements
    
    example = {
        "call": {
            "tool": "check_import_usage",
            "parameters": {
                "package_name": "requests"
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a Python package is imported anywhere in the codebase."""
        package_name = params.get("package_name")
        
        if not package_name:
            return {"success": False, "error": "package_name parameter required"}
        
        try:
            # Import search_code tool dynamically to avoid circular imports
            from . import get_tool
            search_code_tool = get_tool("search_code", self.workspace_root, self.input_dir)
            
            # Search for import patterns
            import_patterns = [
                f"import {package_name}",
                f"from {package_name}",
                f"import {package_name}.",  # submodule imports
            ]
            
            all_locations = []
            all_patterns_found = []
            
            for pattern in import_patterns:
                # Use search_code tool
                result = search_code_tool.execute({
                    "pattern": pattern,
                    "file_glob": "*.py",
                    "case_sensitive": False
                })
                
                if result.get("success") and result.get("matches"):
                    for match in result["matches"]:
                        location = f"{match['file']}:{match['line_number']}"
                        if location not in all_locations:
                            all_locations.append(location)
                            all_patterns_found.append(match['line_content'])
            
            return {
                "success": True,
                "package_name": package_name,
                "is_imported": len(all_locations) > 0,
                "import_locations": all_locations,
                "import_patterns": all_patterns_found
            }
        
        except Exception as e:
            return {
                "success": False,
                "package_name": package_name,
                "error": str(e)
            }

