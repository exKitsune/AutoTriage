"""
Parser Module

This module provides a pluggable interface for parsing different security
and code quality tool outputs.

Users can easily add custom parsers for new tools by implementing the
BaseParser interface.
"""

from .base_parser import BaseParser, Problem
from .sonarqube_parser import SonarQubeParser
from .dependency_check_parser import DependencyCheckParser
from .cyclonedx_parser import CycloneDXParser

__all__ = [
    "BaseParser",
    "Problem",
    "SonarQubeParser",
    "DependencyCheckParser",
    "CycloneDXParser",
]

