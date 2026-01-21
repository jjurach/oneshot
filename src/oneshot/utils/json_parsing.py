"""
JSON Parsing Utilities

Functions for extracting and parsing JSON from LLM output.
"""

import json
import re

def extract_json(text):
    """
    Extract JSON from text and return the raw JSON string with preserved formatting.
    Returns the first valid JSON object or array found in the text as a string.
    Includes leading whitespace from the line containing the JSON.
    """
    # Find JSON objects using a more sophisticated approach
    # Look for balanced braces starting with { or [
    def find_json_candidates(text):
        candidates = []
        start = 0
        while start < len(text):
            # Find potential start of JSON
            brace_start = text.find('{', start)
            bracket_start = text.find('[', start)

            if brace_start == -1 and bracket_start == -1:
                break

            # Choose the earlier one
            if brace_start == -1:
                json_start = bracket_start
                start_char = '['
                end_char = ']'
            elif bracket_start == -1:
                json_start = brace_start
                start_char = '{'
                end_char = '}'
            else:
                json_start = min(brace_start, bracket_start)
                start_char = text[json_start]
                end_char = '}' if start_char == '{' else ']'

            # Back up to start of line for leading whitespace
            line_start = json_start
            while line_start > 0 and text[line_start-1] not in '\n\r':
                line_start -= 1

            # Find the matching end
            brace_count = 0
            for i in range(json_start, len(text)):
                if text[i] == start_char:
                    brace_count += 1
                elif text[i] == end_char:
                    brace_count -= 1
                    if brace_count == 0:
                        candidates.append(text[line_start:i+1])
                        start = i + 1
                        break
            else:
                start = json_start + 1

        return candidates

    # Try each candidate
    for candidate in find_json_candidates(text):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue

    # Try parsing the entire text as JSON
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        return None


def contains_completion_indicators(text):
    """
    Check if text contains completion indicators.
    Returns True if text indicates task completion.
    """
    completion_keywords = [
        'complete', 'done', 'finished', 'success',
        'accomplished', 'resolved', 'achieved',
        'final', 'concluded', 'finished'
    ]

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in completion_keywords)


def extract_lenient_json(text):
    """
    Extract JSON leniently from text and return tuple (result, method).
    Handles various formats with fallback strategies.
    Returns (None, None) if extraction fails.
    """
    if not text:
        return (None, None)

    # Try strict JSON extraction first
    json_str = extract_json(text)
    if json_str:
        try:
            result = json.loads(json_str)
            return (result, "strict")
        except json.JSONDecodeError:
            pass

    # Try fixing common JSON issues (like trailing commas)
    def try_fix_json(text):
        # Remove trailing commas before } or ]
        fixed = re.sub(r',\s*([}\]])', r'\1', text)
        try:
            result = json.loads(fixed)
            return (result, "fixed")
        except json.JSONDecodeError:
            return None

    fixed_result = try_fix_json(text)
    if fixed_result:
        return fixed_result

    # Try lenient fallback - extract simple key-value pairs
    def lenient_extract(text):
        # Look for patterns like "key": "value" or key: "value"
        patterns = [
            r'"([^"\\]+)"\s*:\s*"([^"\\]*)"',
            r'([^:\s]+)\s*:\s*"([^"\\]*)"',
            r'"([^"\\]+)"\s*:\s*([^,\s}]+)',
            r'([^:\s]+)\s*:\s*([^,\s}]+)',
        ]

        result = {}
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                key, value = match.groups()
                # Try to parse value as JSON
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_value = value.strip('"')
                result[key.strip('"')] = parsed_value

        return result if result else None

    lenient_result = lenient_extract(text)
    if lenient_result:
        return (lenient_result, "lenient_fallback")

    # Try extracting from markdown code blocks
    code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
    matches = re.finditer(code_block_pattern, text, re.DOTALL)
    for match in matches:
        try:
            result = json.loads(match.group(1))
            return (result, "code_block")
        except json.JSONDecodeError:
            continue

    # Final fallback: if text contains completion indicators, create a simple result
    if contains_completion_indicators(text):
        return ({"status": "completed", "method": "fallback"}, "lenient_fallback")

    return (None, None)
