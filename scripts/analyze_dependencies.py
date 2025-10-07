#!/usr/bin/env python3

import argparse
import os
import sys
import json
from dataclasses import dataclass
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
    
    print("Starting analysis...")
    enabled_tools = []
    if args.sonarqube:
        enabled_tools.append("sonarqube")
    if args.dependency_check:
        enabled_tools.append("dependency-check")
    print("Enabled tools:", ", ".join(enabled_tools))
    
    problems = collect_problems(input_dir, args)
    
    # Write consolidated problems to a JSON file
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
    
    print(f"\nAnalysis complete. Found {len(problems)} issues:")
    severity_counts = {}
    for p in problems:
        severity_counts[p.severity] = severity_counts.get(p.severity, 0) + 1
    
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        if count := severity_counts.get(severity, 0):
            print(f"  {severity}: {count}")

if __name__ == "__main__":
    main()
