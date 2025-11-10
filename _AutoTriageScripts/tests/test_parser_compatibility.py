#!/usr/bin/env python3
"""
Test to verify that the new parser classes produce the same results
as the old parsing functions.
"""

import json
import sys
from pathlib import Path
from dataclasses import asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import Problem, SonarQubeParser, DependencyCheckParser


# OLD PARSING FUNCTIONS (for comparison)
def old_normalize_severity(severity: str, source: str) -> str:
    """Old normalize_severity function from analyze_dependencies.py"""
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


def old_parse_sonarqube_issues(issues_file: Path):
    """Old parse_sonarqube_issues from analyze_dependencies.py"""
    with open(issues_file) as f:
        data = json.load(f)
    
    problems = []
    for issue in data.get("issues", []):
        problems.append({
            "id": issue["key"],
            "source": "sonarqube",
            "title": issue["message"],
            "description": issue.get("message", ""),
            "severity": old_normalize_severity(issue["severity"], "sonarqube"),
            "component": issue["component"],
            "type": issue["type"].lower(),
            "line": issue.get("line"),
            "raw_data": issue
        })
    
    return problems


def old_parse_dependency_check_issues(report_file: Path):
    """Old parse_dependency_check_issues from analyze_dependencies.py"""
    with open(report_file) as f:
        data = json.load(f)
    
    problems = []
    for dependency in data.get("dependencies", []):
        for vuln in dependency.get("vulnerabilities", []):
            description = vuln.get("description", "")
            if vuln.get("cwes"):
                description = f"CWEs: {', '.join(vuln['cwes'])}\n{description}"
            
            problems.append({
                "id": vuln["name"],
                "source": "dependency-check",
                "title": f"Vulnerability in {dependency['fileName']}: {vuln['name']}",
                "description": description,
                "severity": old_normalize_severity(vuln["severity"], "dependency-check"),
                "component": dependency["fileName"],
                "type": "vulnerability",
                "line": None,
                "raw_data": {
                    "vulnerability": vuln,
                    "dependency": {
                        "fileName": dependency["fileName"],
                        "filePath": dependency["filePath"],
                        "packages": dependency.get("packages", [])
                    }
                }
            })
    
    return problems


def problems_to_dict(problems):
    """Convert Problem objects to dicts for comparison"""
    return [asdict(p) for p in problems]


def compare_problems(old_problems, new_problems):
    """Compare two lists of problems"""
    if len(old_problems) != len(new_problems):
        print(f"❌ Length mismatch: {len(old_problems)} vs {len(new_problems)}")
        return False
    
    all_match = True
    for i, (old, new) in enumerate(zip(old_problems, new_problems)):
        # Compare key fields
        for key in ["id", "source", "title", "severity", "component", "type", "line"]:
            if old.get(key) != new.get(key):
                print(f"❌ Problem {i}, field '{key}' mismatch:")
                print(f"   Old: {old.get(key)}")
                print(f"   New: {new.get(key)}")
                all_match = False
    
    return all_match


def test_sonarqube_parser():
    """Test SonarQube parser compatibility"""
    print("\n" + "="*60)
    print("Testing SonarQube Parser")
    print("="*60)
    
    test_file = Path("../_example_output/SonarQube/sonar-issues.json")
    if not test_file.exists():
        test_file = Path("_example_output/SonarQube/sonar-issues.json")
    
    if not test_file.exists():
        print("⚠️  Test file not found, skipping")
        return True
    
    # Parse with old function
    old_problems = old_parse_sonarqube_issues(test_file)
    print(f"Old parser: {len(old_problems)} problems")
    
    # Parse with new parser
    parser = SonarQubeParser()
    new_problems_objs = parser.parse(test_file)
    new_problems = problems_to_dict(new_problems_objs)
    print(f"New parser: {len(new_problems)} problems")
    
    # Compare
    if compare_problems(old_problems, new_problems):
        print("✅ SonarQube parser: PASS - Results match!")
        return True
    else:
        print("❌ SonarQube parser: FAIL - Results differ!")
        return False


def test_dependency_check_parser():
    """Test Dependency-Check parser compatibility"""
    print("\n" + "="*60)
    print("Testing Dependency-Check Parser")
    print("="*60)
    
    test_file = Path("../_example_output/Dependency-Check/dependency-check-report.json")
    if not test_file.exists():
        test_file = Path("_example_output/Dependency-Check/dependency-check-report.json")
    
    if not test_file.exists():
        print("⚠️  Test file not found, skipping")
        return True
    
    # Parse with old function
    old_problems = old_parse_dependency_check_issues(test_file)
    print(f"Old parser: {len(old_problems)} problems")
    
    # Parse with new parser
    parser = DependencyCheckParser()
    new_problems_objs = parser.parse(test_file)
    new_problems = problems_to_dict(new_problems_objs)
    print(f"New parser: {len(new_problems)} problems")
    
    # Compare
    if compare_problems(old_problems, new_problems):
        print("✅ Dependency-Check parser: PASS - Results match!")
        return True
    else:
        print("❌ Dependency-Check parser: FAIL - Results differ!")
        return False


def main():
    """Run all parser compatibility tests"""
    print("\n" + "="*60)
    print("PARSER COMPATIBILITY TEST")
    print("="*60)
    print("Verifying that new parser classes produce the same results")
    print("as the old parsing functions from analyze_dependencies.py")
    
    results = []
    
    # Test each parser
    results.append(("SonarQube", test_sonarqube_parser()))
    results.append(("Dependency-Check", test_dependency_check_parser()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    # Exit with appropriate code
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✅ All tests passed! Parsers are compatible.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed! Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

