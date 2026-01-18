"""Tests for AsyncOrchestrator functionality."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from oneshot.orchestrator import AsyncOrchestrator
from oneshot.task import OneshotTask, TaskResult
from oneshot.state_machine import OneshotStateMachine, TaskState


class TestAsyncOrchestrator:
    """Test AsyncOrchestrator functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_orchestrator_single_task(self):
        """Test orchestrator with single task."""
        orchestrator = AsyncOrchestrator(max_concurrent=1, heartbeat_interval=0.1)

        # Mock successful task execution
        with patch('oneshot.orchestrator.OneshotTask') as mock_task_class:
            # Create a properly async mock
            async def mock_run():
                await asyncio.sleep(0.01)  # Simulate some work
                return TaskResult(
                    task_id="test-task-1",
                    success=True,
                    output="success",
                    exit_code=0
                )

            mock_task = AsyncMock()
            mock_task.task_id = "test-task-1"
            mock_task.run = mock_run
            mock_task.state = TaskState.COMPLETED
            mock_task.is_finished = True
            mock_task.can_interrupt = False
            mock_task_class.return_value = mock_task

            results = await orchestrator.run_tasks(["echo 'test'"])

            assert len(results) == 1
            assert results["test-task-1"].success is True

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_orchestrator_multiple_tasks(self):
        """Test orchestrator with multiple concurrent tasks."""
        orchestrator = AsyncOrchestrator(max_concurrent=2, heartbeat_interval=0.1)

        # Mock task executions
        with patch('oneshot.orchestrator.OneshotTask') as mock_task_class:
            task_counter = [0]  # Use list to avoid closure issues

            def create_mock_task(command, **kwargs):
                task_counter[0] += 1
                task_id = f"task-{task_counter[0]}"

                async def mock_run():
                    await asyncio.sleep(0.01)  # Simulate work
                    return TaskResult(
                        task_id=task_id,
                        success=True,
                        output=f"output for {command}",
                        exit_code=0
                    )

                mock_task = AsyncMock()
                mock_task.task_id = task_id
                mock_task.run = mock_run
                mock_task.state = TaskState.COMPLETED
                mock_task.is_finished = True
                mock_task.can_interrupt = False
                return mock_task

            mock_task_class.side_effect = create_mock_task

            results = await orchestrator.run_tasks(["cmd1", "cmd2", "cmd3"])

            assert len(results) == 3
            assert all(result.success for result in results.values())

    def test_orchestrator_stats(self):
        """Test orchestrator statistics."""
        orchestrator = AsyncOrchestrator()
        # Simulate tasks by creating mock task objects
        from oneshot.state_machine import OneshotStateMachine, TaskState

        task1 = OneshotTask("cmd1")
        task1.state_machine = OneshotStateMachine("task-1")
        task2 = OneshotTask("cmd2")
        task2.state_machine = OneshotStateMachine("task-2")
        task3 = OneshotTask("cmd3")
        task3.state_machine = OneshotStateMachine("task-3")

        orchestrator.tasks["task-1"] = task1
        orchestrator.tasks["task-2"] = task2
        orchestrator.tasks["task-3"] = task3
        orchestrator.tasks_completed = 2
        orchestrator.tasks_failed = 1

        stats = orchestrator.stats
        assert stats['completed'] == 2
        assert stats['failed'] == 1
        assert stats['total_tasks'] == 3
