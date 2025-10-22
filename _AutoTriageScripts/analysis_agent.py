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
        
        # Query AI
        response = query_model(
            self.ai_client,
            formatted_prompt,
            system_context=prompt_data["system_context"],
            config=self.config
        )
        
        # Parse response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse AI response as JSON",
                "raw_response": response
            }
    
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
        
        # Query AI
        response = query_model(
            self.ai_client,
            formatted_prompt,
            system_context=prompt_data["system_context"],
            config=self.config
        )
        
        # Parse response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse AI response as JSON",
                "raw_response": response
            }
    
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
        
        # Query AI
        response = query_model(
            self.ai_client,
            formatted_prompt,
            system_context=prompt_data["system_context"],
            config=self.config
        )
        
        # Parse response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse AI response as JSON",
                "raw_response": response
            }
    
    def analyze(self) -> AnalysisResult:
        """
        Run the full analysis pipeline.
        Returns an AnalysisResult with the findings.
        """
        try:
            # Analyze based on problem type
            if self.problem["type"] == "vulnerability":
                analysis = self.analyze_vulnerability()
            elif self.problem["type"] in ["code-smell", "bug"]:
                analysis = self.analyze_code_quality()
            else:
                analysis = self.analyze_dependency()
            
            # Check for analysis error
            if "error" in analysis:
                self.state = AnalysisState.ERROR
                raise RuntimeError(f"Analysis failed: {analysis['error']}")
            
            # Create result
            result = AnalysisResult(
                problem_id=self.problem["id"],
                is_applicable=analysis["is_applicable"],
                confidence=analysis["confidence"],
                explanation=analysis["explanation"],
                severity=self.problem["severity"],
                recommended_actions=analysis["recommended_actions"],
                evidence=analysis["evidence"],
                analysis_steps=self.analysis_steps
            )
            
            self.state = AnalysisState.COMPLETE
            return result
            
        except Exception as e:
            self.state = AnalysisState.ERROR
            raise RuntimeError(f"Analysis failed: {str(e)}")

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