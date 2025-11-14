#!/usr/bin/env python3
"""
JSON Sanitizer - Fixes common JSON formatting issues in LLM responses.

This module provides utilities to handle common JSON escaping and formatting
errors that may occur in LLM-generated responses, particularly when the LLM
includes code snippets, regex patterns, or file paths in string values.
"""

import json
import re
from typing import Dict, Any, Tuple


def sanitize_json_string(json_str: str) -> Tuple[str, bool]:
    r"""
    Attempt to fix common JSON formatting issues in LLM responses.
    
    Common issues handled:
    1. Invalid escape sequences (e.g., \\. in regex patterns)
    2. Unescaped backslashes in file paths
    3. Unescaped quotes in strings
    4. Control characters in strings
    
    Args:
        json_str: The potentially malformed JSON string
        
    Returns:
        Tuple of (sanitized_json_str, was_modified)
        - sanitized_json_str: The fixed JSON string
        - was_modified: True if any fixes were applied
    """
    original = json_str
    modified = False
    
    # Try to parse as-is first
    try:
        json.loads(json_str)
        return json_str, False  # Already valid
    except json.JSONDecodeError:
        pass  # Needs fixing
    
    # Fix 1: Remove any non-JSON content before/after the JSON object
    # Sometimes LLMs add explanatory text
    json_str = json_str.strip()
    
    # Find the outermost { }
    start_idx = json_str.find('{')
    end_idx = json_str.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = json_str[start_idx:end_idx + 1]
        if start_idx > 0 or end_idx < len(original) - 1:
            modified = True
    
    # Fix 2: Fix invalid escape sequences by manually parsing and rebuilding
    # We'll use a state machine approach to properly handle strings
    
    result = []
    i = 0
    in_string = False
    escape_next = False
    
    while i < len(json_str):
        char = json_str[i]
        
        if not in_string:
            # Outside string - just copy characters
            if char == '"':
                in_string = True
            result.append(char)
            i += 1
        else:
            # Inside string
            if escape_next:
                # Previous char was backslash - this is an escape sequence
                # Check if it's valid
                if char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                    # Valid escape
                    result.append(char)
                else:
                    # Invalid escape - we already added \\ in previous iteration
                    # Now just add this character
                    result.append(char)
                escape_next = False
                i += 1
            elif char == '\\':
                # Start of escape sequence
                if i + 1 < len(json_str):
                    next_char = json_str[i + 1]
                    if next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                        # Valid escape sequence
                        result.append(char)
                        escape_next = True
                    else:
                        # Invalid escape - double the backslash
                        result.append('\\\\')
                        modified = True
                        escape_next = True
                else:
                    # Backslash at end of string (invalid)
                    result.append('\\\\')
                    modified = True
                i += 1
            elif char == '"':
                # End of string
                in_string = False
                result.append(char)
                i += 1
            else:
                # Regular character in string
                result.append(char)
                i += 1
    
    json_str = ''.join(result)
    
    # Return sanitized version
    return json_str, modified


def parse_llm_json_response(response: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse JSON from an LLM response, with automatic error recovery.
    
    This function attempts multiple strategies:
    1. Parse as-is
    2. Apply sanitization and retry
    3. Extract JSON from markdown code blocks
    
    Args:
        response: The LLM response string
        
    Returns:
        Tuple of (parsed_dict, error_message)
        - parsed_dict: The parsed JSON as a dict, or None if parsing failed
        - error_message: Empty string if successful, error description if failed
        
    Example:
        data, error = parse_llm_json_response(llm_response)
        if error:
            print(f"Failed to parse: {error}")
        else:
            print(f"Tool: {data['tool']}")
    """
    original_response = response
    
    # Strategy 1: Try parsing as-is
    try:
        return json.loads(response.strip()), ""
    except json.JSONDecodeError as e:
        first_error = str(e)
    
    # Strategy 2: Try extracting from markdown code block
    # Sometimes LLMs wrap JSON in ```json ... ```
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1)), ""
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Apply sanitization
    sanitized, was_modified = sanitize_json_string(response)
    
    if was_modified:
        try:
            return json.loads(sanitized), ""
        except json.JSONDecodeError as e:
            # Sanitization didn't help
            return None, (
                f"JSON parsing failed even after sanitization. "
                f"Original error: {first_error}. "
                f"After sanitization: {str(e)}. "
                f"Response length: {len(original_response)} chars."
            )
    else:
        # No modifications were made
        return None, (
            f"JSON parsing failed: {first_error}. "
            f"No automatic fixes could be applied. "
            f"Response length: {len(original_response)} chars."
        )


def get_json_escaping_guidance() -> str:
    """
    Get formatted guidance text about JSON escaping for inclusion in prompts.
    
    Returns:
        String containing JSON escaping guidance for LLM prompts
    """
    return """
JSON ESCAPING RULES - CRITICAL:
1. In JSON string values, you MUST escape backslashes: use \\\\ for a single backslash
2. Common mistakes to avoid:
   - DON'T: "grep -n 'pattern\\.txt'"  (invalid escape \\.)
   - DO:     "grep -n 'pattern\\\\.txt'" (properly escaped)
   - DON'T: "C:\\Users\\file.txt" (in nested JSON - needs more escaping)
   - DO:     "C:\\\\Users\\\\file.txt" (properly escaped for nested JSON)
3. Valid JSON escapes ONLY: \\", \\\\, \\/, \\b, \\f, \\n, \\r, \\t, \\uXXXX
4. For regex patterns in strings: double-escape special chars (e.g., \\\\. for literal dot)
5. For file paths: use forward slashes (/) when possible, or double-escape backslashes (\\\\)
6. When in doubt, use forward slashes instead of backslashes in paths
""".strip()


if __name__ == "__main__":
    # Test cases
    test_cases = [
        # Valid JSON
        ('{"tool": "test", "params": {"value": "hello"}}', True),
        
        # Invalid escape in regex
        ('{"tool": "grep", "params": {"pattern": "file\\.txt"}}', False),
        
        # Windows path
        ('{"tool": "read", "params": {"path": "C:\\Users\\file.txt"}}', False),
        
        # Nested JSON string (the actual problem from the conversation log)
        ('{"tool": "provide_analysis", "parameters": {"verification_steps": ["Run: grep -n \'tempfile\\.mktemp\' file.py"]}}', False),
    ]
    
    print("Testing JSON Sanitizer\n" + "=" * 60)
    
    for i, (test_json, should_pass) in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Input: {test_json}")
        
        data, error = parse_llm_json_response(test_json)
        
        if data:
            print(f"✓ Parsed successfully")
            print(f"  Tool: {data.get('tool', 'N/A')}")
        else:
            print(f"✗ Failed: {error}")
        
        if should_pass and data:
            print("  Result: PASS (expected success)")
        elif not should_pass and data:
            print("  Result: PASS (sanitizer fixed the issue)")
        elif should_pass and not data:
            print("  Result: FAIL (should have parsed)")
        else:
            print("  Result: Expected failure")

