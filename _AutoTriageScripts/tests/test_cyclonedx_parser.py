#!/usr/bin/env python3
"""
Quick test for CycloneDX parser
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import CycloneDXParser

def test_cyclonedx_parser():
    """Test CycloneDX parser with example SBOM"""
    print("Testing CycloneDX Parser...")
    
    # Try multiple possible paths
    test_paths = [
        Path("_example_output/CycloneDX/sbom.json"),
        Path("../_example_output/CycloneDX/sbom.json"),
    ]
    
    test_file = None
    for path in test_paths:
        if path.exists():
            test_file = path
            break
    
    if not test_file:
        print("❌ Test SBOM file not found")
        return False
    
    print(f"  Using SBOM file: {test_file}")
    
    try:
        # Parse with default config (no vulnerabilities expected)
        parser = CycloneDXParser()
        problems = parser.parse(test_file)
        
        print(f"  ✅ Parsed successfully")
        print(f"  Found {len(problems)} problems")
        
        if problems:
            print(f"  Sample problem: {problems[0].id}")
        else:
            print("  (SBOM has no vulnerabilities - this is expected)")
        
        # Also test with component parsing enabled
        parser_with_components = CycloneDXParser(config={"parse_components": True})
        problems_with_comps = parser_with_components.parse(test_file)
        print(f"  With components enabled: {len(problems_with_comps)} items")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cyclonedx_parser()
    sys.exit(0 if success else 1)

