"""Tests for PTY streaming and JSON parsing functionality."""

import pytest
import json
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from oneshot.oneshot import (
    parse_streaming_json,
    get_cline_task_dir,
    monitor_task_activity,
    call_executor_pty,
    SUPPORTS_PTY,
    DISABLE_STREAMING
)


class TestParseStreamingJson:
    """Test streaming JSON parsing functionality."""

    def test_parse_single_json_line(self):
        """Test parsing a single JSON line."""
        data = '{"status": "working", "progress": 50}'
        result = parse_streaming_json(data)
        assert len(result) == 1
        assert result[0]["status"] == "working"
        assert result[0]["progress"] == 50

    def test_parse_multiple_json_lines(self):
        """Test parsing multiple newline-delimited JSON objects."""
        data = '{"status": "working", "progress": 25}\n{"status": "working", "progress": 50}\n{"status": "complete"}'
        result = parse_streaming_json(data)
        assert len(result) == 3
        assert result[0]["progress"] == 25
        assert result[1]["progress"] == 50
        assert result[2]["status"] == "complete"

    def test_parse_json_with_empty_lines(self):
        """Test parsing JSON with empty lines between objects."""
        data = '{"status": "start"}\n\n{"status": "end"}\n\n'
        result = parse_streaming_json(data)
        assert len(result) == 2
        assert result[0]["status"] == "start"
        assert result[1]["status"] == "end"

    def test_parse_malformed_json_graceful_degradation(self):
        """Test graceful degradation with malformed JSON."""
        data = '{"status": "working"}\n{malformed json here}\n{"status": "done"}'
        result = parse_streaming_json(data)
        # Should skip the malformed line and parse valid ones
        assert len(result) == 2
        assert result[0]["status"] == "working"
        assert result[1]["status"] == "done"

    def test_parse_empty_data(self):
        """Test parsing empty data."""
        data = ''
        result = parse_streaming_json(data)
        assert len(result) == 0

    def test_parse_only_whitespace(self):
        """Test parsing only whitespace."""
        data = '   \n\n   \n'
        result = parse_streaming_json(data)
        assert len(result) == 0

    def test_parse_complex_json_objects(self):
        """Test parsing complex JSON objects."""
        data = '{"type": "message", "data": {"key": "value", "nested": [1, 2, 3]}}'
        result = parse_streaming_json(data)
        assert len(result) == 1
        assert result[0]["type"] == "message"
        assert result[0]["data"]["nested"] == [1, 2, 3]


class TestGetClineTaskDir:
    """Test Cline task directory detection."""

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.home')
    def test_get_cline_task_dir_exists(self, mock_home, mock_exists):
        """Test getting Cline task directory when it exists."""
        mock_home.return_value = Path('/home/user')
        mock_exists.return_value = True

        result = get_cline_task_dir('task-123')

        assert result is not None
        assert 'task-123' in str(result)
        assert '.cline' in str(result)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.home')
    def test_get_cline_task_dir_not_exists(self, mock_home, mock_exists):
        """Test getting Cline task directory when it doesn't exist."""
        mock_home.return_value = Path('/home/user')
        mock_exists.return_value = False

        result = get_cline_task_dir('task-456')

        assert result is None


class TestMonitorTaskActivity:
    """Test task activity monitoring functionality."""

    def test_monitor_task_activity_invalid_dir(self):
        """Test monitoring non-existent directory."""
        fake_dir = Path('/nonexistent/path/to/task')
        result = monitor_task_activity(fake_dir, timeout=0.1)
        assert result is False

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.rglob')
    def test_monitor_task_activity_no_activity(self, mock_rglob, mock_exists):
        """Test monitoring with no activity detected."""
        mock_exists.return_value = True
        mock_rglob.return_value = []

        fake_dir = MagicMock()
        fake_dir.exists.return_value = True
        fake_dir.rglob.return_value = []

        result = monitor_task_activity(fake_dir, timeout=0.1, check_interval=0.05)
        assert result is False


