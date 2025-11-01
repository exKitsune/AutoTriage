#!/usr/bin/env python3

import argparse
import os
import sys
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any

@dataclass
class Problem:
    """Represents a security or code quality issue from any analysis tool."""
    id: str  # Unique identifier for the issue
    source: str  # Tool that found the issue (e.g., 'sonarqube', 'dependency-check')
    title: str  # Short description of the issue
    description: str  # Detailed description
    severity: str  # Severity level (normalized across tools)
    component: str  # Affected component/file
    type: str  # Type of issue (e.g., 'vulnerability', 'code-smell', 'bug')
    line: Optional[int] = None  # Line number if applicable
    raw_data: Optional[Dict[str, Any]] = None  # Original raw data from the tool

def normalize_severity(severity: str, source: str) -> str:
    """Normalize severity levels across different tools."""
    severity = severity.upper()
    
    if source == "sonarqube":
        severity_map = {
            "BLOCKER": "CRITICAL",
            "CRITICAL": "CRITICAL",
            "MAJOR": "HIGH",
            "MINOR": "LOW",
            "INFO": "INFO"
        }
        return severity_map.get(severity, severity)
    
    if source == "dependency-check":
        # Dependency Check already uses standard severity levels
        return severity
    
    return severity

def parse_sonarqube_issues(issues_file: Path) -> List[Problem]:
    """Parse SonarQube issues into Problem objects."""
    with open(issues_file) as f:
        data = json.load(f)
    
    problems = []
    for issue in data.get("issues", []):
        problems.append(Problem(
            id=issue["key"],
            source="sonarqube",
            title=issue["message"],
            description=issue.get("message", ""),  # SonarQube doesn't always have detailed descriptions
            severity=normalize_severity(issue["severity"], "sonarqube"),
            component=issue["component"],
            type=issue["type"].lower(),
            line=issue.get("line"),
            raw_data=issue
        ))
    
    return problems

def parse_dependency_check_issues(report_file: Path) -> List[Problem]:
    """Parse Dependency Check issues into Problem objects."""
    with open(report_file) as f:
        data = json.load(f)
    
    problems = []
    for dependency in data.get("dependencies", []):
        for vuln in dependency.get("vulnerabilities", []):
            description = vuln.get("description", "")
            if vuln.get("cwes"):
                description = f"CWEs: {', '.join(vuln['cwes'])}\n{description}"
            
            problems.append(Problem(
                id=vuln["name"],  # Usually a CVE ID
                source="dependency-check",
                title=f"Vulnerability in {dependency['fileName']}: {vuln['name']}",
                description=description,
                severity=normalize_severity(vuln["severity"], "dependency-check"),
                component=dependency["fileName"],
                type="vulnerability",
                raw_data={
                    "vulnerability": vuln,
                    "dependency": {
                        "fileName": dependency["fileName"],
                        "filePath": dependency["filePath"],
                        "packages": dependency.get("packages", [])
                    }
                }
            ))
    
    return problems

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze security tool outputs and generate a consolidated report"
    )
    
    parser.add_argument(
        "subfolder",
        help="Subfolder being analyzed (e.g. container_security)"
    )
    
    parser.add_argument(
        "--sonarqube",
        action="store_true",
        help="Process SonarQube analysis results"
    )
    
    parser.add_argument(
        "--dependency-check",
        action="store_true",
        help="Process OWASP Dependency-Check results"
    )
    
    parser.add_argument(
        "--input-dir",
        type=str,
        default="analysis-inputs",
        help="Directory containing the downloaded artifacts (default: analysis-inputs)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="analysis-outputs",
        help="Directory to write analysis results (default: analysis-outputs)"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum number of tool calls the AI can make per issue (default: 5)"
    )

    args = parser.parse_args()
    
    # If no tools are selected, enable all by default
    if not any([args.sonarqube, args.dependency_check]):
        args.sonarqube = True
        args.dependency_check = True
    
    return args

def get_tool_paths(input_dir: Path, args: argparse.Namespace) -> Dict[str, Path]:
    """
    Get the paths to the tool output files based on enabled tools.
    Returns a dictionary of tool names to their file paths.
    """
    tool_paths = {}
    
    if args.sonarqube:
        sonar_dir = input_dir / "sonarqube"
        if sonar_dir.exists():
            tool_paths["sonarqube"] = sonar_dir / "sonar-issues.json"
    
    if args.dependency_check:
        depcheck_dir = input_dir / "dependency-check"
        if depcheck_dir.exists():
            tool_paths["dependency-check"] = depcheck_dir / "dependency-check-report.json"
    
    # SBOM is always included when available
    sbom_dir = input_dir / "sbom"
    if sbom_dir.exists():
        tool_paths["sbom"] = sbom_dir / "sbom.json"
    
    return tool_paths

