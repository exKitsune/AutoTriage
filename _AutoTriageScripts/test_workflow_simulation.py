#!/usr/bin/env python3
"""
Test that simulates the GitHub workflow to catch integration issues.
This test uses the example output files to simulate a real workflow run.
"""

import json
import sys
import os
from pathlib import Path

def test_workflow_simulation():
    """Simulate a workflow run with example data."""
    print("=" * 60)
    print("Workflow Simulation Test")
    print("=" * 60 + "\n")
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    example_input = project_root / "_example_output"
    test_output = project_root / "test-analysis-outputs"
    
    # Create test output directory
    test_output.mkdir(exist_ok=True)
    
    # Import the main function
    sys.path.insert(0, str(Path(__file__).parent))
    from analyze_dependencies import collect_problems, parse_arguments
    from analysis_agent import AgentSystem
    
    print("1. Testing problem collection...")
    
    # Create mock arguments
    class MockArgs:
        sonarqube = True
        dependency_check = True
    
    args = MockArgs()
    
    # Collect problems from example data
    try:
        problems = collect_problems(example_input, args)
        print(f"   ✓ Collected {len(problems)} problems from example data")
        
        # Verify we got some problems
        if len(problems) == 0:
            print("   ✗ No problems found!")
            return False
        
        # Check problem structure
        for i, problem in enumerate(problems[:2]):  # Check first 2
            print(f"   - Problem {i+1}: {problem.source} - {problem.type} - {problem.severity}")
        
    except Exception as e:
        print(f"   ✗ Failed to collect problems: {e}")
        return False
    
    print("\n2. Testing AgentSystem initialization...")
    
    config_dir = Path(__file__).parent / "config"
    workspace_root = project_root / "container_security"
    
    try:
        # This will fail due to missing API key, but that's expected
        agent_system = AgentSystem(workspace_root, example_input, config_dir)
        print(f"   ✓ AgentSystem initialized")
    except Exception as e:
        if "api_key" in str(e).lower():
            print(f"   ✓ AgentSystem init works (API key missing as expected)")
        else:
            print(f"   ✗ Unexpected error: {e}")
            return False
    
    print("\n3. Testing problem serialization...")
    
    # This is what caused the workflow failure - converting dataclasses to dicts
    from dataclasses import asdict
    
    try:
        problems_as_dicts = [asdict(p) for p in problems]
        print(f"   ✓ Converted {len(problems_as_dicts)} problems to dicts")
        
        # Verify dict structure
        test_problem = problems_as_dicts[0]
        required_fields = ['id', 'source', 'type', 'severity', 'component']
        missing = [f for f in required_fields if f not in test_problem]
        
        if missing:
            print(f"   ✗ Missing required fields: {missing}")
            return False
        
        print(f"   ✓ Problem dict has all required fields")
        
        # Test that the dict is subscriptable (this was the bug)
        test_id = test_problem['id']
        test_get = test_problem.get('line', None)
        print(f"   ✓ Problem dict is properly subscriptable")
        
    except Exception as e:
        print(f"   ✗ Failed to convert problems: {e}")
        return False
    
    print("\n4. Writing test problems file...")
    
    try:
        problems_file = test_output / "test_problems.json"
        with open(problems_file, 'w') as f:
            json.dump(problems_as_dicts, f, indent=2)
        print(f"   ✓ Wrote problems to {problems_file}")
    except Exception as e:
        print(f"   ✗ Failed to write problems: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Workflow simulation test PASSED")
    print("=" * 60)
    print("\nThe script should now work in the GitHub workflow!")
    print("(It will still need OPENROUTER_API_KEY to complete analysis)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_workflow_simulation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

