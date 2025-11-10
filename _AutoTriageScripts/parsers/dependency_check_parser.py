"""
OWASP Dependency-Check Parser

Parses OWASP Dependency-Check vulnerability reports.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from .base_parser import BaseParser, Problem


class DependencyCheckParser(BaseParser):
    """
    Parser for OWASP Dependency-Check reports.
    
    Expects a JSON file with the following structure:
    {
        "dependencies": [
            {
                "fileName": "package-name",
                "filePath": "/path/to/package",
                "packages": [...],
                "vulnerabilities": [
                    {
                        "name": "CVE-2021-12345",
                        "severity": "HIGH",
                        "description": "...",
                        "cwes": ["CWE-79"],
                        ...
                    }
                ]
            }
        ]
    }
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Dependency-Check parser.
        
        Args:
            config: Optional configuration dict (currently unused)
        """
        super().__init__(config)
    
    def parse(self, file_path: Path) -> List[Problem]:
        """
        Parse Dependency-Check report JSON file.
        
        Args:
            file_path: Path to dependency-check-report.json
        
        Returns:
            List of Problem objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is malformed or missing required fields
        """
        if not self.validate_file(file_path):
            raise FileNotFoundError(f"Dependency-Check report not found: {file_path}")
        
        try:
            with open(file_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Dependency-Check file: {str(e)}")
        
        dependencies = data.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError("Dependency-Check JSON must have 'dependencies' array")
        
        problems = []
        for dependency in dependencies:
            try:
                problems.extend(self._parse_dependency(dependency))
            except Exception as e:
                print(f"Warning: Skipping malformed dependency: {str(e)}")
                continue
        
        return problems
    
    def _parse_dependency(self, dependency: Dict[str, Any]) -> List[Problem]:
        """
        Parse vulnerabilities from a single dependency.
        
        Args:
            dependency: Dependency dict from Dependency-Check JSON
        
        Returns:
            List of Problem objects (one per vulnerability)
        """
        problems = []
        vulnerabilities = dependency.get("vulnerabilities", [])
        
        for vuln in vulnerabilities:
            try:
                problems.append(self._parse_vulnerability(dependency, vuln))
            except Exception as e:
                print(f"Warning: Skipping malformed vulnerability: {str(e)}")
                continue
        
        return problems
    
    def _parse_vulnerability(self, dependency: Dict[str, Any], vuln: Dict[str, Any]) -> Problem:
        """
        Parse a single vulnerability into a Problem.
        
        Args:
            dependency: Parent dependency object
            vuln: Vulnerability dict
        
        Returns:
            Problem object
        """
        # Build description with CWE information if available
        description = vuln.get("description", "")
        if vuln.get("cwes"):
            cwe_list = ", ".join(vuln["cwes"])
            description = f"CWEs: {cwe_list}\n{description}"
        
        # Normalize severity
        severity = self.normalize_severity(vuln.get("severity", "UNKNOWN"))
        
        # Create a descriptive title
        cve_id = vuln.get("name", "UNKNOWN-CVE")
        dep_name = dependency.get("fileName", "unknown-dependency")
        title = f"Vulnerability in {dep_name}: {cve_id}"
        
        return Problem(
            id=cve_id,  # Usually a CVE ID
            source="dependency-check",
            title=title,
            description=description,
            severity=severity,
            component=dep_name,
            type="vulnerability",
            line=None,  # Dependency issues don't have line numbers
            raw_data={
                "vulnerability": vuln,
                "dependency": {
                    "fileName": dependency.get("fileName"),
                    "filePath": dependency.get("filePath"),
                    "packages": dependency.get("packages", [])
                }
            }
        )
    
    def normalize_severity(self, severity: str) -> str:
        """
        Normalize Dependency-Check severity levels.
        
        Dependency-Check uses: CRITICAL, HIGH, MEDIUM, LOW
        These already match our standard format.
        """
        severity = severity.upper()
        
        # Dependency-Check already uses standard severity levels
        # but we'll include the mapping for clarity
        severity_map = {
            "CRITICAL": "CRITICAL",
            "HIGH": "HIGH",
            "MEDIUM": "MEDIUM",
            "MODERATE": "MEDIUM",
            "LOW": "LOW",
            "INFO": "INFO",
            "INFORMATIONAL": "INFO",
        }
        
        return severity_map.get(severity, severity)
    
    def get_tool_name(self) -> str:
        """Get the tool name."""
        return "dependency-check"
    
    def get_expected_filename(self) -> str:
        """Get the expected filename."""
        return "dependency-check-report.json"

