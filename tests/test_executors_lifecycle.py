"""
Lifecycle tests for Phase 4 executor implementations.

Tests the context manager contract and resource cleanup for all executors,
ensuring processes are properly terminated on exit.
"""

import pytest
import subprocess
from unittest.mock import Mock, MagicMock, patch, call
from contextlib import contextmanager

from src.oneshot.providers.base import BaseExecutor, RecoveryResult
from src.oneshot.providers.direct_executor import DirectExecutor
from src.oneshot.providers.cline_executor import ClineExecutor
from src.oneshot.providers.claude_executor import ClaudeExecutor
from src.oneshot.providers.gemini_executor import GeminiCLIExecutor
from src.oneshot.providers.aider_executor import AiderExecutor


class TestDirectExecutorLifecycle:
    """Test DirectExecutor context manager and recovery."""

    def test_execute_context_manager_success(self):
        """Test successful execution via context manager."""
        executor = DirectExecutor()

        # Mock the client
        with patch.object(executor.client, 'check_connection', return_value=True):
            with patch.object(executor.client, 'generate') as mock_gen:
                mock_response = Mock()
                mock_response.response = "Test response"
                mock_gen.return_value = mock_response

                with executor.execute("test prompt") as stream:
                    output = stream
                    assert output == "Test response"

    def test_execute_connection_error(self):
        """Test execute raises when connection fails."""
        executor = DirectExecutor()

        with patch.object(executor.client, 'check_connection', return_value=False):
            with pytest.raises(RuntimeError, match="Cannot connect"):
                with executor.execute("test prompt") as stream:
                    pass

    def test_recover_no_persistent_state(self):
        """Test recover returns failure for Direct executor."""
        executor = DirectExecutor()
        result = executor.recover("task123")

        assert isinstance(result, RecoveryResult)
        assert result.success is False
        assert result.recovered_activity == []


class TestClineExecutorLifecycle:
    """Test ClineExecutor context manager and recovery."""

    def test_execute_context_manager_process_creation(self):
        """Test process is created and yielded as generator."""
        executor = ClineExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process running
            mock_process.stdout = Mock()
            mock_process.stdout.readline.side_effect = ["line1\n", "line2\n", ""]
            mock_popen.return_value = mock_process

            with executor.execute("test prompt") as stream_gen:
                # stream_gen is a generator function, we need to call it
                lines = list(stream_gen)
                assert len(lines) >= 2

    def test_execute_process_cleanup_on_exit(self):
        """Test process is terminated on context exit."""
        executor = ClineExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process running
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = ""
            mock_popen.return_value = mock_process

            try:
                with executor.execute("test prompt") as stream_gen:
                    pass
            except StopIteration:
                pass

            # Verify process cleanup was attempted
            mock_process.terminate.assert_called_once()

    def test_execute_force_kill_on_timeout(self):
        """Test process is forcefully killed if terminate times out."""
        executor = ClineExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = ""
            mock_process.wait.side_effect = [
                subprocess.TimeoutExpired("cmd", 5),  # First call (terminate)
                None  # Second call (kill)
            ]
            mock_popen.return_value = mock_process

            try:
                with executor.execute("test prompt") as stream_gen:
                    pass
            except (StopIteration, subprocess.TimeoutExpired):
                pass

            # Verify kill was called after timeout
            mock_process.kill.assert_called_once()

    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    def test_recover_from_task_files(self, mock_open, mock_exists):
        """Test recovery from Cline task state files."""
        executor = ClineExecutor()

        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '''
        [
            {"type": "message", "text": "Starting task"},
            {"say": "completion_result", "text": "Task completed"}
        ]
        '''

        with patch('json.load') as mock_json:
            mock_json.return_value = [
                {"type": "message", "text": "Starting task"},
                {"say": "completion_result", "text": "Task completed"}
            ]

            result = executor.recover("task123")

            assert isinstance(result, RecoveryResult)
            assert result.success is True
            assert len(result.recovered_activity) == 2
            assert result.verdict == "DONE"

    @patch('pathlib.Path.exists')
    def test_recover_no_task_files(self, mock_exists):
        """Test recovery returns failure when task files don't exist."""
        executor = ClineExecutor()
        mock_exists.return_value = False

        result = executor.recover("nonexistent123")

        assert result.success is False
        assert result.recovered_activity == []


