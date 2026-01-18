"""
AsyncOrchestrator

Asynchronous task orchestrator for managing concurrent Oneshot task execution
with concurrency limiting and graceful shutdown support.
"""

import asyncio
import signal
import logging
from typing import Dict, List, Optional, Callable, Any
from contextlib import asynccontextmanager

import anyio
from anyio import CapacityLimiter

from .task import OneshotTask, TaskResult
from .state_machine import TaskState
from .events import event_emitter, emit_system_status

logger = logging.getLogger(__name__)


class AsyncOrchestrator:
    """
    Orchestrator for managing asynchronous Oneshot task execution.

    Provides concurrency limiting, graceful shutdown, and task lifecycle management
    using structured concurrency principles.
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        global_idle_threshold: float = 60.0,
        heartbeat_interval: float = 10.0,
        on_task_start: Optional[Callable[[str], None]] = None,
        on_task_complete: Optional[Callable[[str, TaskResult], None]] = None,
        on_task_error: Optional[Callable[[str, Exception], None]] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            max_concurrent: Maximum number of concurrent tasks
            global_idle_threshold: Global idle timeout for all tasks
            heartbeat_interval: How often to check for idle tasks globally
            on_task_start: Callback when a task starts
            on_task_complete: Callback when a task completes successfully
            on_task_error: Callback when a task fails
        """
        self.max_concurrent = max_concurrent
        self.global_idle_threshold = global_idle_threshold
        self.heartbeat_interval = heartbeat_interval
        self.on_task_start = on_task_start
        self.on_task_complete = on_task_complete
        self.on_task_error = on_task_error

        # Concurrency control
        self.capacity_limiter = CapacityLimiter(max_concurrent)

        # Task tracking
        self.tasks: Dict[str, OneshotTask] = {}
        self.task_results: Dict[str, TaskResult] = {}

        # Control events
        self._shutdown_event = anyio.Event()
        self._interrupt_all_event = anyio.Event()

        # Statistics
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_interrupted = 0

    async def run_tasks(
        self,
        commands: List[str],
        idle_threshold: Optional[float] = None,
        activity_check_interval: float = 5.0
    ) -> Dict[str, TaskResult]:
        """
        Execute multiple commands concurrently with orchestration.

        Args:
            commands: List of shell commands to execute
            idle_threshold: Per-task idle threshold override
            activity_check_interval: Activity check interval for tasks

        Returns:
            Dictionary mapping task IDs to TaskResults
        """
        # Create tasks
        for command in commands:
            task = OneshotTask(
                command=command,
                idle_threshold=idle_threshold or self.global_idle_threshold,
                activity_check_interval=activity_check_interval,
                on_state_change=self._handle_task_state_change,
                on_output=self._handle_task_output,
            )
            self.tasks[task.task_id] = task

        # Set up signal handlers for graceful shutdown
        async with self._signal_handler_context():
            try:
                async with anyio.create_task_group() as tg:
                    # Start heartbeat monitor
                    tg.start_soon(self._heartbeat_monitor)

                    # Start all tasks
                    for task in self.tasks.values():
                        tg.start_soon(self._run_single_task, task)

                # Wait for all tasks to complete or shutdown
                await self._shutdown_event.wait()

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, initiating graceful shutdown...")
                await self._shutdown_all_tasks()
            except Exception as e:
                logger.error(f"Orchestrator error: {e}")
                await self._shutdown_all_tasks()

        return self.task_results

    async def _run_single_task(self, task: OneshotTask):
        """
        Run a single task with concurrency limiting.

        Args:
            task: The OneshotTask to execute
        """
        async with self.capacity_limiter:
            if self.on_task_start:
                self.on_task_start(task.task_id)

            try:
                result = await task.run()
                self.task_results[task.task_id] = result

                if result.success:
                    self.tasks_completed += 1
                    if self.on_task_complete:
                        self.on_task_complete(task.task_id, result)
                else:
                    self.tasks_failed += 1
                    if self.on_task_error:
                        self.on_task_error(task.task_id, Exception(result.error))

            except asyncio.CancelledError:
                # Task was cancelled/interrupted
                self.tasks_interrupted += 1
                result = TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error="Task was interrupted"
                )
                self.task_results[task.task_id] = result
                if self.on_task_error:
                    self.on_task_error(task.task_id, asyncio.CancelledError("Task interrupted"))

            except Exception as e:
                self.tasks_failed += 1
                result = TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=str(e)
                )
                self.task_results[task.task_id] = result
                if self.on_task_error:
                    self.on_task_error(task.task_id, e)

    async def _heartbeat_monitor(self):
        """
        Global heartbeat monitor for idle task detection and cleanup.
        """
        try:
            while not self._shutdown_event.is_set():
                await anyio.sleep(self.heartbeat_interval)

                # Check for globally idle tasks
                current_time = asyncio.get_event_loop().time()
                idle_tasks = []

                for task in self.tasks.values():
                    if not task.is_finished and task.state_machine.last_activity:
                        idle_time = current_time - task.state_machine.last_activity
                        if idle_time > self.global_idle_threshold:
                            idle_tasks.append(task)

                # Interrupt idle tasks
                for task in idle_tasks:
                    logger.warning(f"Task {task.task_id} idle for {self.global_idle_threshold}s, interrupting")
                    task.interrupt()

                # Check if all tasks are finished
                if all(task.is_finished for task in self.tasks.values()):
                    self._shutdown_event.set()
                    break

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Heartbeat monitor error: {e}")

    async def _shutdown_all_tasks(self):
        """
        Gracefully shutdown all running tasks.
        """
        logger.info("Shutting down all tasks...")

        # Interrupt all running tasks
        for task in self.tasks.values():
            if task.can_interrupt:
                task.interrupt()

        # Wait a bit for graceful shutdown
        await anyio.sleep(2.0)

        # Force termination of any remaining tasks
        for task in self.tasks.values():
            if not task.is_finished and task.process:
                try:
                    task.process.kill()
                except (ProcessLookupError, OSError):
                    pass

        self._shutdown_event.set()

    def _handle_task_state_change(self, old_state: TaskState, new_state: TaskState):
        """
        Handle task state changes.

        Args:
            old_state: Previous state
            new_state: New state
        """
        logger.debug(f"Task state changed: {old_state} -> {new_state}")

    def _handle_task_output(self, line: str):
        """
        Handle task output lines.

        Args:
            line: Output line from task
        """
        # Could be used for logging or real-time output streaming
        pass

    @asynccontextmanager
    async def _signal_handler_context(self):
        """
        Context manager for setting up signal handlers.
        """
        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._interrupt_all_event.set()

        # Register signal handlers
        original_sigint = signal.signal(signal.SIGINT, signal_handler)
        original_sigterm = signal.signal(signal.SIGTERM, signal_handler)

        try:
            yield
        finally:
            # Restore original signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

    def interrupt_task(self, task_id: str):
        """
        Interrupt a specific task.

        Args:
            task_id: ID of the task to interrupt
        """
        if task_id in self.tasks:
            self.tasks[task_id].interrupt()

    def interrupt_all(self):
        """
        Interrupt all running tasks.
        """
        self._interrupt_all_event.set()
        for task in self.tasks.values():
            if task.can_interrupt:
                task.interrupt()

    @property
    def running_tasks(self) -> List[str]:
        """Get list of currently running task IDs."""
        return [task_id for task_id, task in self.tasks.items()
                if not task.is_finished]

    @property
    def stats(self) -> Dict[str, int]:
        """Get orchestrator statistics."""
        return {
            'total_tasks': len(self.tasks),
            'completed': self.tasks_completed,
            'failed': self.tasks_failed,
            'interrupted': self.tasks_interrupted,
            'running': len(self.running_tasks),
        }