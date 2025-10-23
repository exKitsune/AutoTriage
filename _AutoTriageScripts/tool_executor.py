#!/usr/bin/env python3
"""
Tool executor for the agentic analysis system.
Implements all tools defined in tools_definition.json
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


class ToolExecutor:
    """Executes tools requested by the analysis agent."""
    
    def __init__(self, workspace_root: Path, input_dir: Path):
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        
        # Load tool definitions
        tools_file = Path(__file__).parent / "tools_definition.json"
        with open(tools_file) as f:
            tools_data = json.load(f)
            self.tool_definitions = {tool["name"]: tool for tool in tools_data["tools"]}
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return results.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
        
        Returns:
            Dictionary with tool results
        """
        if tool_name not in self.tool_definitions:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        # Route to appropriate tool implementation
        tool_methods = {
            "read_file": self.read_file,
            "read_file_lines": self.read_file_lines,
            "search_code": self.search_code,
            "list_directory": self.list_directory,
            "find_files": self.find_files,
            "search_sbom": self.search_sbom,
            "check_import_usage": self.check_import_usage,
        }
        
        if tool_name in tool_methods:
            try:
                return tool_methods[tool_name](parameters)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Tool execution failed: {str(e)}"
                }
        else:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not implemented"
            }
    
    def read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read the complete contents of a file."""
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path parameter required"}
        
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
    
    def read_file_lines(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific range of lines from a file."""
        file_path = params.get("file_path")
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        
        if not file_path or start_line is None or end_line is None:
            return {
                "success": False,
                "error": "file_path, start_line, and end_line parameters required"
            }
        
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
    
    def search_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
        import re
        
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
    
    def list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def find_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def search_sbom(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search the SBOM for package information."""
        package_name = params.get("package_name")
        
        if not package_name:
            return {"success": False, "error": "package_name parameter required"}
        
        try:
            sbom_file = self.input_dir / "sbom" / "sbom.json"
            
            if not sbom_file.exists():
                return {
                    "success": True,
                    "package_name": package_name,
                    "found": False,
                    "note": "SBOM file not available"
                }
            
            with open(sbom_file) as f:
                sbom_data = json.load(f)
            
            components = sbom_data.get("components", [])
            
            if not components:
                return {
                    "success": True,
                    "package_name": package_name,
                    "found": False,
                    "note": "SBOM contains no components"
                }
            
            # Search for package (case-insensitive)
            package_lower = package_name.lower()
            
            for comp in components:
                comp_name = comp.get("name", "").lower()
                comp_purl = comp.get("purl", "").lower()
                
                if package_lower in comp_name or package_lower in comp_purl:
                    return {
                        "success": True,
                        "package_name": package_name,
                        "found": True,
                        "component": {
                            "name": comp.get("name"),
                            "version": comp.get("version"),
                            "purl": comp.get("purl"),
                            "licenses": comp.get("licenses", []),
                            "type": comp.get("type")
                        }
                    }
            
            return {
                "success": True,
                "package_name": package_name,
                "found": False,
                "note": f"Package not found in SBOM"
            }
        
        except Exception as e:
            return {
                "success": False,
                "package_name": package_name,
                "error": str(e)
            }
    
    def check_import_usage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a Python package is imported anywhere in the codebase."""
        package_name = params.get("package_name")
        
        if not package_name:
            return {"success": False, "error": "package_name parameter required"}
        
        try:
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
                result = self.search_code({
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

