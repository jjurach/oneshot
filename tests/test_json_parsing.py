"""Tests for JSON parsing and extraction functionality."""

import pytest
from oneshot.oneshot import (
    extract_json,
    parse_json_verdict,
    contains_completion_indicators,
    extract_lenient_json
)


class TestExtractJson:
    """Test JSON extraction from text."""

    def test_extract_valid_json(self):
        """Test extracting valid JSON from text."""
        text = '''Some text
{
  "key": "value"
}
more text'''
        result = extract_json(text)
        assert result == '{\n  "key": "value"\n}'

    def test_extract_multiline_json(self):
        """Test extracting multiline JSON."""
        text = '''Some text
        {
            "key": "value",
            "number": 42
        }
        more text'''
        result = extract_json(text)
        expected = '''        {
            "key": "value",
            "number": 42
        }'''
        assert result == expected

    def test_extract_no_json(self):
        """Test when no JSON is found."""
        text = "Just plain text without JSON"
        result = extract_json(text)
        assert result is None


class TestParseJsonVerdict:
    """Test parsing auditor verdict from JSON."""

    def test_parse_valid_verdict(self):
        """Test parsing valid verdict JSON."""
        json_text = '{"verdict": "DONE", "reason": "Task completed successfully"}'
        verdict, reason, advice = parse_json_verdict(json_text)
        assert verdict == "DONE"
        assert reason == "Task completed successfully"
        assert advice == ""

    def test_parse_verdict_with_advice(self):
        """Test parsing verdict JSON with advice."""
        json_text = '{"verdict": "REITERATE", "reason": "Need more work", "advice": "Try again"}'
        verdict, reason, advice = parse_json_verdict(json_text)
        assert verdict == "REITERATE"
        assert reason == "Need more work"
        assert advice == "Try again"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        json_text = "not json"
        verdict, reason, advice = parse_json_verdict(json_text)
        assert verdict is None
        assert reason is None
        assert advice is None


class TestLenientJsonParsing:
    """Test lenient JSON parsing with completion indicators."""

    def test_contains_completion_indicators_done(self):
        """Test detection of completion indicators."""
        text = "Task is DONE"
        assert contains_completion_indicators(text) is True

    def test_contains_completion_indicators_false(self):
        """Test when no completion indicators are present."""
        text = "Still working on it"
        assert contains_completion_indicators(text) is False

    def test_extract_lenient_json_strict(self):
        """Test lenient extraction with valid JSON."""
        text = '{"status": "success"}'
        result, method = extract_lenient_json(text)
        assert result is not None
        assert method == "strict"

    def test_extract_lenient_json_fixed(self):
        """Test lenient extraction with fixable JSON."""
        text = '{"status": "success",}'  # Trailing comma
        result, method = extract_lenient_json(text)
        assert result is not None
        assert method in ["strict", "lenient_fallback", "fixed"]

    def test_extract_lenient_json_malformed(self):
        """Test lenient fallback for malformed JSON."""
        text = '{status: "success", result: "Task completed"}'
        result, method = extract_lenient_json(text)
        assert result is not None
        assert method == "lenient_fallback"

    def test_extract_lenient_json_plain_text(self):
        """Test lenient fallback for plain text with completion indicators."""
        text = "Working on the task and DONE"
        result, method = extract_lenient_json(text)
        assert result is not None
        assert method == "lenient_fallback"
