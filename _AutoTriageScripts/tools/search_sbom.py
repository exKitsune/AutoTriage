#!/usr/bin/env python3
"""
Search SBOM Tool

Searches the SBOM (Software Bill of Materials) for package information.
Requires CycloneDX SBOM file to be present.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .base_tool import BaseTool


class SearchSBOMTool(BaseTool):
    """Tool for searching the SBOM for package information."""
    
    # Tool metadata
    name = "search_sbom"
    description = "Search the SBOM (Software Bill of Materials) for package information"
    
    parameters = {
        "package_name": {
            "type": "string",
            "description": "Name of package to search for (case-insensitive)",
            "required": True
        }
    }
    
    returns = {
        "success": "boolean",
        "package_name": "string",
        "found": "boolean - whether package was found in SBOM",
        "component": "object - package details if found",
        "error": "string"
    }
    
    requirements = [
        {
            "type": "file_exists",
            "path": "{input_dir}/sbom/sbom.json",
            "description": "CycloneDX SBOM file must be present"
        }
    ]
    
    example = {
        "call": {
            "tool": "search_sbom",
            "parameters": {
                "package_name": "PyYAML"
            }
        },
        "response": {
            "success": True,
            "package_name": "PyYAML",
            "found": True,
            "component": {
                "name": "PyYAML",
                "version": "5.3.1",
                "purl": "pkg:pypi/pyyaml@5.3.1",
                "licenses": ["MIT"]
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

