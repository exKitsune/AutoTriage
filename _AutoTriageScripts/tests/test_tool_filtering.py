#!/usr/bin/env python3
"""
Test tool availability filtering
"""

import sys
import json
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tool_availability import ToolAvailabilityChecker, load_tools_with_requirements


def setup_test_environment():
    """Create test-inputs directory with dummy SBOM"""
    test_inputs = Path.cwd() / "test-inputs"
    sbom_dir = test_inputs / "sbom"
    sbom_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dummy SBOM
    dummy_sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "components": []
    }
    
    with open(sbom_dir / "sbom.json", "w") as f:
        json.dump(dummy_sbom, f)
    
    return test_inputs


def cleanup_test_environment():
    """Remove test-inputs directory"""
    test_inputs = Path.cwd() / "test-inputs"
    if test_inputs.exists():
        shutil.rmtree(test_inputs)


def test_with_sbom():
    """Test when SBOM file exists"""
    print("\n" + "="*60)
    print("TEST 1: With SBOM present")
    print("="*60)
    
    # Use test inputs directory (created by test setup)
    workspace_root = Path.cwd()
    input_dir = workspace_root / "test-inputs"
    
    checker = ToolAvailabilityChecker(workspace_root, input_dir)
    all_tools = load_tools_with_requirements()
    
    available = checker.get_available_tools(all_tools)
    unavailable = checker.get_unavailable_tool_names(all_tools)
    
    print(f"Total tools: {len(all_tools)}")
    print(f"Available tools: {len(available)}")
    print(f"Filtered out: {len(unavailable)}")
    
    if unavailable:
        print(f"Unavailable tools: {', '.join(unavailable)}")
    
    # Check if search_sbom is available
    search_sbom_available = any(t["name"] == "search_sbom" for t in available)
    
    if search_sbom_available:
        print("✅ search_sbom is AVAILABLE (SBOM file exists)")
    else:
        print("❌ search_sbom is NOT available (SBOM file missing)")
    
    return search_sbom_available


def test_without_sbom():
    """Test when SBOM file does NOT exist"""
    print("\n" + "="*60)
    print("TEST 2: Without SBOM")
    print("="*60)
    
    # Use path where SBOM doesn't exist
    workspace_root = Path.cwd()
    input_dir = workspace_root / "nonexistent_dir"
    
    checker = ToolAvailabilityChecker(workspace_root, input_dir)
    all_tools = load_tools_with_requirements()
    
    available = checker.get_available_tools(all_tools)
    unavailable = checker.get_unavailable_tool_names(all_tools)
    
    print(f"Total tools: {len(all_tools)}")
    print(f"Available tools: {len(available)}")
    print(f"Filtered out: {len(unavailable)}")
    
    if unavailable:
        print(f"Unavailable tools: {', '.join(unavailable)}")
    
    # Check if search_sbom is filtered out
    search_sbom_available = any(t["name"] == "search_sbom" for t in available)
    
    if search_sbom_available:
        print("❌ search_sbom is AVAILABLE (should be filtered!)")
    else:
        print("✅ search_sbom is FILTERED OUT (SBOM file missing)")
    
    return not search_sbom_available


def test_requirement_details():
    """Show what requirements are defined"""
    print("\n" + "="*60)
    print("TEST 3: Tool Requirements")
    print("="*60)
    
    all_tools = load_tools_with_requirements()
    
    tools_with_reqs = [t for t in all_tools if t.get("requirements")]
    
    print(f"Tools with requirements: {len(tools_with_reqs)}")
    
    for tool in tools_with_reqs:
        print(f"\n{tool['name']}:")
        for req in tool["requirements"]:
            print(f"  - {req['type']}: {req.get('path', req.get('name', 'N/A'))}")
            if "description" in req:
                print(f"    {req['description']}")


def main():
    print("\n" + "="*60)
    print("TOOL FILTERING TEST")
    print("="*60)
    print("Testing dynamic tool availability filtering")
    
    # Setup test environment
    setup_test_environment()
    
    try:
        test_requirement_details()
        result1 = test_with_sbom()
        result2 = test_without_sbom()
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        if result1 and result2:
            print("✅ All tests passed!")
            print("   - SBOM present: search_sbom available")
            print("   - SBOM missing: search_sbom filtered out")
            return 0
        else:
            print("❌ Some tests failed")
            return 1
    finally:
        # Cleanup test environment
        cleanup_test_environment()


if __name__ == "__main__":
    sys.exit(main())

