"""
SonarQube Parser

Parses SonarQube analysis results (sonar-issues.json format).
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from .base_parser import BaseParser, Problem


class SonarQubeParser(BaseParser):
    """
    Parser for SonarQube issues export.
    
    Expects a JSON file with the following structure:
    {
        "issues": [
            {
                "key": "issue-id",
                "message": "Issue description",
                "severity": "MAJOR",
                "component": "file-path",
                "type": "CODE_SMELL",
                "line": 42,
                ...
            }
        ]
    }
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize SonarQube parser.
        
        Args:
            config: Optional configuration dict (currently unused)
        """
        super().__init__(config)
    
    def parse(self, file_path: Path) -> List[Problem]:
        """
        Parse SonarQube issues JSON file.
        
        Args:
            file_path: Path to sonar-issues.json
        
        Returns:
            List of Problem objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is malformed or missing required fields
        """
        if not self.validate_file(file_path):
            raise FileNotFoundError(f"SonarQube issues file not found: {file_path}")
        
        try:
            with open(file_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in SonarQube file: {str(e)}")
        
        issues = data.get("issues", [])
        if not isinstance(issues, list):
            raise ValueError("SonarQube JSON must have 'issues' array")
        
        problems = []
        for issue in issues:
            try:
                problems.append(self._parse_issue(issue))
            except Exception as e:
                print(f"Warning: Skipping malformed SonarQube issue: {str(e)}")
                continue
        
        return problems
    
    def _parse_issue(self, issue: Dict[str, Any]) -> Problem:
        """
        Parse a single SonarQube issue into a Problem.
        
        Args:
            issue: Issue dict from SonarQube JSON
        
        Returns:
            Problem object
        """
        # SonarQube severity mapping
        severity = self.normalize_severity(issue.get("severity", "INFO"))
        
        # SonarQube type - just convert to lowercase to match old behavior
        issue_type = issue.get("type", "").lower()
        
        return Problem(
            id=issue["key"],
            source="sonarqube",
            title=issue.get("message", "No message"),
            description=issue.get("message", ""),  # SonarQube doesn't always have detailed descriptions
            severity=severity,
            component=issue.get("component", "unknown"),
            type=issue_type,
            line=issue.get("line"),
            raw_data=issue
        )
    
    def normalize_severity(self, severity: str) -> str:
        """
        Normalize SonarQube severity levels.
        
        SonarQube uses: BLOCKER, CRITICAL, MAJOR, MINOR, INFO
        We normalize to: CRITICAL, HIGH, MEDIUM, LOW, INFO
        """
        severity = severity.upper()
        
        severity_map = {
            "BLOCKER": "CRITICAL",
            "CRITICAL": "CRITICAL",
            "MAJOR": "HIGH",
            "MINOR": "LOW",
            "INFO": "INFO",
        }
        
        return severity_map.get(severity, severity)
    
    def get_tool_name(self) -> str:
        """Get the tool name."""
        return "sonarqube"
    
    def get_expected_filename(self) -> str:
        """Get the expected filename."""
        return "sonar-issues.json"

