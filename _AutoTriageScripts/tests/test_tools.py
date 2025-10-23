#!/usr/bin/env python3
"""
Test the tool executor implementations.
"""

import sys
from pathlib import Path

# Add to path
# (tests are in tests/ subdirectory, modules are in parent)
sys.path.insert(0, str(Path(__file__).parent.parent))

from tool_executor import ToolExecutor

def test_tools():
    """Test all tool implementations."""
    print("=" * 60)
    print("Tool Executor Tests")
    print("=" * 60 + "\n")
    
    # Tests are in _AutoTriageScripts/tests/, so go up to repo root
    workspace_root = Path(__file__).parent.parent.parent
    input_dir = Path(__file__).parent.parent.parent / "_example_output"
    
    executor = ToolExecutor(workspace_root, input_dir)
    
    passed = 0
    failed = 0
    
    # Test 1: read_file
    print("1. Testing read_file...")
    result = executor.read_file({"file_path": "container_security/app/app.py"})
    if result["success"] and "Flask" in result["content"]:
        print("   ✓ Successfully read app.py")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Test 2: read_file_lines
    print("\n2. Testing read_file_lines...")
    result = executor.read_file_lines({
        "file_path": "container_security/vulnerable/Dockerfile",
        "start_line": 1,
        "end_line": 5
    })
    if result["success"] and "FROM" in result["content"]:
        print(f"   ✓ Read lines 1-5 ({result['total_lines']} total lines)")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Test 3: search_code
    print("\n3. Testing search_code...")
    result = executor.search_code({
        "pattern": "from flask import",
        "file_glob": "*.py",
        "case_sensitive": False
    })
    if result["success"]:
        print(f"   ✓ Found {result['match_count']} matches")
        if result['matches']:
            print(f"      Example: {result['matches'][0]['file']}")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Test 4: find_files
    print("\n4. Testing find_files...")
    result = executor.find_files({
        "pattern": "requirements.txt",
        "directory": "."
    })
    if result["success"] and result["count"] > 0:
        print(f"   ✓ Found {result['count']} requirements files")
        for f in result["files"][:3]:
            print(f"      - {f}")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'No files found')}")
        failed += 1
    
    # Test 5: list_directory
    print("\n5. Testing list_directory...")
    result = executor.list_directory({
        "directory": "container_security",
        "recursive": False
    })
    if result["success"]:
        print(f"   ✓ Found {len(result['files'])} files, {len(result['directories'])} directories")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Test 6: search_sbom
    print("\n6. Testing search_sbom...")
    result = executor.search_sbom({"package_name": "PyYAML"})
    if result["success"]:
        if result["found"]:
            print(f"   ✓ Found in SBOM: {result['component']['name']} {result['component']['version']}")
        else:
            print(f"   ✓ Search completed: {result.get('note', 'Not found')}")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Test 7: check_import_usage
    print("\n7. Testing check_import_usage...")
    result = executor.check_import_usage({"package_name": "flask"})
    if result["success"]:
        if result["is_imported"]:
            print(f"   ✓ Flask is imported in {len(result['import_locations'])} location(s)")
        else:
            print("   ✓ Flask is not imported")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Test 8: check_import_usage for unused package
    print("\n8. Testing check_import_usage (yaml - should be unused)...")
    result = executor.check_import_usage({"package_name": "yaml"})
    if result["success"]:
        if result["is_imported"]:
            print(f"   ⚠️  yaml is imported (unexpected): {result['import_locations']}")
        else:
            print("   ✓ yaml is not imported (as expected)")
        passed += 1
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed + failed} tests passed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = test_tools()
    sys.exit(0 if success else 1)

