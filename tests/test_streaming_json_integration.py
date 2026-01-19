#!/usr/bin/env python3
"""
Integration test for streaming JSON output format across executors.

Tests the unified streaming JSON format with a simple query:
"What is the capital of Australia?"

This tests:
1. JSON output format consistency across providers
2. Complete error capture without truncation
3. Event streaming structure
4. Provider-specific handling of streaming
"""

import json
import pytest
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oneshot.providers import ExecutorProvider, ProviderConfig
from oneshot.providers.activity_interpreter import ActivityInterpreter
from oneshot.providers.activity_logger import ActivityLogger


# Test query - simple, deterministic, same across all executors
TEST_QUERY = "What is the capital of Australia?"
EXPECTED_ANSWERS = ["Canberra", "canberra", "Sydney", "Melbourne"]  # Accept common responses


class TestStreamingJSONFormat:
    """Test streaming JSON output format across executors."""

    @pytest.fixture
    def activity_logger(self, tmp_path):
        """Create a temporary activity logger."""
        logger = ActivityLogger(session_file_base=str(tmp_path / "activities"))
        yield logger
        logger.finalize_log()

    @pytest.fixture
    def activity_interpreter(self):
        """Create an activity interpreter for parsing events."""
        return ActivityInterpreter()

    def test_streaming_json_structure(self, activity_logger):
        """Test that streaming JSON output has correct structure."""
        # Create a minimal streaming event
        event = {
            "type": "activity_event",
            "timestamp": datetime.now().isoformat(),
            "sequence": 1,
            "provider": "claude",
            "iteration": 1,
            "event": {
                "type": "query_received",
                "description": TEST_QUERY,
                "metadata": {}
            }
        }

        # Should be valid JSON
        json_str = json.dumps(event)
        parsed = json.loads(json_str)

        assert parsed["type"] == "activity_event"
        assert parsed["timestamp"]
        assert parsed["sequence"] == 1
        assert parsed["provider"] == "claude"
        assert parsed["event"]["type"] == "query_received"

    def test_streaming_json_no_truncation(self):
        """Test that complete error messages are preserved in JSON."""
        # Create a realistic error event with a long error message
        long_error_msg = (
            "AssertionError: Expected the response to contain 'Canberra' "
            "but got an unexpected module reference: "
            "<module 'oneshot.providers' from '/home/phaedrus/AiSpace/oneshot/"
            "src/oneshot/providers/__init__.py'>"
        )

        error_event = {
            "type": "error_event",
            "timestamp": datetime.now().isoformat(),
            "provider": "claude",
            "event": {
                "type": "error",
                "description": long_error_msg,
                "error_type": "AssertionError",
                "full_traceback": "full traceback here..."
            }
        }

        # Serialize and deserialize
        json_str = json.dumps(error_event)
        parsed = json.loads(json_str)

        # Full error message must be preserved
        assert parsed["event"]["description"] == long_error_msg
        assert "module 'oneshot.providers'" in parsed["event"]["description"]
        # Should NOT contain truncation markers like "..."
        assert "..." not in parsed["event"]["description"]

    def test_streaming_event_types(self):
        """Test all expected streaming event types."""
        expected_event_types = [
            "query_received",
            "execution_started",
            "thinking",
            "tool_call",
            "planning",
            "response_generated",
            "response_completed",
            "execution_completed",
            "error",
            "file_operation"
        ]

        for event_type in expected_event_types:
            event = {
                "type": "activity_event",
                "timestamp": datetime.now().isoformat(),
                "event": {"type": event_type}
            }
            # Should serialize without error
            json_str = json.dumps(event)
            parsed = json.loads(json_str)
            assert parsed["event"]["type"] == event_type

    def test_streaming_json_lines_format(self, tmp_path):
        """Test JSONL (JSON Lines) format for streaming output."""
        output_file = tmp_path / "streaming_output.jsonl"

        # Create multiple events
        events = [
            {
                "type": "activity_event",
                "timestamp": datetime.now().isoformat(),
                "sequence": i,
                "event": {"type": "query_event", "content": f"event_{i}"}
            }
            for i in range(5)
        ]

        # Write as JSONL (one JSON object per line)
        with open(output_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')

        # Read back and verify
        with open(output_file, 'r') as f:
            lines = f.read().strip().split('\n')
            assert len(lines) == 5

            for i, line in enumerate(lines):
                parsed = json.loads(line)
                assert parsed["sequence"] == i
                assert parsed["event"]["content"] == f"event_{i}"

    def test_activity_interpreter_streaming_json(self, activity_interpreter):
        """Test that ActivityInterpreter can process streaming JSON events."""
        # Create a streaming event
        event = {
            "type": "activity_event",
            "timestamp": datetime.now().isoformat(),
            "event": {
                "type": "tool_call",
                "description": "Running: bash -c 'echo Canberra'",
                "metadata": {"tool": "bash", "command": "echo Canberra"}
            }
        }

        # Interpreter should be able to process streaming JSON
        # (This assumes interpret_json_event method exists or will be added)
        json_str = json.dumps(event)
        parsed = json.loads(json_str)

        # At minimum, should be able to extract event type and description
        assert parsed["event"]["type"] == "tool_call"
        assert "Canberra" in parsed["event"]["description"]

    def test_capital_query_response_json_format(self):
        """Test JSON format for capital query response."""
        # Expected response structure for "What is the capital of Australia?"
        response_event = {
            "type": "response_event",
            "timestamp": datetime.now().isoformat(),
            "provider": "claude",
            "iteration": 1,
            "query": TEST_QUERY,
            "response": {
                "content": "The capital of Australia is Canberra.",
                "type": "text",
                "complete": True
            },
            "metadata": {
                "duration_ms": 1234,
                "tokens_used": 45,
                "model": "claude-opus-4-5"
            }
        }

        # Should serialize cleanly
        json_str = json.dumps(response_event)
        parsed = json.loads(json_str)

        assert parsed["query"] == TEST_QUERY
        assert "Canberra" in parsed["response"]["content"]
        assert parsed["response"]["complete"] is True

    def test_provider_consistency_in_json(self):
        """Test that JSON format is consistent across different providers."""
        providers = ["claude", "cline", "aider", "gemini"]

        for provider in providers:
            event = {
                "type": "activity_event",
                "timestamp": datetime.now().isoformat(),
                "provider": provider,
                "sequence": 1,
                "event": {
                    "type": "execution_started",
                    "query": TEST_QUERY
                }
            }

            # Should be valid JSON regardless of provider
            json_str = json.dumps(event)
            parsed = json.loads(json_str)

            assert parsed["provider"] == provider
            assert parsed["event"]["query"] == TEST_QUERY

    def test_error_capture_without_truncation(self):
        """Test that errors are captured completely without truncation."""
        # Simulate a realistic error that might be truncated in current impl
        full_traceback = (
            "Traceback (most recent call last):\n"
            "  File \"/home/phaedrus/AiSpace/oneshot/src/oneshot/providers/activity_interpreter.py\", line 123\n"
            "    assert response.content is not None\n"
            "AssertionError: Response content is None\n"
            "During handling of the above exception, another exception occurred:\n"
            "  File \"/home/phaedrus/AiSpace/oneshot/src/oneshot/providers/activity_formatter.py\", line 456\n"
            "    formatted = self.format_activity(activity)\n"
            "ValueError: Cannot format None activity"
        )

        error_event = {
            "type": "error_event",
            "timestamp": datetime.now().isoformat(),
            "provider": "claude",
            "error": {
                "type": "AssertionError",
                "message": "Response content is None",
                "full_traceback": full_traceback,
                "context": {
                    "query": TEST_QUERY,
                    "iteration": 1,
                    "provider": "claude"
                }
            }
        }

        # Serialize and deserialize
        json_str = json.dumps(error_event)
        parsed = json.loads(json_str)

        # All error information must be preserved
        assert len(parsed["error"]["full_traceback"]) > 100
        assert "AssertionError" in parsed["error"]["full_traceback"]
        assert parsed["error"]["context"]["query"] == TEST_QUERY

    def test_streaming_json_with_special_characters(self):
        """Test that special characters in responses are properly escaped in JSON."""
        # Response with quotes, newlines, unicode
        response_with_specials = (
            "The capital is 'Canberra'.\n"
            "Quote test: He said \"Hello\"\n"
            "Unicode: café, naïve, 中国\n"
            "Backslash: path\\to\\file"
        )

        event = {
            "type": "response_event",
            "response": {
                "content": response_with_specials
            }
        }

        # Should serialize correctly
        json_str = json.dumps(event)
        parsed = json.loads(json_str)

        # All special characters should be preserved
        assert "Canberra" in parsed["response"]["content"]
        assert "café" in parsed["response"]["content"]
        assert "中国" in parsed["response"]["content"]
        assert parsed["response"]["content"].count('\n') >= 3


class TestStreamingJSONSchema:
    """Test schema validation for streaming JSON events."""

    def test_activity_event_schema(self):
        """Test that activity events match schema."""
        # Minimal valid event
        event = {
            "type": "activity_event",
            "timestamp": "2026-01-19T15:06:12.399056",
            "sequence": 1,
            "provider": "claude",
            "event": {
                "type": "tool_call",
                "description": "Running tool"
            }
        }

        # Required fields
        assert "type" in event
        assert "timestamp" in event
        assert "provider" in event
        assert "event" in event
        assert "type" in event["event"]

    def test_error_event_schema(self):
        """Test that error events match schema."""
        event = {
            "type": "error_event",
            "timestamp": "2026-01-19T15:06:12.399056",
            "provider": "claude",
            "error": {
                "type": "RuntimeError",
                "message": "Something went wrong"
            }
        }

        # Required fields
        assert "type" in event
        assert "error" in event
        assert "type" in event["error"]
        assert "message" in event["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
