"""
search_code tool - Search for patterns in codebase using grep
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import re

from .base_tool import BaseTool


class SearchCodeTool(BaseTool):
    """Search for a pattern in the codebase using grep."""
    
    # Tool metadata
    name = "search_code"
    description = "Search for a pattern in the codebase using grep"
    
    parameters = {
        "pattern": {
            "type": "string",
            "description": "Regular expression pattern to search for",
            "required": True
        },
        "file_glob": {
            "type": "string",
            "description": "File pattern to search (e.g., '*.py', '*.js'). Default: '*'",
            "required": False,
            "default": "*"
        },
        "case_sensitive": {
            "type": "boolean",
            "description": "Whether the search should be case-sensitive. Default: false",
            "required": False,
            "default": False
        }
    }
    
    returns = {
        "success": "boolean",
        "pattern": "string",
        "matches": "array of {file, line_number, line_content}",
        "match_count": "integer",
        "error": "string"
    }
    
    requirements = []  # No requirements, grep fallback to Python if not available
    
    example = {
        "call": {
            "tool": "search_code",
            "parameters": {
                "pattern": "def\\s+calculate_",
                "file_glob": "*.py",
                "case_sensitive": False
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for a pattern in the codebase using grep."""
        pattern = params.get("pattern")
        file_glob = params.get("file_glob", "*")
        case_sensitive = params.get("case_sensitive", False)
        
        if not pattern:
            return {"success": False, "error": "pattern parameter required"}
        
        try:
            # Use grep (available on Linux/GitHub Actions)
            cmd = ["grep", "-r", "-n"]  # recursive, line numbers
            
            if not case_sensitive:
                cmd.append("-i")  # case insensitive
            
            cmd.extend(["-E", pattern])  # extended regex
            
            # Add file glob if specified
            if file_glob and file_glob != "*":
                cmd.extend(["--include", file_glob])
            
            # Exclude _AutoTriageScripts directory to avoid searching tool code
            cmd.extend(["--exclude-dir", "_AutoTriageScripts"])
            
            cmd.append(str(self.workspace_root))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            matches = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        # Format: filepath:line_number:content
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            filepath = parts[0]
                            # Make path relative to workspace
                            try:
                                rel_path = Path(filepath).relative_to(self.workspace_root)
                            except ValueError:
                                rel_path = filepath
                            
                            matches.append({
                                "file": str(rel_path),
                                "line_number": int(parts[1]) if parts[1].isdigit() else 0,
                                "line_content": parts[2].strip()
                            })
            
            return {
                "success": True,
                "pattern": pattern,
                "matches": matches,
                "match_count": len(matches)
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "pattern": pattern,
                "error": "Search timed out after 30 seconds"
            }
        except FileNotFoundError:
            # grep not available, fallback to Python
            return self._search_code_python(pattern, file_glob, case_sensitive)
        except Exception as e:
            return {
                "success": False,
                "pattern": pattern,
                "error": str(e)
            }
    
    def _search_code_python(self, pattern: str, file_glob: str, case_sensitive: bool) -> Dict[str, Any]:
        """Fallback Python implementation of code search."""
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            matches = []
            
            # Search in files matching glob
            if file_glob == "*":
                search_pattern = "**/*"
            else:
                search_pattern = f"**/{file_glob}"
            
            for filepath in self.workspace_root.glob(search_pattern):
                if filepath.is_file():
                    # Skip _AutoTriageScripts directory
                    try:
                        rel_path = filepath.relative_to(self.workspace_root)
                        if rel_path.parts[0] == "_AutoTriageScripts":
                            continue
                    except (ValueError, IndexError):
                        pass
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    matches.append({
                                        "file": str(filepath.relative_to(self.workspace_root)),
                                        "line_number": line_num,
                                        "line_content": line.strip()
                                    })
                    except Exception:
                        continue
            
            return {
                "success": True,
                "pattern": pattern,
                "matches": matches,
                "match_count": len(matches)
            }
        
        except Exception as e:
            return {
                "success": False,
                "pattern": pattern,
                "error": f"Python search failed: {str(e)}"
            }