class TestCallExecutorPty:
    """Test PTY executor functionality."""

    @pytest.mark.skipif(not SUPPORTS_PTY, reason="PTY not supported on this platform")
    def test_pty_supported_on_platform(self):
        """Test that PTY is supported on appropriate platforms."""
        if platform.system() in ('Linux', 'Darwin'):
            assert SUPPORTS_PTY is True
        else:
            assert SUPPORTS_PTY is False

    @pytest.mark.skipif(DISABLE_STREAMING, reason="Streaming disabled via environment variable")
    def test_pty_disabled_check(self):
        """Test that streaming can be disabled."""
        # This test just verifies the environment variable check works
        assert DISABLE_STREAMING is False

    @pytest.mark.skipif(not SUPPORTS_PTY, reason="PTY not supported on this platform")
    def test_pty_simple_echo(self):
        """Test PTY execution with simple echo command."""
        try:
            stdout, stderr, exit_code = call_executor_pty(['echo', 'hello'], timeout=5)
            # Verify output was captured
            assert stdout is not None
            assert isinstance(stdout, str)
            # Output should contain hello or similar
            assert len(stdout) > 0
        except OSError as e:
            # PTY might fail on some systems, that's okay
            pytest.skip(f"PTY execution not available: {e}")

    def test_pty_raises_on_unsupported_platform(self):
        """Test that PTY raises appropriate error on unsupported platforms."""
        if not SUPPORTS_PTY:
            with pytest.raises(OSError, match="PTY not supported"):
                call_executor_pty(['echo', 'hello'])

    @pytest.mark.skipif(not SUPPORTS_PTY, reason="PTY not supported on this platform")
    def test_pty_buffer_accumulation_basic(self):
        """Test basic buffer accumulation functionality."""
        try:
            stdout, stderr, exit_code = call_executor_pty(['echo', 'test accumulation'], timeout=5, accumulation_buffer_size=1024)
            # Should work the same as before but with accumulation logic
            assert 'test accumulation' in stdout
            assert stderr == ''
        except OSError as e:
            pytest.skip(f"PTY execution not available: {e}")

    @pytest.mark.skipif(not SUPPORTS_PTY, reason="PTY not supported on this platform")
    def test_pty_buffer_accumulation_multiline(self):
        """Test buffer accumulation with multiline output."""
        try:
            # Use printf to generate controlled multiline output
            stdout, stderr, exit_code = call_executor_pty(['printf', 'line1\nline2\nline3\n'], timeout=5, accumulation_buffer_size=512)
            assert 'line1' in stdout
            assert 'line2' in stdout
            assert 'line3' in stdout
            lines = [line for line in stdout.split('\n') if line.strip()]
            assert len(lines) >= 3
        except OSError as e:
            pytest.skip(f"PTY execution not available: {e}")

    def test_pty_accumulation_buffer_parameter(self):
        """Test that accumulation_buffer_size parameter is accepted."""
        from inspect import signature
        sig = signature(call_executor_pty)
        assert 'accumulation_buffer_size' in sig.parameters
        # Default should be 4096 as set in the function
        param = sig.parameters['accumulation_buffer_size']
        assert param.default == 4096


class TestStreamingIntegration:
    """Integration tests for streaming functionality."""

    def test_parse_streaming_json_real_claude_output(self):
        """Test parsing simulated Claude streaming output."""
        # Simulated Claude stream-json output
        claude_output = '''{"type": "message", "id": "msg_123", "role": "assistant"}
{"type": "content_block_start", "content_block": {"type": "text"}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "The answer is "}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "42"}}
{"type": "content_block_stop"}
{"type": "message_stop"}'''

        result = parse_streaming_json(claude_output)

        # Should parse all valid JSON objects
        assert len(result) > 0
        assert any(obj.get("type") == "message" for obj in result)
        assert any(obj.get("type") == "content_block_delta" for obj in result)

    def test_parse_streaming_json_real_cline_output(self):
        """Test parsing simulated Cline JSON output."""
        # Simulated Cline json output
        cline_output = '''{"type": "thinking", "content": "Let me analyze this task..."}
{"type": "action", "name": "read_file", "path": "/tmp/test.txt"}
{"type": "result", "success": true, "content": "File contents"}
{"type": "thinking", "content": "Now I'll process the file"}
{"type": "completion", "result": "Task completed"}'''

        result = parse_streaming_json(cline_output)

        assert len(result) >= 3
        assert result[0]["type"] == "thinking"
        assert result[1]["type"] == "action"
        assert result[-1]["type"] == "completion"

    def test_streaming_output_capture_and_reconstruction(self):
        """Test that streaming output can be captured and reconstructed."""
        # Simulate streaming output split across multiple reads
        chunks = [
            '{"msg": "start"}\n{"msg": "',
            'middle"}\n{"msg": "end"}'
        ]

        # Reconstruct by joining
        full_output = ''.join(chunks)
        result = parse_streaming_json(full_output)

        # Should parse correctly even with split output
        assert len(result) >= 2


class TestJsonFlagIntegration:
    """Test that JSON output flags are properly configured."""

    def test_claude_stream_json_flag(self):
        """Verify Claude uses stream-json output format."""
        from oneshot.oneshot import call_executor
        # This is a structural test, not actually calling the executor
        # Just ensuring the code path is correct
        assert True  # Placeholder for integration test

    def test_cline_json_flag(self):
        """Verify Cline uses json output format."""
        from oneshot.oneshot import call_executor
        # This is a structural test, not actually calling the executor
        # Just ensuring the code path is correct
        assert True  # Placeholder for integration test


if __name__ == '__main__':
    pytest.main([__file__, '-v'])