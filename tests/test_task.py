"""Tests for OneshotTask async functionality."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from oneshot.task import OneshotTask, TaskResult
from oneshot.state_machine import TaskState


class TestOneshotTask:
    """Test OneshotTask async functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_task_successful_execution(self):
        """Test successful task execution."""
        # Mock subprocess
        with patch('asyncio.create_subprocess_shell') as mock_proc:
            mock_process = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_process.wait.return_value = 0
            mock_proc.return_value = mock_process

            # Mock stream reading
            async def mock_readline():
                return b'output line\n'

            mock_process.stdout.readline.side_effect = [
                b'output line\n',
                b''
            ]
            mock_process.stderr.readline.return_value = b''

            task = OneshotTask("echo test", idle_threshold=30)
            result = await task.run()

            assert result.success is True
            assert result.exit_code == 0
            assert 'output line' in result.output

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_task_failed_execution(self):
        """Test failed task execution."""
        with patch('asyncio.create_subprocess_shell') as mock_proc:
            mock_process = AsyncMock()
            mock_process.wait = AsyncMock(return_value=1)
            mock_process.poll = AsyncMock(return_value=1)
            mock_proc.return_value = mock_process

            # Track readline calls
            stderr_calls = [b'error message\n', b'', b'']
            stdout_calls = [b'', b'']

            async def stderr_readline():
                if stderr_calls:
                    return stderr_calls.pop(0)
                return b''

            async def stdout_readline():
                if stdout_calls:
                    return stdout_calls.pop(0)
                return b''

            mock_process.stderr = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=stderr_readline)
            mock_process.stdout.readline = AsyncMock(side_effect=stdout_readline)

            task = OneshotTask("failing command", idle_threshold=1, activity_check_interval=0.1)
            result = await task.run()

            assert result.success is False
            assert result.exit_code == 1
            assert 'error message' in result.error

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_task_idle_detection(self):
        """Test idle detection and state transitions."""
        # This test verifies the state machine can transition to idle
        # We'll test the state machine directly rather than mocking complex async streams
        task = OneshotTask("test command", idle_threshold=0.2, activity_check_interval=0.1)

        # Start the state machine
        task.state_machine.start()
        assert task.state == TaskState.RUNNING

        # Simulate no activity for longer than idle threshold
        await asyncio.sleep(0.3)

        # Manually trigger idle detection (simulating what the monitor would do)
        if task.can_interrupt:
            task.state_machine.detect_silence()
            assert task.state == TaskState.IDLE

        # Verify we can detect activity again
        task.state_machine.detect_activity()
        assert task.state == TaskState.RUNNING

    def test_task_interruption(self):
        """Test task interruption."""
        task = OneshotTask("long running command")
        task.state_machine.start()

        assert task.can_interrupt is True

        task.interrupt()
        assert task.state == TaskState.INTERRUPTED
        assert task.can_interrupt is False
