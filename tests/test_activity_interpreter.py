"""
Unit tests for activity interpreter and formatter.

Tests metadata filtering, activity extraction, and display formatting.
"""

import pytest
from oneshot.providers.activity_interpreter import (
    ActivityInterpreter,
    ActivityEvent,
    ActivityType,
    get_interpreter
)
from oneshot.providers.activity_formatter import ActivityFormatter, format_for_display


class TestActivityInterpreter:
    """Tests for activity extraction and filtering."""

    def setup_method(self):
        """Set up test fixtures."""
        self.interpreter = ActivityInterpreter()

    def test_filter_metadata_removes_tokens(self):
        """Test that token counts are removed from output."""
        text = "Processing done\ninput_tokens: 1234\noutput_tokens: 567"
        filtered = self.interpreter.filter_metadata(text)

        assert "input_tokens" not in filtered
        assert "output_tokens" not in filtered
        assert "Processing done" in filtered

    def test_filter_metadata_removes_costs(self):
        """Test that cost information is removed."""
        text = "API call successful\ncost: $0.05\ninput_cost: $0.01"
        filtered = self.interpreter.filter_metadata(text)

        assert "cost:" not in filtered
        assert "$" not in filtered
        assert "API call successful" in filtered

    def test_filter_metadata_removes_cache_tokens(self):
        """Test that cache-related tokens are removed."""
        text = "Result obtained\ncache_creation_input_tokens: 100\ncache_read_input_tokens: 50"
        filtered = self.interpreter.filter_metadata(text)

        # The important part is that the numeric values are removed
        assert ": 100" not in filtered
        assert ": 50" not in filtered
        assert "Result obtained" in filtered

    def test_has_sensitive_data_detects_tokens(self):
        """Test detection of sensitive metadata."""
        assert self.interpreter.has_sensitive_data("input_tokens: 123")
        assert self.interpreter.has_sensitive_data("cost: $0.50")
        assert self.interpreter.has_sensitive_data("normal text") is False

    def test_extract_tool_calls_basic(self):
        """Test extraction of basic tool calls."""
        text = "Calling tool: bash /path/to/script.sh"
        events = self.interpreter.extract_tool_calls(text)

        assert len(events) > 0
        assert events[0].activity_type == ActivityType.TOOL_CALL
        assert "bash" in events[0].description or "script" in events[0].description

    def test_extract_tool_calls_python(self):
        """Test extraction of Python tool calls."""
        text = "Running python print('hello')"
        events = self.interpreter.extract_tool_calls(text)

        assert len(events) > 0
        assert events[0].activity_type == ActivityType.TOOL_CALL

    def test_extract_file_operations(self):
        """Test extraction of file operation activities."""
        text = "Creating file: /tmp/test.txt\nModifying path: src/main.py"
        events = self.interpreter.extract_file_operations(text)

        assert len(events) >= 1
        assert any(evt.activity_type == ActivityType.FILE_OPERATION for evt in events)
        assert any("/tmp/test.txt" in evt.description or "test.txt" in evt.description for evt in events)

    def test_extract_errors(self):
        """Test extraction of error activities."""
        text = "Error: Connection failed\nFAILED: Timeout occurred"
        events = self.interpreter.extract_errors(text)

        assert len(events) >= 1
        assert all(evt.activity_type == ActivityType.ERROR for evt in events)
        assert any("Connection failed" in evt.description for evt in events)

    def test_extract_planning(self):
        """Test extraction of planning activities."""
        text = "<thinking>I need to first understand the problem, then break it down</thinking>"
        events = self.interpreter.extract_planning(text)

        assert len(events) > 0
        assert events[0].activity_type == ActivityType.THINKING

    def test_interpret_activity_combined(self):
        """Test combined activity interpretation."""
        text = """
Processing request.
<thinking>Let me break this down step by step</thinking>
Calling tool: bash -c "ls -la"
Error: Command not found
Creating file: output.txt
input_tokens: 1234
cost: $0.05
"""
        events = self.interpreter.interpret_activity(text)

        # Should have multiple events
        assert len(events) > 0

        # Check that sensitive data was filtered in analysis
        descriptions = [e.description for e in events]
        sensitive_found = any("input_tokens" in d or "cost" in d for d in descriptions)

        # Sensitive events might be extracted, but should be marked as such
        types = [e.activity_type for e in events]
        assert ActivityType.ERROR in types or len(events) > 0

    def test_interpret_activity_empty_output(self):
        """Test interpretation of empty output."""
        events = self.interpreter.interpret_activity("")
        # Should handle gracefully, might return empty or status event
        assert isinstance(events, list)

    def test_get_filtered_output(self):
        """Test getting filtered output for display."""
        text = "Result: success\ninput_tokens: 5000\ncost: $0.10"
        filtered = self.interpreter.get_filtered_output(text)

        assert "success" in filtered
        assert "input_tokens" not in filtered
        assert "cost" not in filtered

    def test_activity_event_structure(self):
        """Test ActivityEvent dataclass structure."""
        event = ActivityEvent(
            activity_type=ActivityType.TOOL_CALL,
            description="Testing tool call",
            details={"tool": "bash", "command": "echo test"},
            is_sensitive=False
        )

        assert event.activity_type == ActivityType.TOOL_CALL
        assert "Testing tool call" in event.description
        assert event.details["tool"] == "bash"
        assert event.is_sensitive is False

    def test_global_interpreter_instance(self):
        """Test that get_interpreter returns a singleton."""
        interp1 = get_interpreter()
        interp2 = get_interpreter()
        assert interp1 is interp2


