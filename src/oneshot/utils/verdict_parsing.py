"""
Verdict Parsing Utilities

Functions for extracting auditor verdicts from text.
"""

import json
import re
from .json_parsing import extract_json

def parse_json_verdict(text):
    """
    Parse JSON verdict from text and return tuple (verdict, reason, advice).
    Returns (None, None, None) if parsing fails.
    """
    json_str = extract_json(text)
    if not json_str:
        return (None, None, None)

    try:
        json_obj = json.loads(json_str)
        verdict = json_obj.get('verdict')
        reason = json_obj.get('reason', '')
        advice = json_obj.get('advice', '')
        return (verdict, reason, advice)
    except (json.JSONDecodeError, TypeError):
        return (None, None, None)


def parse_lenient_verdict(text):
    """
    Parse verdict leniently from text and return tuple (verdict, reason, advice).
    Handles various formats: strict JSON, embedded patterns, plain completion words.
    Returns (None, None, None) if no verdict found.
    """
    if not text:
        return (None, None, None)

    # Try strict JSON first
    json_str = extract_json(text)
    if json_str:
        try:
            json_obj = json.loads(json_str)
            verdict = json_obj.get('verdict')
            if verdict:
                # Uppercase verdict
                verdict = verdict.upper() if isinstance(verdict, str) else str(verdict).upper()
                reason = json_obj.get('reason', '')
                advice = json_obj.get('advice', '')
                return (verdict, reason, advice)
        except (json.JSONDecodeError, TypeError):
            pass

    # Try to find "verdict": "VALUE" pattern
    verdict_pattern = r'"verdict"\s*:\s*"([^"]+)"'
    match = re.search(verdict_pattern, text, re.IGNORECASE)
    if match:
        verdict = match.group(1).upper()
        # Try to find reason in the same JSON-like structure
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text, re.IGNORECASE)
        reason = reason_match.group(1) if reason_match else ""
        advice_match = re.search(r'"advice"\s*:\s*"([^"]*)"', text, re.IGNORECASE)
        advice = advice_match.group(1) if advice_match else ""
        return (verdict, reason, advice)

    # Try to find "status": "VALUE" pattern
    status_pattern = r'"status"\s*:\s*"([^"]+)"'
    match = re.search(status_pattern, text, re.IGNORECASE)
    if match:
        verdict = match.group(1).upper()
        reason = "Parsed from status completion indicator"
        return (verdict, reason, "")

    # Try malformed JSON with completion indicators (like {verdict: "DONE", reason: "Completed successfully"})
    # Check this BEFORE plain completion words to avoid false matches
    malformed_pattern = r'verdict\s*:\s*["\']([^"\']+)["\']'
    match = re.search(malformed_pattern, text, re.IGNORECASE)
    if match:
        verdict = match.group(1).upper()
        reason_match = re.search(r'reason\s*:\s*["\']([^"\']*)["\']', text, re.IGNORECASE)
        reason = reason_match.group(1) if reason_match else ""
        return (verdict, reason, "")

    # Try plain completion words (last resort)
    completion_keywords = ['done', 'complete', 'completed', 'finished', 'success', 'successful']
    text_lower = text.lower()
    for keyword in completion_keywords:
        if keyword in text_lower:
            verdict = "DONE"
            reason = f"Parsed from completion indicator: {keyword}"
            return (verdict, reason, "")

    return (None, None, None)
