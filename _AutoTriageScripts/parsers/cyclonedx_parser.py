"""
CycloneDX SBOM Parser

Parses CycloneDX Software Bill of Materials (SBOM) files.
Can extract vulnerabilities if present in the SBOM.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base_parser import BaseParser, Problem


class CycloneDXParser(BaseParser):
    """
    Parser for CycloneDX SBOM files (JSON format).
    
    CycloneDX is a standard format for Software Bill of Materials (SBOM).
    This parser can extract:
    - Vulnerabilities (if present in SBOM)
    - Component inventory (optional)
    
    Expects a JSON file with the following structure:
    {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4" or "1.5" or "1.6",
        "components": [...],
        "vulnerabilities": [...]  // Optional
    }
    
    Configuration:
        - parse_components: If True, also create informational problems for
                          all components (dependency inventory). Default: False
        - min_vulnerability_severity: Only parse vulnerabilities at or above
                                     this severity. Default: "LOW"
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize CycloneDX parser.
        
        Args:
            config: Optional configuration dict:
                - parse_components: Bool, parse all components as INFO items
                - min_vulnerability_severity: Str, minimum severity to include
        """
        super().__init__(config)
        self.parse_components = self.config.get("parse_components", False)
        self.min_severity = self.config.get("min_vulnerability_severity", "LOW")
    
    def parse(self, file_path: Path) -> List[Problem]:
        """
        Parse CycloneDX SBOM JSON file.
        
        Args:
            file_path: Path to SBOM JSON file (sbom.json)
        
        Returns:
            List of Problem objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is malformed or not a valid CycloneDX SBOM
        """
        if not self.validate_file(file_path):
            raise FileNotFoundError(f"CycloneDX SBOM file not found: {file_path}")
        
        try:
            with open(file_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in CycloneDX SBOM: {str(e)}")
        
        # Validate it's a CycloneDX SBOM
        if data.get("bomFormat") != "CycloneDX":
            raise ValueError("File is not a valid CycloneDX SBOM (missing bomFormat)")
        
        problems = []
        
        # Parse vulnerabilities if present
        vulnerabilities = data.get("vulnerabilities", [])
        if vulnerabilities:
            for vuln in vulnerabilities:
                try:
                    problem = self._parse_vulnerability(vuln, data.get("components", []))
                    if problem:  # May be filtered by severity
                        problems.append(problem)
                except Exception as e:
                    print(f"Warning: Skipping malformed vulnerability: {str(e)}")
                    continue
        
        # Optionally parse components as informational items
        if self.parse_components:
            components = data.get("components", [])
            for component in components:
                try:
                    problems.append(self._parse_component(component))
                except Exception as e:
                    print(f"Warning: Skipping malformed component: {str(e)}")
                    continue
        
        return problems
    
    def _parse_vulnerability(
        self, 
        vuln: Dict[str, Any], 
        components: List[Dict[str, Any]]
    ) -> Optional[Problem]:
        """
        Parse a vulnerability from the SBOM.
        
        Args:
            vuln: Vulnerability dict from CycloneDX
            components: List of components to find affected component
        
        Returns:
            Problem object or None if filtered by severity
        """
        vuln_id = vuln.get("id", "UNKNOWN-VULN")
        
        # Get severity from ratings
        severity = "UNKNOWN"
        if "ratings" in vuln and vuln["ratings"]:
            # Use the first rating's severity
            severity = vuln["ratings"][0].get("severity", "UNKNOWN")
        
        # Normalize severity
        normalized_severity = self.normalize_severity(severity)
        
        # Filter by minimum severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        min_order = severity_order.get(self.min_severity, 99)
        vuln_order = severity_order.get(normalized_severity, 99)
        
        if vuln_order > min_order:
            return None  # Skip vulnerabilities below minimum severity
        
        # Find affected component
        affected_component = "unknown-component"
        affects = vuln.get("affects", [])
        if affects:
            # Get the component reference
            ref = affects[0].get("ref", "")
            # Try to find the component by bom-ref
            for comp in components:
                if comp.get("bom-ref") == ref:
                    affected_component = f"{comp.get('name', 'unknown')}@{comp.get('version', '')}"
                    break
        
        # Build description
        description = vuln.get("description", "")
        
        # Add CWE information if available
        cwes = vuln.get("cwes", [])
        if cwes:
            cwe_str = ", ".join([str(cwe) for cwe in cwes])
            description = f"CWEs: {cwe_str}\n{description}" if description else f"CWEs: {cwe_str}"
        
        # Create title
        title = f"Vulnerability in {affected_component}: {vuln_id}"
        
        return Problem(
            id=vuln_id,
            source="cyclonedx",
            title=title,
            description=description,
            severity=normalized_severity,
            component=affected_component,
            type="vulnerability",
            line=None,  # SBOMs don't have line numbers
            raw_data={
                "vulnerability": vuln,
                "source_type": "sbom"
            }
        )
    
    def _parse_component(self, component: Dict[str, Any]) -> Problem:
        """
        Parse a component as an informational problem.
        
        Args:
            component: Component dict from CycloneDX
        
        Returns:
            Problem object with INFO severity
        """
        name = component.get("name", "unknown")
        version = component.get("version", "unknown")
        comp_type = component.get("type", "library")
        purl = component.get("purl", "")
        
        comp_id = f"{name}@{version}"
        title = f"Component: {name} {version}"
        description = f"Type: {comp_type}\nPackage URL: {purl}" if purl else f"Type: {comp_type}"
        
        return Problem(
            id=comp_id,
            source="cyclonedx",
            title=title,
            description=description,
            severity="INFO",
            component=comp_id,
            type="component-inventory",
            line=None,
            raw_data=component
        )
    
    def normalize_severity(self, severity: str) -> str:
        """
        Normalize CycloneDX severity levels.
        
        CycloneDX uses: critical, high, medium, low, info, none, unknown
        We normalize to: CRITICAL, HIGH, MEDIUM, LOW, INFO
        """
        severity = severity.upper()
        
        severity_map = {
            "CRITICAL": "CRITICAL",
            "HIGH": "HIGH",
            "MEDIUM": "MEDIUM",
            "MODERATE": "MEDIUM",
            "LOW": "LOW",
            "INFO": "INFO",
            "INFORMATIONAL": "INFO",
            "NONE": "INFO",
            "UNKNOWN": "LOW",  # Conservative: treat unknown as LOW
        }
        
        return severity_map.get(severity, "LOW")
    
    def get_tool_name(self) -> str:
        """Get the tool name."""
        return "cyclonedx"
    
    def get_expected_filename(self) -> str:
        """Get the expected filename."""
        return "sbom.json"

