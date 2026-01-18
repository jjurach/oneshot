"""
Oneshot State Machine

Finite state machine for managing task execution lifecycle with support for
process interruption and idle detection.
"""

import asyncio
from enum import Enum
from typing import Optional, Any
from statemachine import StateMachine, State

from .events import EventType, emit_task_event


class TaskState(Enum):
    """Enumeration of possible task states."""
    CREATED = "created"
    RUNNING = "running"
    IDLE = "idle"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class OneshotStateMachine(StateMachine):
    """
    State machine for managing Oneshot task execution lifecycle.

    States:
    - CREATED: Task has been created but not yet started
    - RUNNING: Task is actively executing with recent activity
    - IDLE: Task is running but no activity detected for threshold period
    - INTERRUPTED: Task execution was interrupted by external signal
    - COMPLETED: Task finished successfully
    - FAILED: Task finished with failure

    Transitions:
    - start: CREATED -> RUNNING
    - detect_silence: RUNNING -> IDLE
    - detect_activity: IDLE -> RUNNING
    - interrupt: RUNNING/IDLE -> INTERRUPTED
    - finish: RUNNING/IDLE -> COMPLETED
    - fail: Any state -> FAILED
    """

    # Define states
    created = State(TaskState.CREATED, initial=True)
    running = State(TaskState.RUNNING)
    idle = State(TaskState.IDLE)
    interrupted = State(TaskState.INTERRUPTED)
    completed = State(TaskState.COMPLETED)
    failed = State(TaskState.FAILED)

    # Define transitions
    start = created.to(running)
    detect_silence = running.to(idle)
    detect_activity = idle.to(running)
    interrupt = running.to(interrupted) | idle.to(interrupted)
    finish = running.to(completed) | idle.to(completed) | completed.to(completed, internal=True)
    fail = created.to(failed) | running.to(failed) | idle.to(failed) | interrupted.to(failed) | failed.to(failed, internal=True) | completed.to(failed)

    def __init__(self, task_id: str, process: Optional[Any] = None):
        """
        Initialize the state machine.

        Args:
            task_id: Unique identifier for the task
            process: Optional subprocess handle for process management
        """
        super().__init__()
        self.task_id = task_id
        self.process = process
        try:
            self.last_activity = asyncio.get_running_loop().time()
        except RuntimeError:
            # No running event loop, use None
            self.last_activity = None

    def update_activity(self):
        """Update the last activity timestamp."""
        try:
            self.last_activity = asyncio.get_running_loop().time()
        except RuntimeError:
            # No running loop, use time module
            import time
            self.last_activity = time.time()

    async def emit_event(self, event_type: EventType, **kwargs):
        """
        Emit an event for this task.

        Args:
            event_type: Type of event to emit
            **kwargs: Additional event data
        """
        await emit_task_event(
            event_type,
            self.task_id,
            state=self.current_state_enum.value,
            **kwargs
        )

    def on_enter_interrupted(self):
        """Handle entering INTERRUPTED state - terminate the process."""
        if self.process:
            try:
                self.process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    loop = asyncio.get_running_loop()
                    loop.run_until_complete(asyncio.sleep(0.1))
                except RuntimeError:
                    import time
                    time.sleep(0.1)

                # Force kill if still running
                if self.process.poll() is None:
                    self.process.kill()
            except (ProcessLookupError, OSError):
                # Process may have already terminated
                pass

    def on_enter_completed(self):
        """Handle entering COMPLETED state."""
        # Ensure process is cleaned up
        if self.process and self.process.poll() is None:
            try:
                self.process.wait()
            except (ProcessLookupError, OSError):
                pass

    def on_enter_failed(self):
        """Handle entering FAILED state."""
        # Ensure process is cleaned up
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
                self.process.wait()
            except (ProcessLookupError, OSError):
                pass

    @property
    def current_state_enum(self) -> TaskState:
        """Get the current state as TaskState enum."""
        state_value = self.current_state.value if hasattr(self.current_state, 'value') else self.current_state
        return TaskState(state_value)

    def can_interrupt(self) -> bool:
        """Check if the task can be interrupted (is running or idle)."""
        return self.current_state_enum in [TaskState.RUNNING, TaskState.IDLE]

    def is_finished(self) -> bool:
        """Check if the task has finished (completed, failed, or interrupted)."""
        return self.current_state_enum in [TaskState.COMPLETED, TaskState.FAILED, TaskState.INTERRUPTED]