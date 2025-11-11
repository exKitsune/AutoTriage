"""
provide_analysis tool - Provides the final analysis of a problem

This is a SPECIAL tool that signals analysis completion and returns the final verdict.
It is not executed like other tools but handled specially by the analysis agent.
"""

from pathlib import Path
from typing import Dict, Any, List

from .base_tool import BaseTool


class ProvideAnalysisTool(BaseTool):
    """Provides the final analysis of a problem."""
    
    # Tool metadata
    name = "provide_analysis"
    description = "Provides the final analysis of a problem. Call this tool when you have gathered enough information to make a determination."
    
    parameters = {
        "is_applicable": {
            "type": "boolean",
            "description": "Whether the reported issue is actually a real problem that needs attention",
            "required": True
        },
        "confidence": {
            "type": "string",
            "description": "Your confidence level in the assessment. Options: 'high', 'medium', 'low'",
            "required": True
        },
        "real_severity": {
            "type": "string",
            "description": "The actual severity if applicable. Options: 'critical', 'high', 'medium', 'low', 'info'",
            "required": True
        },
        "explanation": {
            "type": "string",
            "description": "Clear explanation of your determination",
            "required": True
        },
        "evidence": {
            "type": "array",
            "description": "List of specific evidence that supports your conclusion",
            "required": True
        },
        "recommended_actions": {
            "type": "array",
            "description": "Specific actionable steps to address the issue (or explanation if not applicable)",
            "required": True
        }
    }
    
    returns = {
        "status": "string - 'analysis_complete'"
    }
    
    requirements = []  # No special requirements
    
    example = {
        "call": {
            "tool": "provide_analysis",
            "parameters": {
                "is_applicable": True,
                "confidence": "high",
                "real_severity": "medium",
                "explanation": "The vulnerability is real but already mitigated by input validation",
                "evidence": [
                    "CVE-2021-1234 affects version 1.2.3 which is in use",
                    "Input validation in line 45 prevents exploitation"
                ],
                "recommended_actions": [
                    "Update to version 1.2.5 for official fix",
                    "Continue monitoring for related vulnerabilities"
                ]
            }
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        This tool is special and is not actually executed.
        It's handled directly by the analysis agent to signal completion.
        """
        return {"status": "analysis_complete"}

