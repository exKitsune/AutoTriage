#!/usr/bin/env python3
"""
Test modular tool system
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import get_all_tool_classes, get_tool_class, get_all_tool_metadata


def test_tool_discovery():
    """Test that tools are auto-discovered"""
    print("\n" + "="*60)
    print("TEST: Tool Auto-Discovery")
    print("="*60)
    
    tool_classes = get_all_tool_classes()
    
    print(f"Discovered {len(tool_classes)} tools:")
    for name, tool_class in tool_classes.items():
        print(f"  - {name}: {tool_class.__name__}")
    
    return len(tool_classes) > 0


def test_tool_metadata():
    """Test getting tool metadata"""
    print("\n" + "="*60)
    print("TEST: Tool Metadata")
    print("="*60)
    
    metadata = get_all_tool_metadata()
    
    print(f"Got metadata for {len(metadata)} tools:\n")
    for tool_meta in metadata:
        print(f"{tool_meta['name']}:")
        print(f"  Description: {tool_meta['description'][:60]}...")
        print(f"  Parameters: {list(tool_meta['parameters'].keys())}")
        print(f"  Requirements: {len(tool_meta['requirements'])} requirement(s)")
        print()
    
    return len(metadata) > 0


def test_tool_execution():
    """Test executing a tool"""
    print("\n" + "="*60)
    print("TEST: Tool Execution")
    print("="*60)
    
    # Get ReadFileTool
    tool_class = get_tool_class("read_file")
    print(f"Got tool class: {tool_class.__name__}")
    
    # Create instance
    workspace = Path.cwd()
    input_dir = Path.cwd() / "_example_output"
    tool = tool_class(workspace, input_dir)
    
    print(f"Created tool instance: {tool}")
    
    # Test with README.md
    result = tool.execute({"file_path": "README.md"})
    
    if result.get("success"):
        print(f"✅ Successfully read file")
        print(f"   Lines: {result['lines']}")
        print(f"   Content preview: {result['content'][:100]}...")
        return True
    else:
        print(f"❌ Failed: {result.get('error')}")
        return False


def test_tool_with_requirements():
    """Test tool with requirements (search_sbom)"""
    print("\n" + "="*60)
    print("TEST: Tool with Requirements")
    print("="*60)
    
    try:
        tool_class = get_tool_class("search_sbom")
        print(f"Got tool class: {tool_class.__name__}")
        
        # Check requirements
        print(f"Requirements:")
        for req in tool_class.requirements:
            print(f"  - {req['type']}: {req['path']}")
        
        return True
    except KeyError:
        print("❌ search_sbom tool not found")
        return False


def main():
    print("\n" + "="*60)
    print("MODULAR TOOL SYSTEM TEST")
    print("="*60)
    
    results = []
    results.append(("Discovery", test_tool_discovery()))
    results.append(("Metadata", test_tool_metadata()))
    results.append(("Execution", test_tool_execution()))
    results.append(("Requirements", test_tool_with_requirements()))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✅ All tests passed! Modular tool system works.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

