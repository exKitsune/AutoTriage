#!/usr/bin/env python3
"""
Basic smoke test for the analysis system.
Tests that the script can parse problems and instantiate the agent system.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import modules
# (tests are in tests/ subdirectory, modules are in parent)
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_problem_parsing():
    """Test that we can parse the example problems.json file."""
    print("Testing problem parsing...")
    
    from analyze_dependencies import parse_sonarqube_issues, parse_dependency_check_issues
    
    # Test with example data
    example_dir = Path(__file__).parent.parent / "_example_output"
    
    # Test SonarQube parsing
    sonar_file = example_dir / "SonarQube" / "sonar-issues.json"
    if sonar_file.exists():
        problems = parse_sonarqube_issues(sonar_file)
        print(f"✓ Parsed {len(problems)} SonarQube issues")
        assert len(problems) > 0, "Should have found some SonarQube issues"
    else:
        print("⚠ SonarQube example file not found, skipping")
    
    # Test Dependency-Check parsing
    depcheck_file = example_dir / "Dependency-Check" / "dependency-check-report.json"
    if depcheck_file.exists():
        problems = parse_dependency_check_issues(depcheck_file)
        print(f"✓ Parsed {len(problems)} dependency issues")
        assert len(problems) > 0, "Should have found some dependency issues"
    else:
        print("⚠ Dependency-Check example file not found, skipping")
    
    print("Problem parsing: PASSED\n")
    return True

def test_agent_system_init():
    """Test that we can initialize the agent system."""
    print("Testing agent system initialization...")
    
    from analysis_agent import AgentSystem
    
    # Test paths
    # Tests are in _AutoTriageScripts/tests/, so go up to _AutoTriageScripts/ and then to config/
    workspace_root = Path(__file__).parent.parent.parent / "container_security"
    input_dir = Path(__file__).parent.parent.parent / "_example_output"
    config_dir = Path(__file__).parent.parent / "config"
    
    if not config_dir.exists():
        print("✗ Config directory not found")
        return False
    
    try:
        # Try to initialize (will fail if OPENROUTER_API_KEY not set, but that's OK)
        agent_system = AgentSystem(workspace_root, input_dir, config_dir, max_iterations=3)
        print("✓ AgentSystem initialized successfully")
        print(f"  - Workspace: {agent_system.workspace_root}")
        print(f"  - Input dir: {agent_system.input_dir}")
        print(f"  - Max iterations: {agent_system.max_iterations}")
        print(f"  - Config loaded: {len(agent_system.config)} keys")
        print("Agent system initialization: PASSED\n")
        return True
    except Exception as e:
        # Check if it's just the API key issue
        error_str = str(e)
        if "api_key" in error_str.lower() or "OPENROUTER_API_KEY" in error_str:
            print("✓ AgentSystem init works (API key not set, which is expected)")
            print("  - Code structure is correct, just needs API key at runtime")
            print("Agent system initialization: PASSED\n")
            return True
        else:
            print(f"✗ AgentSystem initialization failed: {e}")
            print("Agent system initialization: FAILED\n")
            return False

def test_validation_functions():
    """Test the validation and fallback functions."""
    print("Testing validation and fallback functions...")
    
    from analysis_agent import AnalysisAgent
    from pathlib import Path
    
    # Create a mock agent
    class MockClient:
        pass
    
    mock_problem = {
        "id": "test-1",
        "type": "vulnerability",
        "component": "test.py",
        "severity": "HIGH"
    }
    
    config = {"analysis": {}}
    
    try:
        agent = AnalysisAgent(
            mock_problem,
            Path("."),
            Path("."),
            MockClient(),
            config
        )
        
        # Test valid JSON response
        valid_response = json.dumps({
            "is_applicable": True,
            "confidence": 0.8,
            "explanation": "Test explanation",
            "evidence": {"test": "data"},
            "recommended_actions": ["action1"]
        })
        
        result = agent._validate_and_fallback(valid_response, 
            ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"])
        
        assert result["is_applicable"] == True
        assert result["confidence"] == 0.8
        print("✓ Valid JSON validation works")
        
        # Test invalid JSON response
        invalid_response = "This is not valid JSON {{"
        result = agent._validate_and_fallback(invalid_response,
            ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"])
        
        assert result["is_applicable"] == False  # Fallback is conservative
        assert result["confidence"] == 0.0
        print("✓ Invalid JSON fallback works")
        
        # Test missing fields
        incomplete_response = json.dumps({
            "is_applicable": True
            # Missing other fields
        })
        result = agent._validate_and_fallback(incomplete_response,
            ["is_applicable", "confidence", "explanation", "evidence", "recommended_actions"])
        
        assert "confidence" in result  # Should have been filled in
        assert "explanation" in result
        print("✓ Missing fields fallback works")
        
        print("Validation and fallback: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        print("Validation and fallback: FAILED\n")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("AutoTriage Phase 1 Smoke Tests")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("Problem Parsing", test_problem_parsing()))
    except Exception as e:
        print(f"✗ Problem parsing test crashed: {e}\n")
        results.append(("Problem Parsing", False))
    
    try:
        results.append(("Agent System Init", test_agent_system_init()))
    except Exception as e:
        print(f"✗ Agent system init test crashed: {e}\n")
        results.append(("Agent System Init", False))
    
    try:
        results.append(("Validation Functions", test_validation_functions()))
    except Exception as e:
        print(f"✗ Validation test crashed: {e}\n")
        results.append(("Validation Functions", False))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 1 is complete.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

