"""
Base Parser Interface

Abstract base class and data structures for tool parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class Problem:
    """
    Represents a security or code quality issue from any analysis tool.
    
    This is a normalized format that all parsers must convert their
    tool-specific output into.
    """
    id: str  # Unique identifier for the issue
    source: str  # Tool that found the issue (e.g., 'sonarqube', 'dependency-check')
    title: str  # Short description of the issue
    description: str  # Detailed description
    severity: str  # Severity level (normalized: CRITICAL, HIGH, MEDIUM, LOW, INFO)
    component: str  # Affected component/file
    type: str  # Type of issue (e.g., 'vulnerability', 'code-smell', 'bug')
    line: Optional[int] = None  # Line number if applicable
    raw_data: Optional[Dict[str, Any]] = None  # Original raw data from the tool


class BaseParser(ABC):
    """
    Abstract base class for tool output parsers.
    
    All parsers must implement this interface to be compatible with
    the AutoTriage analysis system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the parser with optional configuration.
        
        Args:
            config: Parser-specific configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[Problem]:
        """
        Parse a tool output file and return a list of problems.
        
        Args:
            file_path: Path to the tool output file
        
        Returns:
            List of Problem objects
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        pass
    
    @abstractmethod
    def get_tool_name(self) -> str:
        """
        Get the name of the tool this parser handles.
        
        Returns:
            Tool name string (e.g., "sonarqube", "dependency-check")
        """
        pass
    
    @abstractmethod
    def get_expected_filename(self) -> str:
        """
        Get the expected filename pattern for this tool's output.
        
        Returns:
            Filename or pattern (e.g., "sonar-issues.json")
        """
        pass
    
    def normalize_severity(self, severity: str) -> str:
        """
        Normalize severity levels to a common format.
        
        Override this method if your tool uses different severity levels.
        
        Args:
            severity: Tool-specific severity level
        
        Returns:
            Normalized severity: CRITICAL, HIGH, MEDIUM, LOW, or INFO
        """
        severity = severity.upper()
        
        # Common mappings
        severity_map = {
            "BLOCKER": "CRITICAL",
            "CRITICAL": "CRITICAL",
            "MAJOR": "HIGH",
            "HIGH": "HIGH",
            "MODERATE": "MEDIUM",
            "MEDIUM": "MEDIUM",
            "MINOR": "LOW",
            "LOW": "LOW",
            "INFO": "INFO",
            "INFORMATIONAL": "INFO",
        }
        
        return severity_map.get(severity, severity)
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that the file exists and is readable.
        
        Args:
            file_path: Path to validate
        
        Returns:
            True if file is valid, False otherwise
        """
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return False
        
        if not file_path.is_file():
            print(f"Error: Path is not a file: {file_path}")
            return False
        
        return True

