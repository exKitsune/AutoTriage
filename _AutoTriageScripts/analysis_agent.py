#!/usr/bin/env python3

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI

from ai_tools import get_ai_client, query_model

class AnalysisState(Enum):
    """States that the analysis can be in."""
    GATHERING_CONTEXT = "gathering_context"
    ANALYZING_CODE = "analyzing_code"
    CHECKING_DEPENDENCIES = "checking_dependencies"
    EVALUATING_EXPLOIT = "evaluating_exploit"
    MAKING_DECISION = "making_decision"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class AnalysisResult:
    """Result of the analysis."""
    problem_id: str
    is_applicable: bool
    confidence: float  # 0.0 to 1.0
    explanation: str
    severity: str
    recommended_actions: List[str]
    evidence: Dict[str, Any]
    analysis_steps: List[Dict[str, Any]]  # Track the analysis process

class AnalysisAgent:
    """Agent responsible for analyzing a single security/quality problem."""
    
    def __init__(
        self,
        problem: Dict,
        workspace_root: Path,
        input_dir: Path,
        ai_client: OpenAI,
        config: Dict[str, Any]
    ):
        self.problem = problem
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        self.ai_client = ai_client
        self.config = config
        self.state = AnalysisState.GATHERING_CONTEXT
        self.analysis_steps = []
        
        # Load prompt templates
        with open(Path(__file__).parent / "config" / "prompts.json") as f:
            self.prompts = json.load(f)
    
    def _validate_and_fallback(self, response: str, required_fields: List[str]) -> Dict[str, Any]:
        """
        Validate AI response and provide fallback values if needed.
        
        Args:
            response: Raw AI response string
            required_fields: List of required fields in the response
        
        Returns:
            Validated dict with fallback values if needed
        """
        # Try to parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse AI response as JSON: {str(e)}")
            print(f"Response preview: {response[:200]}...")
            return self._create_fallback_response(
                error="Failed to parse AI response as JSON",
                raw_response=response
            )
        
        # Validate required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            print(f"Warning: AI response missing required fields: {missing_fields}")
            # Try to provide defaults for missing fields
            for field in missing_fields:
                if field == "is_applicable":
                    data[field] = False  # Conservative default
                elif field == "confidence":
                    data[field] = 0.0
                elif field == "explanation":
                    data[field] = "No explanation provided by AI"
                elif field == "evidence":
                    data[field] = {}
                elif field == "recommended_actions":
                    data[field] = []
        
        # Validate field types
        if "is_applicable" in data and not isinstance(data["is_applicable"], bool):
            data["is_applicable"] = bool(data["is_applicable"])
        
        if "confidence" in data:
            try:
                confidence = float(data["confidence"])
                data["confidence"] = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
            except (ValueError, TypeError):
                print(f"Warning: Invalid confidence value: {data['confidence']}")
                data["confidence"] = 0.5
        
        if "recommended_actions" in data and not isinstance(data["recommended_actions"], list):
            data["recommended_actions"] = []
        
        return data
    
    def _create_fallback_response(self, error: str, raw_response: str = "") -> Dict[str, Any]:
        """
        Create a fallback response when AI fails.
        
        Args:
            error: Error message
            raw_response: Raw AI response if available
        
        Returns:
            Fallback response dict
        """
        return {
            "is_applicable": False,  # Conservative: assume not applicable on error
            "confidence": 0.0,
            "explanation": f"Analysis failed: {error}. Manual review recommended.",
            "evidence": {"error": error, "raw_response": raw_response[:500] if raw_response else ""},
            "recommended_actions": ["Manual review required due to analysis failure"]
        }
    
    def get_code_context(self, file_path: str, line_number: Optional[int] = None) -> str:
        """Get relevant code context from the specified file."""
        try:
            target_file = self.workspace_root / file_path
            if not target_file.exists():
                return "File not found"
            
            with open(target_file) as f:
                content = f.read()
            
            if line_number:
                # TODO: Get context around the specific line
                return f"Line {line_number} context not implemented yet"
            
            return content
            
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def get_sbom_context(self, component: str) -> Dict[str, Any]:
        """Get relevant SBOM data for a component."""
        sbom_file = self.input_dir / "sbom" / "sbom.json"
        if not sbom_file.exists():
            return {}
        
        try:
            with open(sbom_file) as f:
                sbom_data = json.load(f)
            
            # TODO: Find relevant component data in SBOM
            return sbom_data
            
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_vulnerability(self) -> Dict[str, Any]:
        """Analyze a security vulnerability."""
        # Get vulnerability prompt template
        prompt_data = self.prompts["vulnerability_analysis"]
        
        # Gather context
        code_context = "No code context available"
        if "component" in self.problem:
            code_context = self.get_code_context(
                self.problem["component"],
                self.problem.get("line")
            )
        
        sbom_context = self.get_sbom_context(self.problem.get("component", ""))
        
        # Format prompt with gathered context
        formatted_prompt = prompt_data["prompt_template"].format(
            vulnerability=json.dumps(self.problem, indent=2),
            code_context=code_context,
            sbom_context=json.dumps(sbom_context, indent=2)
        )
        
        # Query AI with error handling
        try:
            response = query_model(
                self.ai_client,
                formatted_prompt,
                system_context=prompt_data["system_context"],
                config=self.config
            )
            
            # Validate and parse response with fallback
            required_fields = ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"]
            return self._validate_and_fallback(response, required_fields)
            
        except Exception as e:
            print(f"Error during vulnerability analysis: {str(e)}")
            return self._create_fallback_response(str(e))
    
    def analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze a code quality issue."""
        # Get code quality prompt template
        prompt_data = self.prompts["code_quality_analysis"]
        
        # Gather context
        code_context = self.get_code_context(
            self.problem["component"],
            self.problem.get("line")
        )
        
        project_context = {
            "file": self.problem["component"],
            "line": self.problem.get("line"),
            "type": self.problem.get("type"),
            "severity": self.problem.get("severity")
        }
        
        # Format prompt with gathered context
        formatted_prompt = prompt_data["prompt_template"].format(
            issue=json.dumps(self.problem, indent=2),
            code_context=code_context,
            project_context=json.dumps(project_context, indent=2)
        )
        
        # Query AI with error handling
        try:
            response = query_model(
                self.ai_client,
                formatted_prompt,
                system_context=prompt_data["system_context"],
                config=self.config
            )
            
            # Validate and parse response with fallback
            required_fields = ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"]
            return self._validate_and_fallback(response, required_fields)
            
        except Exception as e:
            print(f"Error during code quality analysis: {str(e)}")
            return self._create_fallback_response(str(e))
    
    def analyze_dependency(self) -> Dict[str, Any]:
        """Analyze a dependency issue."""
        # Get dependency prompt template
        prompt_data = self.prompts["dependency_analysis"]
        
        # Gather context
        usage_context = self.get_code_context(self.problem["component"])
        sbom_context = self.get_sbom_context(self.problem["component"])
        
        # Format prompt with gathered context
        formatted_prompt = prompt_data["prompt_template"].format(
            dependency=json.dumps(self.problem, indent=2),
            usage_context=usage_context,
            sbom_context=json.dumps(sbom_context, indent=2)
        )
        
        # Query AI with error handling
        try:
            response = query_model(
                self.ai_client,
                formatted_prompt,
                system_context=prompt_data["system_context"],
                config=self.config
            )
            
            # For dependency analysis, the required fields might differ slightly
            # but we'll use the same basic structure for consistency
            required_fields = ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"]
            return self._validate_and_fallback(response, required_fields)
            
        except Exception as e:
            print(f"Error during dependency analysis: {str(e)}")
            return self._create_fallback_response(str(e))
    
    def analyze(self) -> AnalysisResult:
        """
        Run the full analysis pipeline.
        Returns an AnalysisResult with the findings.
        
        Even if errors occur, returns a result with fallback values
        and low confidence to enable manual review.
        """
        try:
            # Analyze based on problem type
            if self.problem["type"] == "vulnerability":
                analysis = self.analyze_vulnerability()
            elif self.problem["type"] in ["code-smell", "bug", "code_smell"]:
                analysis = self.analyze_code_quality()
            else:
                analysis = self.analyze_dependency()
            
            # Note: We no longer raise on "error" in analysis because
            # fallback responses still provide valid structure with
            # conservative defaults (not applicable, 0 confidence)
            
            # Create result (analysis now always has required fields due to fallback)
            result = AnalysisResult(
                problem_id=self.problem.get("id", "unknown"),
                is_applicable=analysis.get("is_applicable", False),
                confidence=analysis.get("confidence", 0.0),
                explanation=analysis.get("explanation", "Analysis unavailable"),
                severity=self.problem.get("severity", "UNKNOWN"),
                recommended_actions=analysis.get("recommended_actions", ["Manual review required"]),
                evidence=analysis.get("evidence", {}),
                analysis_steps=self.analysis_steps
            )
            
            # Set state based on whether there was an error
            if "error" in analysis.get("evidence", {}):
                self.state = AnalysisState.ERROR
                print(f"Warning: Analysis completed with errors for {self.problem.get('id', 'unknown')}")
            else:
                self.state = AnalysisState.COMPLETE
            
            return result
            
        except Exception as e:
            # Last resort fallback if something goes completely wrong
            self.state = AnalysisState.ERROR
            print(f"Critical error in analysis pipeline: {str(e)}")
            return AnalysisResult(
                problem_id=self.problem.get("id", "unknown"),
                is_applicable=False,
                confidence=0.0,
                explanation=f"Critical analysis failure: {str(e)}",
                severity=self.problem.get("severity", "UNKNOWN"),
                recommended_actions=["Manual review required - analysis pipeline failed"],
                evidence={"critical_error": str(e)},
                analysis_steps=self.analysis_steps
            )

class AgentSystem:
    """System for managing multiple analysis agents."""
    
    def __init__(
        self,
        workspace_root: Path,
        input_dir: Path,
        config_dir: Path
    ):
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        
        # Load AI config
        with open(config_dir / "ai_config.json") as f:
            self.config = json.load(f)
        
        # Initialize AI client
        self.ai_client = get_ai_client(self.config)
        
        self.results = []
    
    def analyze_problems(self, problems: List[Dict]) -> List[AnalysisResult]:
        """
        Analyze a list of problems using individual agents.
        Returns a list of analysis results.
        """
        for problem in problems:
            agent = AnalysisAgent(
                problem,
                self.workspace_root,
                self.input_dir,
                self.ai_client,
                self.config
            )
            try:
                result = agent.analyze()
                self.results.append(result)
            except Exception as e:
                print(f"Error analyzing problem {problem.get('id', 'unknown')}: {str(e)}")
        
        return self.results
    
    def generate_report(self, output_dir: Path) -> None:
        """Generate a detailed report of all analysis results."""
        report = {
            "summary": {
                "total_problems": len(self.results),
                "applicable_problems": sum(1 for r in self.results if r.is_applicable),
                "by_severity": {}
            },
            "results": [
                {
                    "problem_id": r.problem_id,
                    "is_applicable": r.is_applicable,
                    "confidence": r.confidence,
                    "explanation": r.explanation,
                    "severity": r.severity,
                    "recommended_actions": r.recommended_actions,
                    "evidence": r.evidence,
                    "analysis_steps": r.analysis_steps
                }
                for r in self.results
            ]
        }
        
        # Count by severity
        for result in self.results:
            if result.is_applicable:
                report["summary"]["by_severity"][result.severity] = \
                    report["summary"]["by_severity"].get(result.severity, 0) + 1
        
        # Write detailed report
        report_file = output_dir / "analysis_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Write markdown summary
        summary_file = output_dir / "analysis_summary.md"
        with open(summary_file, 'w') as f:
            f.write("# Security and Quality Analysis Summary\n\n")
            f.write(f"Total problems analyzed: {report['summary']['total_problems']}\n")
            f.write(f"Applicable problems: {report['summary']['applicable_problems']}\n\n")
            
            f.write("## Problems by Severity\n\n")
            for severity, count in report["summary"]["by_severity"].items():
                f.write(f"- {severity}: {count}\n")