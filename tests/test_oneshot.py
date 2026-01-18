"""Tests for oneshot core functionality."""

import json
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
import tempfile
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oneshot.oneshot import (
    extract_json,
    parse_json_verdict,
    call_executor,
    find_latest_session,
    read_session_context,
    strip_ansi,
    run_oneshot,
    count_iterations
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


class TestCallExecutor:
    """Test executor calls (mocked to avoid external dependencies)."""

    @patch('subprocess.run')
    def test_call_claude_executor(self, mock_run):
        """Test calling claude executor."""
        mock_run.return_value = type('MockResult', (), {
            'stdout': 'Mock output',
            'stderr': '',
            'returncode': 0
        })()

        result = call_executor("test prompt", "claude-3-5-haiku", "claude")
        assert result == "Mock output"

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs['input'] == "test prompt"
        assert 'claude' in ' '.join(args[0])

    @patch('subprocess.run')
    def test_call_cline_executor(self, mock_run):
        """Test calling cline executor."""
        mock_run.return_value = type('MockResult', (), {
            'stdout': 'Mock output',
            'stderr': '',
            'returncode': 0
        })()

        result = call_executor("test prompt", None, "cline")
        assert result == "Mock output"

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert 'cline' in ' '.join(args[0])
        assert '--oneshot' in args[0]

    @patch('subprocess.run')
    def test_call_executor_timeout(self, mock_run):
        """Test executor timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("cmd", 120)

        result = call_executor("test prompt", "model", "claude")
        assert "timed out" in result

    @patch('subprocess.run')
    def test_call_executor_exception(self, mock_run):
        """Test executor exception handling."""
        mock_run.side_effect = Exception("Test error")

        result = call_executor("test prompt", "model", "claude")
        assert "ERROR: Test error" == result


class TestSessionManagement:
    """Test session file management."""

    def test_find_latest_session(self):
        """Test finding the latest session file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some session files
            file1 = temp_path / "session_20230101_120000.md"
            file2 = temp_path / "session_20230101_130000.md"
            file3 = temp_path / "session_20230102_120000.md"

            file1.touch()
            import time
            time.sleep(0.01)  # Ensure different mtimes
            file2.touch()
            time.sleep(0.01)
            file3.touch()  # This will have the latest mtime

            latest = find_latest_session(temp_path)
            assert latest.name == "session_20230102_120000.md"

    def test_find_latest_session_no_files(self):
        """Test finding latest session when no files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            latest = find_latest_session(temp_path)
            assert latest is None

    @patch('builtins.open', new_callable=mock_open, read_data="Session content")
    def test_read_session_context(self, mock_file):
        """Test reading session context."""
        result = read_session_context(Path("dummy.md"))
        assert result == "Session content"

    @patch('builtins.open')
    def test_read_session_context_error(self, mock_file):
        """Test reading session context with error."""
        mock_file.side_effect = Exception("Read error")
        result = read_session_context(Path("dummy.md"))
        assert result is None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_strip_ansi(self):
        """Test ANSI escape code removal."""
        text_with_ansi = "\x1b[31mRed text\x1b[0m normal text"
        result = strip_ansi(text_with_ansi)
        assert result == "Red text normal text"

    def test_count_iterations(self):
        """Test counting iterations in session file."""
        content = """# Session
## Iteration 1
Some content
## Iteration 2
More content
## Iteration 3
Final content"""

        with patch('builtins.open', mock_open(read_data=content)):
            result = count_iterations(Path("dummy.md"))
            assert result == 3

    def test_count_iterations_empty_file(self):
        """Test counting iterations in empty file."""
        with patch('builtins.open', mock_open(read_data="")):
            result = count_iterations(Path("dummy.md"))
            assert result == 0


class TestRunOneshot:
    """Test the main run_oneshot function (with mocking)."""

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.time.sleep')
    @patch('builtins.open', new_callable=mock_open)
    @patch('oneshot.oneshot.datetime')
    def test_run_oneshot_success_on_first_iteration(self, mock_datetime, mock_file, mock_sleep, mock_call):
        """Test successful completion on first iteration."""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20230101_120000"

        # Mock worker returning DONE
        worker_response = '''Some output
{
  "status": "DONE",
  "result": "Task completed",
  "confidence": "high",
  "validation": "Verified",
  "execution_proof": "Executed successfully"
}
'''
        auditor_response = '''Some auditor output
{
  "verdict": "DONE",
  "reason": "Perfect"
}
'''

        mock_call.side_effect = [worker_response, auditor_response]

        success = run_oneshot(
            prompt="Test task",
            worker_model="test-worker",
            auditor_model="test-auditor",
            max_iterations=3
        )

        assert success is True
        assert mock_call.call_count == 2  # worker + auditor

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.time.sleep')
    @patch('builtins.open', new_callable=mock_open)
    @patch('oneshot.oneshot.datetime')
    def test_run_oneshot_max_iterations_reached(self, mock_datetime, mock_file, mock_sleep, mock_call):
        """Test when max iterations are reached without success."""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20230101_120000"

        # Mock responses with proper JSON formatting
        worker_response = '''Output
{
  "status": "DONE"
}'''

        auditor_response = '''Audit output
{
  "verdict": "REITERATE",
  "reason": "Try again"
}'''

        # Provide responses for 3 iterations: 3 workers + 3 auditors
        mock_call.side_effect = [
            worker_response, auditor_response,  # iteration 1
            worker_response, auditor_response,  # iteration 2
            worker_response, auditor_response,  # iteration 3
        ]

        success = run_oneshot(
            prompt="Test task",
            worker_model="test-worker",
            auditor_model="test-auditor",
            max_iterations=3
        )

        assert success is False
        assert mock_call.call_count == 6  # 3 workers + 3 auditors


from oneshot.oneshot import main as oneshot_main

class TestMain:
    @patch('sys.argv', ['oneshot', 'test prompt', '--executor', 'cline', '--worker-model', 'some-model'])
    def test_main_cline_with_model_aborts(self):
        """Test that main aborts when cline executor is used with a model."""
        with pytest.raises(SystemExit) as excinfo:
            oneshot_main()
        assert excinfo.value.code == 1

    @patch('sys.argv', ['oneshot', 'test prompt', '--executor', 'cline'])
    @patch('oneshot.oneshot.call_executor')
    def test_main_cline_without_model_succeeds(self, mock_call_executor):
        """Test that main succeeds when cline executor is used without a model."""
        # Mock the return value of call_executor to simulate a successful run
        mock_call_executor.side_effect = [
            '{"status": "DONE", "result": "Success"}',
            '{"verdict": "DONE", "reason": "Perfect"}'
        ] * 5
        with patch('sys.exit') as mock_exit:
            oneshot_main()
            mock_exit.assert_called_once_with(0)

    @patch('sys.argv', ['oneshot', 'test prompt', '--executor', 'claude', '--worker-model', 'some-model'])
    @patch('oneshot.oneshot.call_executor')
    def test_main_claude_with_model_succeeds(self, mock_call_executor):
        """Test that main succeeds when claude executor is used with a model."""
        # Mock the return value of call_executor to simulate a successful run
        mock_call_executor.side_effect = [
            '{"status": "DONE", "result": "Success"}',
            '{"verdict": "DONE", "reason": "Perfect"}'
        ] * 5
        with patch('sys.exit') as mock_exit:
            oneshot_main()
            mock_exit.assert_called_once_with(0)