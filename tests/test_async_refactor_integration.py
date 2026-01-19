"""Integration tests for async refactor implementation."""

import asyncio
import pytest
import time
from unittest.mock import patch, AsyncMock
from oneshot.orchestrator import AsyncOrchestrator
from oneshot.task import TaskResult


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_concurrency_limit_capacity_limiter():
    """Test concurrency limit with CapacityLimiter(2) as specified in prompt."""
    orchestrator = AsyncOrchestrator(max_concurrent=2, heartbeat_interval=0.1)

    # Track concurrent executions
    max_concurrent_seen = 0
    current_concurrent = 0
    concurrent_counts = []

    with patch('oneshot.orchestrator.OneshotTask') as mock_task_class:
        task_counter = [0]

        def create_mock_task(command, **kwargs):
            task_counter[0] += 1
            task_id = f"task-{task_counter[0]}"

            async def mock_run():
                nonlocal current_concurrent, max_concurrent_seen
                current_concurrent += 1
                max_concurrent_seen = max(max_concurrent_seen, current_concurrent)
                concurrent_counts.append(current_concurrent)

                # Simulate work that takes some time
                await asyncio.sleep(0.05)

                current_concurrent -= 1
                concurrent_counts.append(current_concurrent)

                return TaskResult(
                    task_id=task_id,
                    success=True,
                    output=f"output for {command}",
                    exit_code=0
                )

            mock_task = AsyncMock()
            mock_task.task_id = task_id
            mock_task.run = mock_run
            mock_task.state = type('MockState', (), {'value': 'completed'})()
            mock_task.is_finished = True
            mock_task.can_interrupt = False
            return mock_task

        mock_task_class.side_effect = create_mock_task

        # Launch 5 tasks as specified in the prompt
        results = await orchestrator.run_tasks([f"cmd{i}" for i in range(1, 6)])

        assert len(results) == 5
        assert all(result.success for result in results.values())

        # Verify concurrency was limited to 2 as specified
        assert max_concurrent_seen <= 2, f"Max concurrent tasks was {max_concurrent_seen}, expected <= 2"

        # Verify we actually had concurrent execution
        assert max_concurrent_seen == 2, f"Expected exactly 2 concurrent tasks, got {max_concurrent_seen}"


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_orchestrator_heartbeat_monitor_exists():
    """Verify that AsyncOrchestrator has heartbeat monitoring capability."""
    orchestrator = AsyncOrchestrator(
        max_concurrent=2,
        global_idle_threshold=10.0,
        heartbeat_interval=1.0
    )

    # Verify the orchestrator has the expected attributes for idle monitoring
    assert hasattr(orchestrator, 'global_idle_threshold')
    assert hasattr(orchestrator, '_heartbeat_monitor')
    assert orchestrator.global_idle_threshold == 10.0
    assert orchestrator.heartbeat_interval == 1.0

    # Verify heartbeat monitor is a coroutine method
    import inspect
    assert inspect.iscoroutinefunction(orchestrator._heartbeat_monitor)


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_state_machine_transition_integrity():
    """Test state machine transition integrity as specified in prompt."""
    from oneshot.state_machine import OneshotStateMachine, TaskState
    from unittest.mock import MagicMock

    # Create state machine with mock process
    mock_process = MagicMock()
    sm = OneshotStateMachine("test-task", mock_process)

    # Test the exact scenario from the prompt: Start a task and then call interrupt
    sm.start()
    assert sm.current_state.id == TaskState.RUNNING.value

    # Call interrupt (this should transition to INTERRUPTED and terminate process)
    sm.interrupt()
    assert sm.current_state.id == TaskState.INTERRUPTED.value

    # Verify process.terminate() was called exactly once
    mock_process.terminate.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_silence_detection_with_timestamp_mock():
    """Test silence detection by mocking last_activity timestamp."""
    from oneshot.state_machine import OneshotStateMachine, TaskState
    import time

    sm = OneshotStateMachine("test-task")

    # Start the task
    sm.start()
    assert sm.current_state.id == TaskState.RUNNING.value

    # Mock the last_activity to be 15+ seconds in the past (as mentioned in prompt)
    sm.last_activity = time.time() - 16

    # This simulates the health monitor detecting silence
    sm.detect_silence()
    assert sm.current_state.id == TaskState.IDLE.value


@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_full_async_oneshot_workflow():
    """Test full async oneshot workflow with mocked providers."""
    from oneshot.oneshot import run_oneshot_async
    from oneshot.providers import ProviderConfig, create_provider
    from unittest.mock import AsyncMock

    # Create mock providers
    worker_config = ProviderConfig(
        provider_type='executor',
        executor='claude',
        model='test-model'
    )
    auditor_config = ProviderConfig(
        provider_type='executor',
        executor='claude',
        model='test-model'
    )

    # Mock the provider creation and behavior
    with patch('oneshot.providers.create_provider') as mock_create:
        mock_worker = AsyncMock()
        mock_auditor = AsyncMock()

        # Worker returns valid JSON response
        mock_worker.generate_async.return_value = '{"status": "DONE", "result": "Test completed successfully", "confidence": "high"}'
        mock_worker.config = worker_config

        # Auditor confirms completion
        mock_auditor.generate_async.return_value = '{"verdict": "DONE", "reason": "Task completed successfully"}'
        mock_auditor.config = auditor_config

        mock_create.side_effect = [mock_worker, mock_auditor]

        # Run async oneshot
        success = await run_oneshot_async(
            prompt="Test prompt for async refactor",
            worker_provider=mock_worker,
            auditor_provider=mock_auditor,
            max_iterations=1
        )

        assert success is True
        mock_worker.generate_async.assert_called_once()
        mock_auditor.generate_async.assert_called_once()