class TestClaudeExecutorLifecycle:
    """Test ClaudeExecutor context manager and recovery."""

    def test_execute_context_manager_process_creation(self):
        """Test Claude process is created and yielded as generator."""
        executor = ClaudeExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.side_effect = ["line1\n", ""]
            mock_popen.return_value = mock_process

            with executor.execute("test prompt") as stream_gen:
                lines = list(stream_gen)
                assert len(lines) >= 1

    def test_execute_process_cleanup(self):
        """Test Claude process cleanup."""
        executor = ClaudeExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = ""
            mock_popen.return_value = mock_process

            try:
                with executor.execute("test prompt") as stream_gen:
                    pass
            except StopIteration:
                pass

            mock_process.terminate.assert_called_once()

    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    def test_recover_from_logs(self, mock_open, mock_exists):
        """Test recovery from Claude session logs."""
        executor = ClaudeExecutor()

        # First call returns True for the first location
        mock_exists.side_effect = [True, False, False]
        mock_open.return_value.__enter__.return_value.read.return_value = '[]'

        with patch('json.load') as mock_json:
            mock_json.return_value = [{"type": "activity", "status": "completed"}]

            result = executor.recover("session123")

            assert isinstance(result, RecoveryResult)
            assert result.success is True


class TestGeminiExecutorLifecycle:
    """Test GeminiExecutor context manager and recovery."""

    def test_execute_context_manager(self):
        """Test Gemini process execution."""
        executor = GeminiCLIExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.side_effect = ["Action: task\n", ""]
            mock_popen.return_value = mock_process

            with executor.execute("test prompt") as stream_gen:
                lines = list(stream_gen)
                assert len(lines) >= 1

    def test_execute_cleanup(self):
        """Test Gemini process cleanup."""
        executor = GeminiCLIExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = ""
            mock_popen.return_value = mock_process

            try:
                with executor.execute("test prompt") as stream_gen:
                    pass
            except StopIteration:
                pass

            mock_process.terminate.assert_called_once()

    def test_recover_from_logs(self):
        """Test Gemini recovery."""
        executor = GeminiCLIExecutor()

        with patch('pathlib.Path.exists', return_value=False):
            result = executor.recover("exec123")

            assert isinstance(result, RecoveryResult)
            assert result.success is False


class TestAiderExecutorLifecycle:
    """Test AiderExecutor context manager and recovery."""

    def test_execute_context_manager(self):
        """Test Aider process execution."""
        executor = AiderExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.side_effect = ["Committing changes\n", ""]
            mock_popen.return_value = mock_process

            with executor.execute("test prompt") as stream_gen:
                lines = list(stream_gen)
                assert len(lines) >= 1

    def test_execute_cleanup(self):
        """Test Aider process cleanup."""
        executor = AiderExecutor()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = ""
            mock_popen.return_value = mock_process

            try:
                with executor.execute("test prompt") as stream_gen:
                    pass
            except StopIteration:
                pass

            mock_process.terminate.assert_called_once()

    def test_recover_from_git(self):
        """Test Aider recovery from git history."""
        executor = AiderExecutor()

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "abc1234 First commit\ndefg567 Second commit\n"
            mock_run.return_value = mock_result

            with patch('pathlib.Path.exists', return_value=False):
                result = executor.recover("task123")

                assert isinstance(result, RecoveryResult)
                assert result.success is True
                # Should have exactly 2 git commits
                git_commits = [a for a in result.recovered_activity if a.get('type') == 'git_commit']
                assert len(git_commits) == 2


class TestExecutorCleanupContract:
    """Test the general cleanup contract for all executors."""

    def test_all_executors_have_execute_method(self):
        """Test all executors implement execute() context manager."""
        executors = [
            DirectExecutor(),
            ClineExecutor(),
            ClaudeExecutor(),
            GeminiCLIExecutor(),
            AiderExecutor()
        ]

        for executor in executors:
            assert hasattr(executor, 'execute')
            assert callable(executor.execute)

    def test_all_executors_have_recover_method(self):
        """Test all executors implement recover() method."""
        executors = [
            DirectExecutor(),
            ClineExecutor(),
            ClaudeExecutor(),
            GeminiCLIExecutor(),
            AiderExecutor()
        ]

        for executor in executors:
            assert hasattr(executor, 'recover')
            assert callable(executor.recover)

    def test_recover_returns_recovery_result(self):
        """Test all recover() methods return RecoveryResult."""
        executors = [
            DirectExecutor(),
            ClineExecutor(),
            ClaudeExecutor(),
            GeminiCLIExecutor(),
            AiderExecutor()
        ]

        for executor in executors:
            result = executor.recover("test_id")
            assert isinstance(result, RecoveryResult)
            assert hasattr(result, 'success')
            assert hasattr(result, 'recovered_activity')
            assert hasattr(result, 'verdict')