def collect_problems(input_dir: Path, args: argparse.Namespace) -> List[Problem]:
    """Collect all problems from available analysis tools."""
    problems = []
    tool_paths = get_tool_paths(input_dir, args)
    
    if not tool_paths:
        print("No analysis tool outputs found in", input_dir)
        return problems
    
    # Process SonarQube results if enabled and available
    if "sonarqube" in tool_paths:
        print("Processing SonarQube results...")
        problems.extend(parse_sonarqube_issues(tool_paths["sonarqube"]))
    elif args.sonarqube:
        print("Warning: SonarQube analysis was enabled but no results found")
    
    # Process Dependency Check results if enabled and available
    if "dependency-check" in tool_paths:
        print("Processing Dependency-Check results...")
        problems.extend(parse_dependency_check_issues(tool_paths["dependency-check"]))
    elif args.dependency_check:
        print("Warning: Dependency-Check was enabled but no results found")
    
    # Sort problems by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    problems.sort(key=lambda x: severity_order.get(x.severity, 999))
    
    return problems

def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)
    
    # Check for required environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is required")
        sys.exit(1)
    
    print("Starting analysis...")
    enabled_tools = []
    if args.sonarqube:
        enabled_tools.append("sonarqube")
    if args.dependency_check:
        enabled_tools.append("dependency-check")
    print("Enabled tools:", ", ".join(enabled_tools))
    print(f"Max iterations per issue: {args.max_iterations}")
    
    # Collect problems from enabled tools
    problems = collect_problems(input_dir, args)
    
    # Write initial problems to a JSON file for debug
    problems_file = output_dir / "problems.json"
    with open(problems_file, 'w') as f:
        json.dump([{
            "id": p.id,
            "source": p.source,
            "title": p.title,
            "description": p.description,
            "severity": p.severity,
            "component": p.component,
            "type": p.type,
            "line": p.line,
            "raw_data": p.raw_data
        } for p in problems], f, indent=2)
    
    print(f"\nFound {len(problems)} potential issues.")
    print(f"{'='*80}")
    print(f"Starting detailed AI-powered analysis...")
    print(f"{'='*80}\n")
    
    # Initialize the agent system
    from analysis_agent import AgentSystem
    
    config_dir = Path(__file__).parent / "config"
    if not config_dir.exists():
        print(f"Error: Config directory not found at {config_dir}")
        sys.exit(1)
    
    # Workspace root is the current directory (repo root), not the subfolder
    # The subfolder is already included in the component paths from SonarQube
    workspace_root = Path.cwd()
    agent_system = AgentSystem(workspace_root, input_dir, config_dir, max_iterations=args.max_iterations)
    
    # Convert Problem dataclasses to dicts for the agent system
    problems_as_dicts = [asdict(p) for p in problems]
    
    # Run analysis
    try:
        results = agent_system.analyze_problems(problems_as_dicts, output_dir=output_dir)
        agent_system.generate_report(output_dir)
        
        # Count issues by priority
        important_count = sum(1 for r in results if r.is_applicable and r.severity in ["CRITICAL", "HIGH", "MEDIUM"])
        low_priority_count = sum(1 for r in results if r.is_applicable and r.severity in ["LOW", "TRIVIAL"])
        dismissed_count = sum(1 for r in results if not r.is_applicable)
        
        print(f"\n{'='*80}")
        print("✅ ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"Total issues analyzed: {len(problems)}")
        print(f"🚨 Issues requiring attention: {important_count} (CRITICAL/HIGH/MEDIUM)")
        if low_priority_count > 0:
            print(f"ℹ️  Low priority issues: {low_priority_count}")
        print(f"✅ Issues dismissed: {dismissed_count}")
        
        # Calculate efficiency metrics
        if results:
            avg_confidence = sum(r.confidence for r in results) / len(results)
            total_steps = sum(len(r.analysis_steps) for r in results)
            avg_steps = total_steps / len(results)
            
            print(f"\n📊 Analysis Performance:")
            print(f"  Average confidence: {avg_confidence:.0%}")
            print(f"  Total investigation steps: {total_steps}")
            print(f"  Average steps per issue: {avg_steps:.1f}")
            print(f"  Efficiency: {'🔥 Excellent' if avg_steps < 3 else '✅ Good' if avg_steps < 5 else '⚠️  Could improve'}")
        
        print(f"\n📁 Results written to:")
        print(f"  📄 {output_dir / 'analysis_report.json'}")
        print(f"  📋 {output_dir / 'analysis_summary.md'}")
        print(f"  💾 {output_dir / 'conversation_logs'}/ (detailed logs)")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
