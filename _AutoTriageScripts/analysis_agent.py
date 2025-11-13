#!/usr/bin/env python3

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI

from llm_client import get_ai_client, query_model
from tool_executor import ToolExecutor
from prompt_formatter import format_tools_for_prompt
from tools import get_all_tool_classes

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
    problem_title: str
    problem_description: str
    problem_type: str  # vulnerability, code_smell, bug, etc.
    is_applicable: bool
    explanation: str
    severity: str
    recommended_actions: List[str]
    evidence: Dict[str, Any]
    analysis_steps: List[Dict[str, Any]]  # Track the analysis process
    reasoning: str = ""  # LLM's accumulated reasoning/thought process during analysis
    investigation_summary: str = ""  # Summary of what the LLM did to reach its conclusion
    verification_steps: List[str] = None  # How user can verify the findings themselves
    limitations: List[str] = None  # What the LLM couldn't check or missed
    analysis_failed: bool = False  # Whether the analysis failed due to errors (not a determination)
    
    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.verification_steps is None:
            self.verification_steps = []
        if self.limitations is None:
            self.limitations = []

class AnalysisAgent:
    """Agent responsible for analyzing a single security/quality problem."""
    
    @staticmethod
    def _load_prompts() -> Dict[str, Dict[str, str]]:
        """
        Load prompt templates from text files.
        
        Returns:
            Dictionary with prompt data for each analysis type.
            Format: {
                "vulnerability_analysis": {
                    "system_context": "...",
                    "prompt_template": "..."
                },
                ...
            }
        """
        prompts_dir = Path(__file__).parent / "config" / "prompts"
        prompts = {}
        
        # Define the analysis types and their corresponding file prefixes
        analysis_types = [
            "vulnerability_analysis",
            "code_quality_analysis",
            "dependency_analysis"
        ]
        
        for analysis_type in analysis_types:
            system_file = prompts_dir / f"{analysis_type}_system.txt"
            prompt_file = prompts_dir / f"{analysis_type}_prompt.txt"
            
            # Read system context
            if system_file.exists():
                with open(system_file, 'r', encoding='utf-8') as f:
                    system_context = f.read().strip()
            else:
                system_context = ""
            
            # Read prompt template
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_template = f.read().strip()
            else:
                prompt_template = ""
            
            prompts[analysis_type] = {
                "system_context": system_context,
                "prompt_template": prompt_template
            }
        
        return prompts
    
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
        
        # Load prompt templates from text files
        self.prompts = self._load_prompts()
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given parameters.
        Returns the tool's result dictionary.
        """
        # Use the modular tool system's execute_tool method
        return self.tool_executor.execute_tool(tool_name, parameters)
    
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
                elif field == "explanation":
                    data[field] = "No explanation provided by AI"
                elif field == "investigation_summary":
                    data[field] = "Investigation summary not provided"
                elif field == "evidence":
                    data[field] = {}
                elif field == "recommended_actions":
                    data[field] = []
                elif field == "verification_steps":
                    data[field] = ["Manually review the issue"]
                elif field == "limitations":
                    data[field] = ["Analysis completeness unknown"]
        
        # Validate field types
        if "is_applicable" in data and not isinstance(data["is_applicable"], bool):
            data["is_applicable"] = bool(data["is_applicable"])
        
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
            Fallback response dict with error flag
        """
        return {
            "is_applicable": False,  # Conservative: assume not applicable on error
            # NOTE: No 'real_severity' - analyze() will use original problem severity for failed analyses
            "explanation": f"Analysis failed: {error}. Manual review recommended.",
            "evidence": {"error": error, "raw_response": raw_response if raw_response else ""},
            "recommended_actions": ["Manual review required due to analysis failure"],
            "investigation_summary": "Analysis failed before investigation could complete",
            "verification_steps": ["Manually review the issue details", "Check logs for error details"],
            "limitations": ["Automated analysis failed - full manual review required"],
            "_analysis_error": True  # Explicit flag to indicate analysis failure
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
            Analysis result dict with is_applicable, explanation, etc.
        """
        print(f"\n{'='*60}")
        print(f"Starting agentic analysis (max {max_iterations} iterations)")
        print(f"Problem: {self.problem.get('title', self.problem.get('id', 'unknown'))}")
        print(f"ID: {self.problem.get('id', 'unknown')}")
        print(f"{'='*60}\n")
        
        conversation_history = []  # Will store full conversation for debugging
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
                print(f"  Messages in conversation: {len(messages)}")
                
                # Show message chain summary
                for i, msg in enumerate(messages):
                    role_icon = "🤖" if msg["role"] == "system" else ("👤" if msg["role"] == "user" else "🔧")
                    content_preview = msg["content"][:100].replace('\n', ' ')
                    print(f"    [{i+1}] {role_icon} {msg['role']}: {content_preview}...")
                
                print(f"  Sending {len(messages)} messages to AI...")
                response = query_model(
                    self.ai_client,
                    messages=messages,  # Pass full conversation history
                    config=self.config
                )
                
                # Try to parse as JSON tool call
                tool_call = json.loads(response.strip())
                
                # Validate it has the right structure
                if not isinstance(tool_call, dict) or "tool" not in tool_call:
                    # Not a valid tool call format
                    print(f"  ❌ ERROR: LLM response not in tool format")
                    print(f"  Response: {response}")
                    fallback = self._create_fallback_response(
                        "LLM did not provide valid tool call format",
                        response
                    )
                    # Include conversation history for debugging
                    fallback["_conversation_history"] = conversation_history
                    fallback["_final_message_count"] = len(messages)
                    return fallback
                
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
                    # First validate required fields are present
                    required_fields = ["is_applicable", "real_severity", "explanation", "investigation_summary", "evidence", "recommended_actions", "verification_steps"]
                    missing_fields = [f for f in required_fields if f not in parameters]
                    
                    # Check for common mistakes in parameter names
                    wrong_names = {
                        "vulnerability_applicable": "is_applicable",
                        "applicable": "is_applicable",
                        "conclusion": "explanation",
                        "reasoning": "explanation",
                        "actions": "recommended_actions",
                        "severity": "real_severity",
                        "actual_severity": "real_severity",
                        "assessed_severity": "real_severity"
                    }
                    
                    if missing_fields:
                        # Try to auto-correct common mistakes
                        corrected = False
                        for wrong, correct in wrong_names.items():
                            if wrong in parameters and correct in missing_fields:
                                parameters[correct] = parameters.pop(wrong)
                                corrected = True
                                print(f"  ⚠️  Auto-corrected parameter: {wrong} → {correct}")
                        
                        # If still missing fields after correction, return error to AI
                        missing_fields = [f for f in required_fields if f not in parameters]
                        if missing_fields:
                            error_msg = {
                                "error": f"provide_analysis missing required fields: {', '.join(missing_fields)}",
                                "required_fields": required_fields,
                                "your_fields": list(parameters.keys()),
                                "note": "Please call provide_analysis again with ALL required fields"
                            }
                            print(f"  ❌ ERROR: Missing required fields: {missing_fields}")
                            
                            # Give AI another chance
                            messages.append({"role": "assistant", "content": response})
                            messages.append({
                                "role": "user",
                                "content": f"Tool error:\n{json.dumps(error_msg, indent=2)}\n\nCall provide_analysis again with the EXACT required fields: {', '.join(required_fields)}"
                            })
                            continue  # Go to next iteration
                    
                    print(f"\n  ✅ ANALYSIS COMPLETE")
                    print(f"  Is Applicable: {parameters.get('is_applicable', 'N/A')}")
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
                    
                    # Add accumulated reasoning to the result
                    if accumulated_reasoning:
                        parameters["reasoning"] = "\n".join([
                            f"[Step {i+1}] {thought}" 
                            for i, thought in enumerate(accumulated_reasoning)
                        ])
                    else:
                        parameters["reasoning"] = ""
                    
                    # Save final provide_analysis to conversation history
                    conversation_history.append({
                        "iteration": iteration + 1,
                        "ai_response": response,
                        "tool_called": "provide_analysis",
                        "tool_parameters": parameters,
                        "tool_result": {"status": "analysis_complete"}
                    })
                    
                    # Add conversation history for debugging
                    parameters["_conversation_history"] = conversation_history
                    parameters["_final_message_count"] = len(messages)
                    parameters["_analysis_error"] = False  # Explicitly mark as successful
                    
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
                
                # Check if tool doesn't exist and provide helpful guidance
                if tool_result.get("error") and "Unknown tool" in tool_result["error"]:
                    print(f"  ❌ ERROR: Tool '{tool_name}' does not exist")
                    # Get available tools dynamically from the tool registry
                    available_tools = sorted(get_all_tool_classes().keys())
                    error_msg = {
                        "error": f"Tool '{tool_name}' does not exist",
                        "available_tools": available_tools,
                        "note": "If you have gathered enough information, call provide_analysis to conclude. Otherwise, use one of the available tools listed above."
                    }
                    
                    # Give AI guidance
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": f"Tool error:\n{json.dumps(error_msg, indent=2)}\n\nAvailable tools: {', '.join(available_tools)}\n\nIf you have enough information to make a determination, call provide_analysis. Otherwise, choose an available tool."
                    })
                    continue  # Go to next iteration
                elif tool_result.get("error"):
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
                
                # Save to conversation history for debugging
                conversation_history.append({
                    "iteration": iteration + 1,
                    "ai_response": response,
                    "tool_called": tool_name,
                    "tool_parameters": parameters,
                    "tool_result": tool_result
                })
                
            except json.JSONDecodeError:
                # Response is not JSON - treat as malformed
                print(f"  ❌ ERROR: LLM response is not valid JSON")
                print(f"  Response preview: {response}")
                fallback = self._create_fallback_response(
                    "LLM response was not valid JSON",
                    response
                )
                # Include conversation history for debugging
                fallback["_conversation_history"] = conversation_history
                fallback["_final_message_count"] = len(messages)
                return fallback
            except Exception as e:
                print(f"  ❌ ERROR in agentic loop: {str(e)}")
                fallback = self._create_fallback_response(f"Loop error: {str(e)}")
                # Include conversation history for debugging
                fallback["_conversation_history"] = conversation_history
                fallback["_final_message_count"] = len(messages)
                return fallback
        
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
                messages=messages,  # Pass full conversation history
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
                
                # Save final provide_analysis to conversation history
                conversation_history.append({
                    "iteration": max_iterations + 1,
                    "ai_response": response,
                    "tool_called": "provide_analysis",
                    "tool_parameters": result,
                    "tool_result": {"status": "analysis_complete"}
                })
                
                # Add conversation history
                result["_conversation_history"] = conversation_history
                result["_final_message_count"] = len(messages)
                result["_analysis_error"] = False  # Completed successfully (just hit max iterations)
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
        # Add conversation history
        fallback["_conversation_history"] = conversation_history
        fallback["_final_message_count"] = len(messages)
        # _analysis_error is already set to True in _create_fallback_response
        return fallback
    
    def analyze_vulnerability(self) -> Dict[str, Any]:
        """Analyze a security vulnerability using agentic loop with tools."""
        prompt_data = self.prompts["vulnerability_analysis"]
        
        # Generate full tools documentation (filtered by availability)
        tools_documentation = format_tools_for_prompt(
            workspace_root=self.workspace_root,
            input_dir=self.input_dir
        )
        
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
        
        # Generate full tools documentation (filtered by availability)
        tools_documentation = format_tools_for_prompt(
            workspace_root=self.workspace_root,
            input_dir=self.input_dir
        )
        
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
        
        # Generate full tools documentation (filtered by availability)
        tools_documentation = format_tools_for_prompt(
            workspace_root=self.workspace_root,
            input_dir=self.input_dir
        )
        
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
    
    def _save_conversation_log(self, conversation_history: list, output_dir: Path = None) -> None:
        """Save detailed conversation log for debugging."""
        if not output_dir:
            return
            
        # Create logs directory
        logs_dir = output_dir / "conversation_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Save conversation log
        problem_id = self.problem.get('id', 'unknown').replace(':', '_').replace('/', '_')
        log_file = logs_dir / f"{problem_id}_conversation.json"
        
        # Calculate metrics
        total_tools_called = len([c for c in conversation_history if c.get('tool_called') != 'provide_analysis'])
        
        log_data = {
            "problem_id": self.problem.get('id', 'unknown'),
            "problem_type": self.problem.get('type', 'unknown'),
            "problem_severity": self.problem.get('severity', 'UNKNOWN'),
            "conversation": conversation_history,
            "final_result": {
                "analysis_steps_count": len(self.analysis_steps),
                "iterations_used": len(conversation_history),
                "investigation_tools_used": total_tools_called,
                "tools_breakdown": {}
            }
        }
        
        # Count tools used
        for conv in conversation_history:
            tool = conv.get('tool_called', 'unknown')
            log_data["final_result"]["tools_breakdown"][tool] = \
                log_data["final_result"]["tools_breakdown"].get(tool, 0) + 1
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"  💾 Conversation log saved: {log_file.name} ({len(conversation_history)} turns)")
    
    def analyze(self, output_dir: Path = None) -> AnalysisResult:
        """
        Run the full analysis pipeline.
        Returns an AnalysisResult with the findings.
        
        Even if errors occur, returns a result with fallback values to enable manual review.
        
        Args:
            output_dir: Optional output directory for saving conversation logs
        """
        try:
            # Analyze based on problem type
            if self.problem["type"] in ["vulnerability", "security_hotspot"]:
                analysis = self.analyze_vulnerability()
            elif self.problem["type"] in ["code-smell", "bug", "code_smell"]:
                analysis = self.analyze_code_quality()
            else:
                analysis = self.analyze_dependency()
            
            # Note: We no longer raise on "error" in analysis because
            # fallback responses still provide valid structure with
            # conservative defaults (not applicable)
            
            # Validate that analysis is a dict
            if not isinstance(analysis, dict):
                print(f"ERROR: analysis is not a dict, it's {type(analysis)}: {analysis}")
                raise TypeError(f"Expected dict from analysis methods, got {type(analysis)}")
            
            # Extract conversation history for logging (if present)
            conversation_history = analysis.pop("_conversation_history", [])
            final_message_count = analysis.pop("_final_message_count", 0)
            
            # Save conversation log if output_dir provided
            if output_dir and conversation_history:
                self._save_conversation_log(conversation_history, output_dir)
            
            # Create result (analysis now always has required fields due to fallback)
            # Include reasoning in evidence if provided
            evidence = analysis.get("evidence", {})
            if isinstance(evidence, str):
                evidence = {"note": evidence}
            elif not isinstance(evidence, dict):
                evidence = {}
            
            if analysis.get("reasoning"):
                evidence["reasoning"] = analysis.get("reasoning")
            if final_message_count > 0:
                evidence["conversation_turns"] = final_message_count
            
            # Use AI's severity assessment if provided, otherwise use original severity
            # The AI may provide a more accurate severity based on actual real-world impact
            final_severity = analysis.get("real_severity", self.problem.get("severity", "UNKNOWN"))
            
            # Normalize severity to uppercase and standardize variations
            severity_mapping = {
                "CRITICAL": "CRITICAL",
                "HIGH": "HIGH",
                "MEDIUM": "MEDIUM",
                "MODERATE": "MEDIUM",
                "LOW": "LOW",
                "MINOR": "LOW",
                "TRIVIAL": "TRIVIAL",
                "INFO": "INFO",
                "INFORMATIONAL": "INFO"
            }
            final_severity = severity_mapping.get(str(final_severity).upper(), str(final_severity).upper())
            
            # Ensure recommended_actions is a list
            rec_actions = analysis.get("recommended_actions", ["Manual review required"])
            if not isinstance(rec_actions, list):
                if isinstance(rec_actions, str):
                    rec_actions = [rec_actions]
                else:
                    rec_actions = ["Manual review required"]
            
            # Ensure verification_steps and limitations are lists
            verification_steps = analysis.get("verification_steps", [])
            if not isinstance(verification_steps, list):
                verification_steps = [str(verification_steps)] if verification_steps else []
            
            limitations = analysis.get("limitations", [])
            if not isinstance(limitations, list):
                limitations = [str(limitations)] if limitations else []
            
            result = AnalysisResult(
                problem_id=self.problem.get("id", "unknown"),
                problem_title=self.problem.get("title", "No title"),
                problem_description=self.problem.get("description", "No description"),
                problem_type=self.problem.get("type", "unknown"),
                is_applicable=analysis.get("is_applicable", False),
                explanation=analysis.get("explanation", "Analysis unavailable"),
                severity=final_severity,
                recommended_actions=rec_actions,
                evidence=evidence,
                analysis_steps=self.analysis_steps,
                reasoning=analysis.get("reasoning", ""),
                investigation_summary=analysis.get("investigation_summary", ""),
                verification_steps=verification_steps,
                limitations=limitations
            )
            
            # Set state based on whether there was an error
            # Check explicit error flag from analysis
            if analysis.get("_analysis_error", False):
                result.analysis_failed = True
                self.state = AnalysisState.ERROR
                print(f"Warning: Analysis completed with errors for {self.problem.get('id', 'unknown')}")
            else:
                result.analysis_failed = False
                self.state = AnalysisState.COMPLETE
            
            return result
            
        except Exception as e:
            # Last resort fallback if something goes completely wrong
            self.state = AnalysisState.ERROR
            print(f"Critical error in analysis pipeline: {str(e)}")
            return AnalysisResult(
                problem_id=self.problem.get("id", "unknown"),
                problem_title=self.problem.get("title", "No title"),
                problem_description=self.problem.get("description", "No description"),
                problem_type=self.problem.get("type", "unknown"),
                is_applicable=False,
                explanation=f"Critical analysis failure: {str(e)}",
                severity=self.problem.get("severity", "UNKNOWN"),
                recommended_actions=["Manual review required - analysis pipeline failed"],
                evidence={"critical_error": str(e)},
                analysis_steps=self.analysis_steps,
                reasoning="",
                investigation_summary="Analysis failed before investigation could complete",
                verification_steps=["Manually review the issue details", "Check logs for error details"],
                limitations=["Automated analysis failed - full manual review required"],
                analysis_failed=True
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
    
    def analyze_problems(self, problems: List[Dict], output_dir: Path = None) -> List[AnalysisResult]:
        """
        Analyze a list of problems using individual agents.
        Returns a list of analysis results.
        
        Args:
            problems: List of problem dicts to analyze
            output_dir: Optional output directory for conversation logs
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
                result = agent.analyze(output_dir=output_dir)
                self.results.append(result)
            except Exception as e:
                print(f"Error analyzing problem {problem.get('id', 'unknown')}: {str(e)}")
        
        return self.results
    
    def generate_report(self, output_dir: Path) -> None:
        """Generate a detailed report of all analysis results."""
        from datetime import datetime
        
        report = {
            "summary": {
                "total_problems": len(self.results),
                "applicable_problems": sum(1 for r in self.results if r.is_applicable),
                "by_severity": {},
                "vulnerabilities_by_severity": {},
                "code_quality_by_severity": {}
            },
            "analysis_metadata": {
                "analysis_date": datetime.now().isoformat(),
                "model_used": self.config.get("ai_providers", {}).get("openrouter", {}).get("models", {}).get("default", "unknown"),
                "max_iterations_per_issue": self.max_iterations
            },
            "results": [
                {
                    "problem_id": r.problem_id,
                    "problem_title": r.problem_title,
                    "problem_description": r.problem_description,
                    "problem_type": r.problem_type,
                    "is_applicable": r.is_applicable,
                    "explanation": r.explanation,
                    "severity": r.severity,
                    "investigation_summary": r.investigation_summary,
                    "recommended_actions": r.recommended_actions,
                    "verification_steps": r.verification_steps,
                    "limitations": r.limitations,
                    "evidence": r.evidence,
                    "analysis_steps": r.analysis_steps,
                    "reasoning": r.reasoning,
                    "analysis_failed": r.analysis_failed
                }
                for r in self.results
            ]
        }
        
        # Count by severity (overall and split by type)
        for result in self.results:
            if result.is_applicable:
                # Overall count
                report["summary"]["by_severity"][result.severity] = \
                    report["summary"]["by_severity"].get(result.severity, 0) + 1
                
                # Split by type
                is_vulnerability = result.problem_type in ['vulnerability', 'security_hotspot']
                if is_vulnerability:
                    report["summary"]["vulnerabilities_by_severity"][result.severity] = \
                        report["summary"]["vulnerabilities_by_severity"].get(result.severity, 0) + 1
                else:
                    report["summary"]["code_quality_by_severity"][result.severity] = \
                        report["summary"]["code_quality_by_severity"].get(result.severity, 0) + 1
        
        # Write detailed report
        report_file = output_dir / "analysis_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Write markdown summary
        summary_file = output_dir / "analysis_summary.md"
        with open(summary_file, 'w') as f:
            # Count categories - separate vulnerabilities from code quality
            # Vulnerabilities: type='vulnerability' from dependency-check or cyclonedx
            # Code quality: type='code_smell', 'bug' from sonarqube
            is_vulnerability = lambda r: r.problem_type in ['vulnerability', 'security_hotspot']
            is_code_quality = lambda r: r.problem_type in ['code_smell', 'bug', 'code-smell']
            
            # Separate failed analyses from actual determinations
            failed_analyses = [r for r in self.results if r.analysis_failed]
            successful_results = [r for r in self.results if not r.analysis_failed]
            
            important_vulns = [r for r in successful_results if r.is_applicable and is_vulnerability(r) and r.severity in ["CRITICAL", "HIGH", "MEDIUM"]]
            low_vulns = [r for r in successful_results if r.is_applicable and is_vulnerability(r) and r.severity in ["LOW", "TRIVIAL"]]
            code_quality = [r for r in successful_results if r.is_applicable and is_code_quality(r)]
            false_positives = [r for r in successful_results if not r.is_applicable]
            false_positive_count = len(false_positives)
            
            # Header
            f.write("# Security and Quality Analysis Summary\n\n")
            f.write(f"**Date:** {report.get('analysis_metadata', {}).get('analysis_date', 'N/A')}\n")
            f.write(f"**Total Issues Analyzed:** {report['summary']['total_problems']}\n")
            f.write(f"**Security Issues Requiring Attention:** {len(important_vulns)} (CRITICAL/HIGH/MEDIUM)\n")
            f.write(f"**Code Quality Issues:** {len(code_quality)}\n")
            f.write(f"**False Positives/Not Applicable:** {false_positive_count}\n")
            if failed_analyses:
                f.write(f"**⚠️ Analysis Failures (Manual Review Required):** {len(failed_analyses)}\n")
            f.write("\n")
            
            # Analysis Details at the top
            f.write("## 📊 Analysis Details\n\n")
            
            # Split severity by type
            vuln_severities = report["summary"]["vulnerabilities_by_severity"]
            quality_severities = report["summary"]["code_quality_by_severity"]
            
            if vuln_severities:
                f.write(f"- **Vulnerabilities by Severity:**\n")
                for severity, count in vuln_severities.items():
                    f.write(f"  - {severity}: {count}\n")
            
            if quality_severities:
                f.write(f"- **Code Quality Issues by Severity:**\n")
                for severity, count in quality_severities.items():
                    f.write(f"  - {severity}: {count}\n")
            
            if not vuln_severities and not quality_severities:
                f.write(f"- **All Issues:** No applicable issues found\n")
            
            f.write(f"- **Total Investigation Steps:** {sum(len(r.analysis_steps) for r in self.results)}\n\n")
            f.write("---\n\n")
            
            # Security vulnerabilities - only show important issues (CRITICAL, HIGH, MEDIUM)
            if important_vulns:
                f.write("## 🚨 Security Issues Requiring Attention\n\n")
                
                # Group by severity - only important ones
                severity_order = ["CRITICAL", "HIGH", "MEDIUM"]
                for severity in severity_order:
                    severity_issues = [r for r in important_vulns if r.severity == severity]
                    if severity_issues:
                        f.write(f"### {severity} Severity ({len(severity_issues)} issue{'s' if len(severity_issues) > 1 else ''})\n\n")
                        for result in severity_issues:
                            f.write(f"### Problem: {result.problem_title}\n\n")
                            f.write(f"**Description:** {result.problem_description}\n\n")
                            f.write(f"- **ID:** `{result.problem_id}`\n")
                            if result.investigation_summary:
                                f.write(f"- **Investigation:** {result.investigation_summary}\n")
                            f.write(f"- **Analysis:** {result.explanation}\n")
                            f.write(f"- **Actions:**\n")
                            for action in result.recommended_actions:
                                f.write(f"  - {action}\n")
                            if result.verification_steps:
                                f.write(f"- **Verify Yourself:**\n")
                                for step in result.verification_steps:
                                    f.write(f"  - {step}\n")
                            if result.limitations:
                                f.write(f"- **Limitations:**\n")
                                for limitation in result.limitations:
                                    f.write(f"  - {limitation}\n")
                            f.write("\n")
            
            # Low priority vulnerabilities
            if low_vulns:
                f.write("## ⚠️ Low Priority Security Issues\n\n")
                f.write("*These vulnerabilities are low severity but should be addressed during maintenance.*\n\n")
                for result in low_vulns:
                    f.write(f"### Problem: {result.problem_title}\n\n")
                    f.write(f"**Description:** {result.problem_description}\n\n")
                    f.write(f"- **ID:** `{result.problem_id}`\n")
                    f.write(f"- **Severity:** {result.severity}\n")
                    if result.investigation_summary:
                        f.write(f"- **Investigation:** {result.investigation_summary}\n")
                    f.write(f"- **Analysis:** {result.explanation}\n")
                    if result.recommended_actions and isinstance(result.recommended_actions, list):
                        f.write(f"- **Suggested Actions:**\n")
                        for action in result.recommended_actions:
                            f.write(f"  - {action}\n")
                    if result.verification_steps:
                        f.write(f"- **Verify Yourself:**\n")
                        for step in result.verification_steps:
                            f.write(f"  - {step}\n")
                    if result.limitations:
                        f.write(f"- **Limitations:**\n")
                        for limitation in result.limitations:
                            f.write(f"  - {limitation}\n")
                    f.write("\n")
            
            # Code quality issues (separate from vulnerabilities)
            if code_quality:
                f.write("## 🔧 Code Quality Issues\n\n")
                f.write("*These are code quality concerns, not security vulnerabilities.*\n\n")
                for result in code_quality:
                    f.write(f"### Problem: {result.problem_title}\n\n")
                    f.write(f"**Description:** {result.problem_description}\n\n")
                    f.write(f"- **ID:** `{result.problem_id}`\n")
                    f.write(f"- **Severity:** {result.severity}\n")
                    if result.investigation_summary:
                        f.write(f"- **Investigation:** {result.investigation_summary}\n")
                    f.write(f"- **Analysis:** {result.explanation}\n")
                    if result.recommended_actions and isinstance(result.recommended_actions, list):
                        f.write(f"- **Suggested Actions:**\n")
                        for action in result.recommended_actions:
                            f.write(f"  - {action}\n")
                    if result.verification_steps:
                        f.write(f"- **Verify Yourself:**\n")
                        for step in result.verification_steps:
                            f.write(f"  - {step}\n")
                    if result.limitations:
                        f.write(f"- **Limitations:**\n")
                        for limitation in result.limitations:
                            f.write(f"  - {limitation}\n")
                    f.write("\n")
            
            # False positives
            if false_positives:
                f.write("## ✅ False Positives / Not Applicable\n\n")
                for result in false_positives:
                    f.write(f"### Problem: {result.problem_title}\n\n")
                    f.write(f"**Description:** {result.problem_description}\n\n")
                    f.write(f"- **ID:** `{result.problem_id}`\n")
                    f.write(f"- **Severity:** {result.severity}\n")
                    if result.investigation_summary:
                        f.write(f"- **Investigation:** {result.investigation_summary}\n")
                    f.write(f"- **Reason:** {result.explanation}\n")
                    if result.recommended_actions and isinstance(result.recommended_actions, list):
                        f.write(f"- **Recommendations:**\n")
                        for action in result.recommended_actions:
                            f.write(f"  - {action}\n")
                    if result.verification_steps:
                        f.write(f"- **Verify Yourself:**\n")
                        for step in result.verification_steps:
                            f.write(f"  - {step}\n")
                    if result.limitations:
                        f.write(f"- **Limitations:**\n")
                        for limitation in result.limitations:
                            f.write(f"  - {limitation}\n")
                    f.write("\n")
            
            # Failed analyses - separate category for errors
            if failed_analyses:
                f.write("## ⚠️ Analysis Failures - Manual Review Required\n\n")
                f.write("*These issues could not be automatically analyzed due to errors. Manual review is required.*\n\n")
                for result in failed_analyses:
                    f.write(f"### Problem: {result.problem_title}\n\n")
                    f.write(f"**Description:** {result.problem_description}\n\n")
                    f.write(f"- **ID:** `{result.problem_id}`\n")
                    f.write(f"- **Original Severity:** {result.severity}\n")
                    f.write(f"- **Error:** {result.explanation}\n")
                    if result.recommended_actions and isinstance(result.recommended_actions, list):
                        f.write(f"- **Next Steps:**\n")
                        for action in result.recommended_actions:
                            f.write(f"  - {action}\n")
                    f.write("\n")