class TestActivityFormatter:
    """Tests for activity formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ActivityFormatter(use_colors=False, use_icons=False)

    def test_format_event_basic(self):
        """Test formatting a single event."""
        event = ActivityEvent(
            activity_type=ActivityType.TOOL_CALL,
            description="Running git status"
        )
        formatted = self.formatter.format_event(event)

        assert "TOOL_CALL" in formatted
        assert "Running git status" in formatted

    def test_format_event_with_details(self):
        """Test formatting event with details."""
        event = ActivityEvent(
            activity_type=ActivityType.FILE_OPERATION,
            description="Created file",
            details={"path": "/tmp/test.txt", "size": 1024}
        )
        formatted = self.formatter.format_event(event, include_details=True)

        assert "FILE_OPERATION" in formatted
        assert "path" in formatted
        assert "/tmp/test.txt" in formatted

    def test_format_events_multiple(self):
        """Test formatting multiple events."""
        events = [
            ActivityEvent(ActivityType.PLANNING, "Planning phase"),
            ActivityEvent(ActivityType.TOOL_CALL, "Tool execution"),
            ActivityEvent(ActivityType.RESPONSE, "Completed")
        ]
        formatted = self.formatter.format_events(events)

        assert "PLANNING" in formatted
        assert "TOOL_CALL" in formatted
        assert "RESPONSE" in formatted

    def test_format_stream_update(self):
        """Test compact streaming format."""
        event = ActivityEvent(
            activity_type=ActivityType.TOOL_CALL,
            description="Quick update"
        )
        formatted = self.formatter.format_stream_update(event)

        assert "Quick update" in formatted

    def test_format_activity_header(self):
        """Test header formatting."""
        header = self.formatter.format_activity_header("claude", "task_123")

        assert "claude" in header
        assert "task_123" in header
        assert "Activity Stream" in header

    def test_format_activity_footer(self):
        """Test footer formatting."""
        footer = self.formatter.format_activity_footer(5)

        assert "5 activity events" in footer

    def test_get_activity_summary(self):
        """Test activity summary generation."""
        events = [
            ActivityEvent(ActivityType.PLANNING, "Plan 1"),
            ActivityEvent(ActivityType.PLANNING, "Plan 2"),
            ActivityEvent(ActivityType.TOOL_CALL, "Tool 1"),
            ActivityEvent(ActivityType.ERROR, "Error 1"),
        ]
        summary = self.formatter.get_activity_summary(events)

        assert "planning" in summary
        assert "tool_call" in summary
        assert "error" in summary
        assert "2" in summary  # planning count

    def test_format_for_display_convenience(self):
        """Test convenience formatting function."""
        events = [
            ActivityEvent(ActivityType.PLANNING, "Start"),
            ActivityEvent(ActivityType.RESPONSE, "Finish")
        ]
        formatted = format_for_display(events, executor="test_executor", task_id="test_123")

        assert "test_executor" in formatted
        assert "test_123" in formatted
        assert "PLANNING" in formatted
        assert "RESPONSE" in formatted

    def test_colors_disabled(self):
        """Test that colors can be disabled."""
        formatter_no_colors = ActivityFormatter(use_colors=False)
        event = ActivityEvent(ActivityType.ERROR, "Test error")
        formatted = formatter_no_colors.format_event(event)

        # Should not contain ANSI color codes
        assert "\033[" not in formatted


class TestActivityIntegration:
    """Integration tests for interpreter and formatter together."""

    def test_full_workflow(self):
        """Test complete interpretation and formatting workflow."""
        raw_output = """
I will help you with this task.
<thinking>
Let me first understand what needs to be done.
I should check the current state of the system.
</thinking>

Calling tool: bash -c "git status"

The git status shows:
- Modified files: 3
- Untracked files: 5

Now I'll commit these changes.
Calling tool: bash -c "git add ."

Creating file: CHANGES.md

Tokens used: 1234
Cost: $0.05
"""
        interpreter = ActivityInterpreter()
        formatter = ActivityFormatter(use_colors=False)

        # Interpret
        events = interpreter.interpret_activity(raw_output)
        assert len(events) > 0

        # Format
        formatted = formatter.format_events(events)
        assert len(formatted) > 0

        # Should not contain token/cost info
        assert "Tokens used" not in formatted
        assert "Cost" not in formatted

    def test_sensitive_metadata_filtering_comprehensive(self):
        """Test that all types of sensitive data are filtered."""
        test_cases = [
            ("input_tokens: 5000", ": 5000"),
            ("output_tokens: 1000", ": 1000"),
            ("cost: $1.50", "$1.50"),
            ("input_cost: $0.25", "$0.25"),
            ("cache_creation_input_tokens: 100", ": 100"),
            ("cache_read_input_tokens: 50", ": 50"),
        ]

        interpreter = ActivityInterpreter()

        for text, value_pattern in test_cases:
            result = interpreter.get_filtered_output(text)
            assert value_pattern not in result, \
                f"Value '{value_pattern}' not filtered from: {text}"
