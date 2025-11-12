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
        "investigation_summary": {
            "type": "string",
            "description": "Brief summary of what you investigated and how you reached your conclusion (e.g., 'Searched for imports, checked SBOM, examined usage patterns')",
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
        },
        "verification_steps": {
            "type": "array",
            "description": "Steps the user can take to independently verify your findings (e.g., 'grep for import statements', 'check requirements.txt', 'run tool X')",
            "required": True
        },
        "limitations": {
            "type": "array",
            "description": "What you couldn't check or potential gaps in your analysis (e.g., 'Could not verify runtime behavior', 'Unable to test actual exploit', 'Dynamic imports not checked')",
            "required": False
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
                "real_severity": "medium",
                "explanation": "The vulnerability is real but already mitigated by input validation",
                "investigation_summary": "Checked SBOM to confirm vulnerable version 1.2.3 is present, searched codebase for library usage, found input validation that prevents exploitation in auth.py line 45",
                "evidence": [
                    "CVE-2021-1234 affects version 1.2.3 which is in use",
                    "Input validation in line 45 prevents exploitation",
                    "No direct user input reaches vulnerable function"
                ],
                "recommended_actions": [
                    "Update to version 1.2.5 for official fix",
                    "Continue monitoring for related vulnerabilities",
                    "Add regression test for the mitigation"
                ],
                "verification_steps": [
                    "Run 'grep -r \"import vulnerable_lib\" .' to confirm usage locations",
                    "Check requirements.txt or package.json for version 1.2.3",
                    "Review auth.py line 45 to verify input validation logic",
                    "Test with malicious input to confirm mitigation works"
                ],
                "limitations": [
                    "Could not verify behavior with actual exploit payload",
                    "Dynamic imports or indirect usage not checked",
                    "Runtime configuration may affect mitigation effectiveness"
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

