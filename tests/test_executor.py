"""Tests for executor functionality (sync and async)."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from oneshot.oneshot import call_executor


class TestCallExecutor:
    """Test executor calls (mocked to avoid external dependencies)."""

    @patch('oneshot.oneshot._check_test_mode_blocking')
    @patch('oneshot.oneshot.subprocess.run')
    def test_call_claude_executor(self, mock_run, mock_check):
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

    @patch('oneshot.oneshot._check_test_mode_blocking')
    @patch('oneshot.oneshot.subprocess.run')
    def test_call_cline_executor(self, mock_run, mock_check):
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

    @patch('oneshot.oneshot._check_test_mode_blocking')
    @patch('oneshot.oneshot.subprocess.run')
    def test_call_executor_timeout(self, mock_run, mock_check):
        """Test executor timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("cmd", 300)

        result = call_executor("test prompt", "model", "claude")
        assert "timed out" in result

    @patch('oneshot.oneshot._check_test_mode_blocking')
    @patch('oneshot.oneshot.subprocess.run')
    def test_call_executor_exception(self, mock_run, mock_check):
        """Test executor exception handling."""
        mock_run.side_effect = Exception("Test error")

        result = call_executor("test prompt", "model", "claude")
        assert "ERROR: Test error" == result

    @patch('oneshot.oneshot._check_test_mode_blocking')
    @patch('oneshot.oneshot.subprocess.run')
    def test_call_executor_adaptive_timeout(self, mock_run, mock_check):
        """Test adaptive timeout with activity monitoring."""
        from subprocess import TimeoutExpired

        # First call times out after initial timeout
        # Second call (adaptive) succeeds
        mock_run.side_effect = [
            TimeoutExpired("cmd", 300),  # Initial timeout
            type('MockResult', (), {     # Adaptive success
                'stdout': 'Adaptive output',
                'stderr': '',
                'returncode': 0
            })()
        ]

        result = call_executor("test prompt", "model", "claude", initial_timeout=300, max_timeout=3600)
        assert result == "Adaptive output"

        assert mock_run.call_count == 2


class TestAsyncExecutor:
    """Test async executor functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_call_executor_async_cline(self):
        """Test async executor with cline."""
        from oneshot.oneshot import call_executor_async

        with patch('oneshot.task.OneshotTask') as mock_task_class:
            mock_task = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.output = "mock output"
            mock_task.run.return_value = mock_result
            mock_task_class.return_value = mock_task

            result = await call_executor_async("test prompt", None, "cline")

            assert result == "mock output"

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_call_executor_async_claude_fallback(self):
        """Test async executor falls back to sync for claude."""
        from oneshot.oneshot import call_executor_async

        with patch('oneshot.oneshot.call_executor') as mock_sync_call:
            mock_sync_call.return_value = "sync result"

            result = await call_executor_async("test prompt", "model", "claude")

            assert result == "sync result"
            mock_sync_call.assert_called_once()
