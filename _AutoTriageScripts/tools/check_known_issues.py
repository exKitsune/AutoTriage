"""
check_known_issues tool - Check if a problem has already been reviewed by humans

This tool queries the known_issues database to see if humans have already
made a decision about this issue with documented context and reasoning.

IMPORTANT: Call this tool FIRST before any other investigation to avoid
re-analyzing issues that have already been reviewed.
"""

from pathlib import Path
from typing import Dict, Any

from .base_tool import BaseTool


class CheckKnownIssuesTool(BaseTool):
    """Check if a problem has already been reviewed by humans."""
    
    # Tool metadata
    name = "check_known_issues"
    description = "Check if this problem has already been reviewed by humans with documented reasoning. ALWAYS call this FIRST before investigating - it may save significant time and provide valuable context."
    
    parameters = {
        "problem_id": {
            "type": "string",
            "description": "The problem ID to look up (e.g., CVE-2020-14343, sonarqube-key, etc.)",
            "required": True
        }
    }
    
    returns = {
        "success": "boolean - Whether the query was successful",
        "found": "boolean - Whether a human review was found",
        "status": "string - Status if found: not_applicable, accepted_risk, mitigated, wont_fix",
        "human_reasoning": "string - The human's detailed reasoning (if found)",
        "context": "array - Additional context the AI doesn't have access to",
        "evidence": "array - Evidence collected during human review",
        "reviewed_by": "string - Who reviewed this issue",
        "review_date": "string - When it was reviewed",
        "expires": "string - When this review should be re-evaluated (if set)",
        "message": "string - Guidance message"
    }
    
    requirements = []  # No special requirements
    
    example = {
        "call": {
            "tool": "check_known_issues",
            "parameters": {
                "problem_id": "CVE-2020-14343"
            }
        },
        "result_if_found": {
            "success": True,
            "found": True,
            "status": "not_applicable",
            "human_reasoning": "PyYAML is only a transitive dependency...",
            "context": ["Confirmed with DevOps team", "Not in production"],
            "evidence": ["grep -r 'import yaml' found 0 matches"],
            "reviewed_by": "Security Team",
            "review_date": "2025-11-13",
            "message": "Human review found! Use this context in your analysis."
        },
        "result_if_not_found": {
            "success": True,
            "found": False,
            "message": "No human review found. Proceed with normal investigation."
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a problem has been reviewed by humans.
        
        Args:
            params: Dict with 'problem_id' key
        
        Returns:
            Dict with review information if found, or not found message
        """
        problem_id = params.get("problem_id")
        
        if not problem_id:
            return {
                "success": False,
                "error": "problem_id parameter is required"
            }
        
        # Known issues directory is sibling to tools directory
        known_issues_dir = self.workspace_root / "_AutoTriageScripts" / "known_issues"
        
        if not known_issues_dir.exists():
            return {
                "success": True,
                "found": False,
                "message": "Known issues database not initialized. Proceed with normal investigation."
            }
        
        # Try to find the file
        yaml_file = self._find_issue_file(known_issues_dir, problem_id)
        
        if yaml_file is None:
            return {
                "success": True,
                "found": False,
                "message": "No human review found for this issue. Proceed with normal investigation."
            }
        
        # Load and parse the YAML file
        try:
            import yaml
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            
            if not data:
                return {
                    "success": False,
                    "error": f"Known issue file {yaml_file.name} is empty or invalid"
                }
            
            # Build response with all available information
            response = {
                "success": True,
                "found": True,
                "status": data.get("status", "unknown"),
                "human_reasoning": data.get("human_reasoning", "No reasoning provided"),
                "reviewed_by": data.get("reviewed_by", "Unknown"),
                "review_date": data.get("review_date", "Unknown"),
                "message": "✓ Human review found! Read the reasoning carefully and build upon their decision in your analysis."
            }
            
            # Add optional fields if present
            if data.get("context"):
                response["context"] = data["context"]
            
            if data.get("evidence"):
                response["evidence"] = data["evidence"]
            
            if data.get("expires"):
                response["expires"] = data["expires"]
                response["message"] += f" Note: This review expires on {data['expires']}."
            
            if data.get("re_evaluate_on"):
                response["re_evaluate_condition"] = data["re_evaluate_on"]
            
            return response
            
        except ImportError:
            return {
                "success": False,
                "error": "PyYAML library not available. Cannot read known issues database."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read known issue file: {str(e)}"
            }
    
    def _find_issue_file(self, known_issues_dir: Path, problem_id: str) -> Path:
        """
        Find the YAML file for a given problem ID.
        Tries multiple naming conventions.
        
        Args:
            known_issues_dir: Directory containing known issues
            problem_id: Problem ID to search for
        
        Returns:
            Path to the YAML file, or None if not found
        """
        # Try exact match first
        candidates = [
            f"{problem_id}.yaml",
            f"{problem_id}.yml",
        ]
        
        # Try with common transformations
        # CVE:2020:14343 -> CVE-2020-14343
        sanitized_dash = problem_id.replace(":", "-").replace("/", "-").replace(" ", "-")
        candidates.extend([
            f"{sanitized_dash}.yaml",
            f"{sanitized_dash}.yml",
        ])
        
        # CVE:2020:14343 -> CVE_2020_14343
        sanitized_underscore = problem_id.replace(":", "_").replace("/", "_").replace(" ", "_")
        candidates.extend([
            f"{sanitized_underscore}.yaml",
            f"{sanitized_underscore}.yml",
        ])
        
        # Try all candidates
        for candidate in candidates:
            yaml_file = known_issues_dir / candidate
            if yaml_file.exists() and not yaml_file.name.startswith("."):
                return yaml_file
        
        # Last resort: case-insensitive search
        # (for when user creates CVE-2020-14343.yaml but scanner reports cve-2020-14343)
        problem_id_lower = problem_id.lower()
        for yaml_file in known_issues_dir.glob("*.yaml"):
            if yaml_file.name.startswith("."):  # Skip template and examples
                continue
            
            # Extract problem ID from filename (remove .yaml/.yml)
            file_id = yaml_file.stem.lower()
            
            # Check if it matches
            if file_id == problem_id_lower or \
               file_id == sanitized_dash.lower() or \
               file_id == sanitized_underscore.lower():
                return yaml_file
        
        return None

