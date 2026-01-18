"""
OneshotTask

Asynchronous task execution with state management and stream monitoring.
"""

import asyncio
import uuid
from typing import Optional, Callable, Any, List
from dataclasses import dataclass, field

from .state_machine import OneshotStateMachine, TaskState
from .events import EventType


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    execution_time: float = 0.0


class OneshotTask:
    """
    Asynchronous task execution with state management and monitoring.

    Handles subprocess execution, stream monitoring, and health checks
    with integration to the state machine for lifecycle management.
    """

    def __init__(
        self,
        command: str,
        task_id: Optional[str] = None,
        idle_threshold: float = 30.0,
        activity_check_interval: float = 5.0,
        on_state_change: Optional[Callable[[TaskState, TaskState], None]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the task.

        Args:
            command: Shell command to execute
            task_id: Optional unique task identifier
            idle_threshold: Seconds of no activity before considering task idle
            activity_check_interval: How often to check for activity
            on_state_change: Callback for state transitions
            on_output: Callback for output data
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.command = command
        self.idle_threshold = idle_threshold
        self.activity_check_interval = activity_check_interval
        self.on_state_change = on_state_change
        self.on_output = on_output

        self.state_machine = OneshotStateMachine(self.task_id)
        self.process: Optional[asyncio.subprocess.Process] = None
        self.result = TaskResult(task_id=self.task_id, success=False)
        self.start_time: Optional[float] = None
        self._stop_event = asyncio.Event()

        # Output buffers
        self.stdout_buffer: List[str] = []
        self.stderr_buffer: List[str] = []

    async def run(self) -> TaskResult:
        """
        Execute the task asynchronously.

        Returns:
            TaskResult containing execution results
        """
        self.start_time = asyncio.get_event_loop().time()

        try:
            # Start the subprocess
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )

            # Update state machine with process reference
            self.state_machine.process = self.process

            # Start state machine
            old_state = self.state_machine.current_state
            self.state_machine.start()
            self._notify_state_change(old_state, self.state_machine.current_state)

            # Create concurrent tasks for monitoring
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._read_stream(self.process.stdout, self.stdout_buffer))
                tg.create_task(self._read_stream(self.process.stderr, self.stderr_buffer))
                tg.create_task(self._monitor_health())

            # Wait for process completion
            returncode = await self.process.wait()
            self.result.exit_code = returncode
            self.result.execution_time = asyncio.get_event_loop().time() - self.start_time

            # Determine final state
            if self._stop_event.is_set():
                # Task was interrupted
                old_state = self.state_machine.current_state
                self.state_machine.interrupt()
                self._notify_state_change(old_state, self.state_machine.current_state)
                self.result.success = False
            elif returncode == 0:
                # Successful completion
                old_state = self.state_machine.current_state
                self.state_machine.finish()
                self._notify_state_change(old_state, self.state_machine.current_state)
                self.result.success = True
            else:
                # Failed
                old_state = self.state_machine.current_state
                self.state_machine.fail()
                self._notify_state_change(old_state, self.state_machine.current_state)
                self.result.success = False

        except asyncio.CancelledError:
            # Task was cancelled
            old_state = self.state_machine.current_state
            self.state_machine.interrupt()
            self._notify_state_change(old_state, self.state_machine.current_state)
            self.result.success = False
            raise
        except Exception as e:
            # Unexpected error
            old_state = self.state_machine.current_state
            self.state_machine.fail()
            self._notify_state_change(old_state, self.state_machine.current_state)
            self.result.error = str(e)
            self.result.success = False

        # Prepare final result
        self.result.output = ''.join(self.stdout_buffer)
        if self.stderr_buffer:
            self.result.error = ''.join(self.stderr_buffer)

        return self.result

    async def _read_stream(self, stream: Optional[asyncio.StreamReader], buffer: List[str]):
        """
        Read from a stream and buffer the output.

        Args:
            stream: The stream to read from
            buffer: List to append output lines to
        """
        if not stream:
            return

        try:
            while not self._stop_event.is_set():
                try:
                    # Wait for data with timeout
                    line = await asyncio.wait_for(
                        stream.readline(),
                        timeout=self.activity_check_interval
                    )
                except asyncio.TimeoutError:
                    # No data available, continue checking
                    continue

                if not line:  # EOF
                    break

                line_str = line.decode('utf-8', errors='replace').rstrip('\n\r')
                buffer.append(line_str + '\n')

                # Update activity and notify
                self.state_machine.update_activity()
                if self.on_output:
                    self.on_output(line_str)

                # If we were idle, transition back to running
                if self.state_machine.current_state_enum == TaskState.IDLE:
                    old_state = self.state_machine.current_state_enum
                    self.state_machine.detect_activity()
                    self._notify_state_change(old_state, self.state_machine.current_state_enum)

        except asyncio.CancelledError:
            raise
        except Exception:
            # Log error but don't fail the task
            pass

    async def _monitor_health(self):
        """
        Monitor task health and handle state transitions.
        """
        try:
            while not self._stop_event.is_set() and self.process and self.process.poll() is None:
                await asyncio.sleep(self.activity_check_interval)

                # Check if process is still running
                if self.process.poll() is not None:
                    break

                # Check for idle timeout
                current_time = asyncio.get_event_loop().time()
                if self.state_machine.last_activity:
                    idle_time = current_time - self.state_machine.last_activity
                    if (idle_time > self.idle_threshold and
                        self.state_machine.current_state_enum == TaskState.RUNNING):
                        old_state = self.state_machine.current_state_enum
                        self.state_machine.detect_silence()
                        self._notify_state_change(old_state, self.state_machine.current_state_enum)

        except asyncio.CancelledError:
            raise
        except Exception:
            # Log error but don't fail the task
            pass

    def interrupt(self):
        """Interrupt the running task."""
        self._stop_event.set()
        if self.state_machine.can_interrupt():
            old_state = self.state_machine.current_state
            self.state_machine.interrupt()
            self._notify_state_change(old_state, self.state_machine.current_state)

    def _notify_state_change(self, old_state: TaskState, new_state: TaskState):
        """Notify listeners of state changes."""
        if old_state != new_state:
            # Emit event asynchronously (fire and forget)
            event_type = self._get_event_type_for_state(new_state)
            if event_type:
                # Create task to emit event without blocking
                asyncio.create_task(self._emit_state_change_event(event_type))

            # Call the callback if provided
            if self.on_state_change:
                self.on_state_change(old_state, new_state)

    def _get_event_type_for_state(self, state: TaskState) -> Optional[EventType]:
        """Get the event type for a state."""
        state_event_map = {
            TaskState.CREATED: EventType.TASK_CREATED,
            TaskState.RUNNING: EventType.TASK_STARTED,
            TaskState.IDLE: EventType.TASK_IDLE,
            TaskState.INTERRUPTED: EventType.TASK_INTERRUPTED,
            TaskState.COMPLETED: EventType.TASK_COMPLETED,
            TaskState.FAILED: EventType.TASK_FAILED,
        }
        return state_event_map.get(state)

    async def _emit_state_change_event(self, event_type: EventType):
        """Emit a state change event."""
        try:
            await self.state_machine.emit_event(
                event_type,
                command=self.command,
                execution_time=self.result.execution_time if self.result.execution_time else 0,
                exit_code=self.result.exit_code
            )
        except Exception as e:
            # Don't let event emission errors affect task execution
            print(f"Warning: Failed to emit event {event_type}: {e}")

    @property
    def state(self) -> TaskState:
        """Get the current task state."""
        return self.state_machine.current_state_enum

    @property
    def is_finished(self) -> bool:
        """Check if the task has finished."""
        return self.state_machine.is_finished()

    @property
    def can_interrupt(self) -> bool:
        """Check if the task can be interrupted."""
        return self.state_machine.can_interrupt()