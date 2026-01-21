"""Tests for JSON parsing and extraction functionality."""

import pytest
from oneshot.utils.json_parsing import (
    extract_json,
    contains_completion_indicators,
    extract_lenient_json
)
from oneshot.utils.verdict_parsing import (
    parse_json_verdict,
    parse_lenient_verdict
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


class TestParseLenientVerdict:
    """Test lenient verdict parsing from auditor responses."""

    def test_parse_lenient_verdict_valid_json(self):
        """Test parsing valid JSON verdict."""
        text = '{"verdict": "DONE", "reason": "Task completed"}'
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"
        assert reason == "Task completed"
        assert advice == ""

    def test_parse_lenient_verdict_verdict_pattern(self):
        """Test parsing verdict from "verdict": "DONE" pattern."""
        text = 'The task is complete. {"verdict": "DONE", "reason": "All requirements met"}'
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"
        assert reason == "All requirements met"
        assert advice == ""

    def test_parse_lenient_verdict_status_pattern_same_line(self):
        """Test parsing from "status": "DONE" on same line (user's specific request)."""
        text = 'Task completed successfully. Line with "status": "DONE" and more text.'
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"
        assert reason == "Parsed from status completion indicator"
        assert advice == ""

    def test_parse_lenient_verdict_status_pattern_multiline(self):
        """Test parsing from "status": "DONE" across lines."""
        text = '''Task evaluation:
"status": "DONE"
The task has been completed.'''
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"
        assert reason == "Parsed from status completion indicator"
        assert advice == ""

    def test_parse_lenient_verdict_plain_completion_words(self):
        """Test parsing from plain completion words."""
        text = "The task is now complete and DONE."
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"
        assert reason == "Parsed from completion indicator: done"
        assert advice == ""

    def test_parse_lenient_verdict_reiterate(self):
        """Test parsing REITERATE verdict."""
        text = '{"verdict": "REITERATE", "reason": "Need more work"}'
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "REITERATE"
        assert reason == "Need more work"
        assert advice == ""

    def test_parse_lenient_verdict_case_insensitive(self):
        """Test case insensitive parsing."""
        text = '{"verdict": "done", "reason": "Task finished"}'
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"  # Should be uppercased
        assert reason == "Task finished"
        assert advice == ""

    def test_parse_lenient_verdict_no_verdict_found(self):
        """Test when no verdict can be extracted."""
        text = "This is just some random text with no completion indicators."
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict is None
        assert reason is None
        assert advice is None

    def test_parse_lenient_verdict_malformed_json_with_indicators(self):
        """Test parsing malformed JSON that contains completion indicators."""
        text = '{verdict: "DONE", reason: "Completed successfully"}'
        verdict, reason, advice = parse_lenient_verdict(text)
        assert verdict == "DONE"
        assert reason == "Completed successfully"
        assert advice == ""


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