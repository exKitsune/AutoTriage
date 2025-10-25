#!/usr/bin/env python3

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI

from ai_tools import get_ai_client, query_model
from tool_executor import ToolExecutor
from prompt_formatter import format_tools_for_prompt

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
    reasoning: str = ""  # LLM's accumulated reasoning/thought process during analysis

class AnalysisAgent:
    """Agent responsible for analyzing a single security/quality problem."""
    
    def __init__(
        self,
        problem: Dict,
        workspace_root: Path,
        input_dir: Path,
        ai_client: OpenAI,
        config: Dict[str, Any],
        max_iterations: int = 5
    ):
        self.problem = problem
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        self.ai_client = ai_client
        self.config = config
        self.max_iterations = max_iterations
        self.state = AnalysisState.GATHERING_CONTEXT
        self.analysis_steps = []
        
        # Initialize tool executor
        self.tool_executor = ToolExecutor(workspace_root, input_dir)
        
        # Load prompt templates
        with open(Path(__file__).parent / "config" / "prompts.json") as f:
            self.prompts = json.load(f)
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given parameters.
        Returns the tool's result dictionary.
        """
        try:
            method = getattr(self.tool_executor, tool_name, None)
            if not method:
                return {"error": f"Unknown tool: {tool_name}"}
            
            # Tool methods expect a single params dict argument
            return method(parameters)
        except TypeError as e:
            return {"error": f"Invalid parameters for {tool_name}: {str(e)}"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
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
            print(f"Response: {response}...")
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
            "evidence": {"error": error, "raw_response": raw_response if raw_response else ""},
            "recommended_actions": ["Manual review required due to analysis failure"]
        }
    
    def _run_agentic_loop(
        self,
        initial_prompt: str,
        system_context: str,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Run the agentic loop where LLM can call tools iteratively.
        
        Args:
            initial_prompt: The formatted prompt with problem details
            system_context: System context for the LLM
            max_iterations: Maximum number of tool calls before forcing conclusion
        
        Returns:
            Analysis result dict with is_applicable, confidence, explanation, etc.
        """
        print(f"\n{'='*60}")
        print(f"Starting agentic analysis (max {max_iterations} iterations)")
        print(f"Problem: {self.problem.get('id', 'unknown')}")
        print(f"{'='*60}\n")
        
        conversation_history = []
        accumulated_reasoning = []  # Track reasoning from record_reasoning calls
        
        # Build initial messages
        messages = [
            {"role": "system", "content": system_context},
            {"role": "user", "content": initial_prompt}
        ]
        
        for iteration in range(max_iterations):
            print(f"[Iteration {iteration + 1}/{max_iterations}]")
            self.analysis_steps.append({
                "step": iteration + 1,
                "action": "querying_llm",
                "timestamp": ""
            })
            
            try:
                # Query the LLM
                print(f"  Querying LLM...")
                print(f"  System context: {'Provided' if system_context else 'None'}")
                print(f"  Message content: {messages[-1]['content']}...")
                response = query_model(
                    self.ai_client,
                    messages[-1]["content"],  # Last message
                    system_context=system_context,  # Always provide system context
                    config=self.config
                )
                
                # Try to parse as JSON tool call
                tool_call = json.loads(response.strip())
                
                # Validate it has the right structure
                if not isinstance(tool_call, dict) or "tool" not in tool_call:
                    # Not a valid tool call format
                    print(f"  ❌ ERROR: LLM response not in tool format")
                    print(f"  Response: {response}")
                    return self._create_fallback_response(
                        "LLM did not provide valid tool call format",
                        response
                    )
                
                tool_name = tool_call["tool"]
                parameters = tool_call.get("parameters", {})
                
                # Extract reasoning from any tool call (optional field)
                reasoning = tool_call.get("reasoning", "")
                if reasoning:
                    accumulated_reasoning.append(reasoning)
                    print(f"  💭 Reasoning: {reasoning}...")
                
                print(f"  LLM called tool: {tool_name}")
                print(f"  Parameters: {json.dumps(parameters, indent=4)}")
                
                # Check if this is the final analysis
                if tool_name == "provide_analysis":
                    print(f"\n  ✅ ANALYSIS COMPLETE")
                    print(f"  Is Applicable: {parameters.get('is_applicable', 'N/A')}")
                    print(f"  Confidence: {parameters.get('confidence', 'N/A')}")
                    print(f"  Explanation: {parameters.get('explanation', 'N/A')}...")
                    if accumulated_reasoning:
                        print(f"  Accumulated Reasoning Steps: {len(accumulated_reasoning)}")
                    print(f"{'='*60}\n")
                    
                    self.analysis_steps.append({
                        "step": iteration + 1,
                        "action": "received_analysis",
                        "tool": tool_name,
                        "result": "Analysis complete"
                    })
                    
                    # Validate the analysis has required fields
                    required_fields = ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"]
                    for field in required_fields:
                        if field not in parameters:
                            parameters[field] = self._create_fallback_response(
                                f"Missing field in analysis: {field}"
                            )[field]
                    
                    # Add accumulated reasoning to the result
                    if accumulated_reasoning:
                        parameters["reasoning"] = "\n".join([
                            f"[Step {i+1}] {thought}" 
                            for i, thought in enumerate(accumulated_reasoning)
                        ])
                    else:
                        parameters["reasoning"] = ""
                    
                    return parameters
                
                # Execute the tool
                self.analysis_steps.append({
                    "step": iteration + 1,
                    "action": "executing_tool",
                    "tool": tool_name,
                    "parameters": parameters
                })
                
                tool_result = self._execute_tool(tool_name, parameters)
                
                print(f"  Tool result: {json.dumps(tool_result, indent=4)}...")
                if tool_result.get("error"):
                    print(f"  ⚠️  Tool returned error: {tool_result['error']}")
                elif tool_result.get("success") is False:
                    print(f"  ⚠️  Tool failed")
                else:
                    print(f"  ✓ Tool executed successfully")
                print()
                
                self.analysis_steps.append({
                    "step": iteration + 1,
                    "action": "tool_result",
                    "tool": tool_name,
                    "result": tool_result
                })
                
                # Add to conversation
                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": f"Tool result:\n{json.dumps(tool_result, indent=2)}\n\nRespond with your next tool call in JSON format. Call another investigation tool or provide_analysis to conclude."
                })
                
            except json.JSONDecodeError:
                # Response is not JSON - treat as malformed
                print(f"  ❌ ERROR: LLM response is not valid JSON")
                print(f"  Response preview: {response}")
                return self._create_fallback_response(
                    "LLM response was not valid JSON",
                    response
                )
            except Exception as e:
                print(f"  ❌ ERROR in agentic loop: {str(e)}")
                return self._create_fallback_response(f"Loop error: {str(e)}")
        
        # Max iterations reached
        print(f"\n⚠️  MAX ITERATIONS REACHED ({max_iterations})")
        print(f"  Forcing conclusion...")
        print()
        
        self.analysis_steps.append({
            "step": max_iterations,
            "action": "max_iterations_reached",
            "result": "Forcing conclusion"
        })
        
        # Try to force a conclusion by asking directly
        try:
            force_prompt = "You have reached the maximum number of tool calls. Based on the information you've gathered, provide your final analysis using the provide_analysis tool. Respond with ONLY the JSON tool call, no other text."
            messages.append({"role": "user", "content": force_prompt})
            
            response = query_model(
                self.ai_client,
                force_prompt,
                system_context=system_context,
                config=self.config
            )
            
            tool_call = json.loads(response.strip())
            if tool_call.get("tool") == "provide_analysis":
                result = tool_call.get("parameters", self._create_fallback_response("Max iterations"))
                # Add accumulated reasoning
                if accumulated_reasoning:
                    result["reasoning"] = "\n".join([
                        f"[Step {i+1}] {thought}" 
                        for i, thought in enumerate(accumulated_reasoning)
                    ])
                else:
                    result["reasoning"] = ""
                return result
        except:
            pass
        
        fallback = self._create_fallback_response(
            f"Max iterations ({max_iterations}) reached without conclusion"
        )
        # Add accumulated reasoning to fallback
        if accumulated_reasoning:
            fallback["reasoning"] = "\n".join([
                f"[Step {i+1}] {thought}" 
                for i, thought in enumerate(accumulated_reasoning)
            ])
        else:
            fallback["reasoning"] = ""
        return fallback
    
    def analyze_vulnerability(self) -> Dict[str, Any]:
        """Analyze a security vulnerability using agentic loop with tools."""
        prompt_data = self.prompts["vulnerability_analysis"]
        
        # Generate full tools documentation
        tools_documentation = format_tools_for_prompt()
        
        # Format prompt
        formatted_prompt = prompt_data["prompt_template"].format(
            vulnerability=json.dumps(self.problem, indent=2),
            tools_documentation=tools_documentation
        )
        
        # Run agentic loop
        try:
            return self._run_agentic_loop(
                formatted_prompt,
                prompt_data["system_context"],
                max_iterations=self.max_iterations
            )
        except Exception as e:
            print(f"Error during vulnerability analysis: {str(e)}")
            return self._create_fallback_response(str(e))
    
    def analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze a code quality issue using agentic loop with tools."""
        prompt_data = self.prompts["code_quality_analysis"]
        
        # Generate full tools documentation
        tools_documentation = format_tools_for_prompt()
        
        # Format prompt
        formatted_prompt = prompt_data["prompt_template"].format(
            issue=json.dumps(self.problem, indent=2),
            file_path=self.problem.get("component", "unknown"),
            line_number=self.problem.get("line", "N/A"),
            issue_type=self.problem.get("type", "unknown"),
            severity=self.problem.get("severity", "unknown"),
            tools_documentation=tools_documentation
        )
        
        # Run agentic loop
        try:
            return self._run_agentic_loop(
                formatted_prompt,
                prompt_data["system_context"],
                max_iterations=self.max_iterations
            )
        except Exception as e:
            print(f"Error during code quality analysis: {str(e)}")
            return self._create_fallback_response(str(e))
    
    def analyze_dependency(self) -> Dict[str, Any]:
        """Analyze a dependency issue using agentic loop with tools."""
        prompt_data = self.prompts["dependency_analysis"]
        
        # Generate full tools documentation
        tools_documentation = format_tools_for_prompt()
        
        # Format prompt
        formatted_prompt = prompt_data["prompt_template"].format(
            dependency=json.dumps(self.problem, indent=2),
            tools_documentation=tools_documentation
        )
        
        # Run agentic loop
        try:
            return self._run_agentic_loop(
                formatted_prompt,
                prompt_data["system_context"],
                max_iterations=self.max_iterations
            )
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
            # Include reasoning in evidence if provided
            evidence = analysis.get("evidence", {})
            if analysis.get("reasoning"):
                evidence["reasoning"] = analysis.get("reasoning")
            
            result = AnalysisResult(
                problem_id=self.problem.get("id", "unknown"),
                is_applicable=analysis.get("is_applicable", False),
                confidence=analysis.get("confidence", 0.0),
                explanation=analysis.get("explanation", "Analysis unavailable"),
                severity=self.problem.get("severity", "UNKNOWN"),
                recommended_actions=analysis.get("recommended_actions", ["Manual review required"]),
                evidence=evidence,
                analysis_steps=self.analysis_steps,
                reasoning=analysis.get("reasoning", "")
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
                analysis_steps=self.analysis_steps,
                reasoning=""
            )

class AgentSystem:
    """System for managing multiple analysis agents."""
    
    def __init__(
        self,
        workspace_root: Path,
        input_dir: Path,
        config_dir: Path,
        max_iterations: int = 5
    ):
        self.workspace_root = workspace_root
        self.input_dir = input_dir
        self.max_iterations = max_iterations
        
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
                self.config,
                max_iterations=self.max_iterations
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
                    "analysis_steps": r.analysis_steps,
                    "reasoning": r.reasoning
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