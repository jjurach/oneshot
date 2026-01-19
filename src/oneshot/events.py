"""
Async Event System for Oneshot UI Integration

Provides an event-driven architecture for broadcasting task state changes
and system events to UI components (web dashboard, TUI).
"""

import asyncio
import json
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, asdict
from datetime import datetime


class EventType(Enum):
    """Types of events that can be emitted by the system."""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_IDLE = "task_idle"
    TASK_ACTIVITY = "task_activity"
    TASK_INTERRUPTED = "task_interrupted"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SYSTEM_STATUS = "system_status"
    UI_COMMAND = "ui_command"
    EXECUTOR_ACTIVITY = "executor_activity"


@dataclass
class EventPayload:
    """Base event payload structure."""
    event_type: EventType
    timestamp: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = asdict(self)
        result['event_type'] = self.event_type.value
        return result

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class TaskEventPayload(EventPayload):
    """Event payload for task-related events."""
    task_id: str
    command: Optional[str] = None
    state: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class SystemStatusPayload(EventPayload):
    """Event payload for system status updates."""
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    interrupted_tasks: int
    max_concurrent: int

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class UICommandPayload(EventPayload):
    """Event payload for UI commands (e.g., interrupt task)."""
    command: str
    target_task_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ExecutorActivityPayload(EventPayload):
    """Event payload for executor activity (Claude, cline, aider, etc.)."""
    activity_type: str  # e.g., "tool_call", "planning", "file_operation"
    description: str
    executor: str = "unknown"  # Which executor this came from
    task_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    is_sensitive: bool = False  # Whether this event contains sensitive info

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AsyncEventEmitter:
    """
    Asynchronous event emitter using asyncio.Queue for broadcasting events.

    Provides a pub/sub system where:
    - Components can subscribe to specific event types
    - Events are broadcast asynchronously without blocking emitters
    - Multiple subscribers can listen to the same events
    """

    def __init__(self, queue_size: int = 1000):
        """
        Initialize the event emitter.

        Args:
            queue_size: Maximum number of events to buffer
        """
        self.queue: asyncio.Queue[EventPayload] = asyncio.Queue(maxsize=queue_size)
        self.subscribers: Dict[EventType, List[Callable[[EventPayload], Awaitable[None]]]] = {}
        self._running = False
        self._dispatcher_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the event dispatcher."""
        if self._running:
            return

        # Recreate queue to handle potential event loop changes (e.g., in tests)
        try:
            # Check if queue is bound to current event loop
            _ = self.queue._loop
            if _ != asyncio.get_running_loop():
                # Queue is bound to different loop, recreate it
                old_maxsize = self.queue.maxsize if hasattr(self.queue, 'maxsize') else 1000
                self.queue = asyncio.Queue(maxsize=old_maxsize)
        except (AttributeError, RuntimeError):
            # No running loop or queue doesn't have _loop, recreate to be safe
            old_maxsize = self.queue.maxsize if hasattr(self.queue, 'maxsize') else 1000
            self.queue = asyncio.Queue(maxsize=old_maxsize)

        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatch_events())

    async def stop(self):
        """Stop the event dispatcher."""
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass

    async def emit(self, event: EventPayload):
        """
        Emit an event asynchronously.

        Args:
            event: The event payload to emit
        """
        try:
            # Non-blocking put with timeout
            await asyncio.wait_for(
                self.queue.put(event),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            # Queue is full, drop the event to prevent blocking
            print(f"Warning: Event queue full, dropping event: {event.event_type}")

    def emit_nowait(self, event: EventPayload):
        """
        Emit an event without waiting (fire and forget).

        Args:
            event: The event payload to emit
        """
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Queue is full, drop the event
            print(f"Warning: Event queue full, dropping event: {event.event_type}")

    async def subscribe(self, event_type: EventType, callback: Callable[[EventPayload], Awaitable[None]]):
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            callback: Async function to call when event is received
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    async def unsubscribe(self, event_type: EventType, callback: Callable[[EventPayload], Awaitable[None]]):
        """
        Unsubscribe from events of a specific type.

        Args:
            event_type: Type of events to unsubscribe from
            callback: The callback function to remove
        """
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                if not self.subscribers[event_type]:
                    del self.subscribers[event_type]
            except ValueError:
                pass  # Callback not found

    async def _dispatch_events(self):
        """Internal event dispatcher that runs in a separate task."""
        try:
            while self._running:
                try:
                    # Wait for next event
                    event = await self.queue.get()

                    # Dispatch to subscribers
                    if event.event_type in self.subscribers:
                        tasks = []
                        for callback in self.subscribers[event.event_type]:
                            # Create task for each callback to run concurrently
                            task = asyncio.create_task(callback(event))
                            tasks.append(task)

                        # Wait for all callbacks to complete (with timeout)
                        if tasks:
                            try:
                                await asyncio.wait_for(
                                    asyncio.gather(*tasks, return_exceptions=True),
                                    timeout=5.0
                                )
                            except asyncio.TimeoutError:
                                print(f"Warning: Event callbacks for {event.event_type} timed out")

                    # Mark task as done
                    self.queue.task_done()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error in event dispatcher: {e}")
                    continue

        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    async def get_event_stream(self) -> asyncio.Queue[EventPayload]:
        """
        Get a queue for consuming all events (useful for UI components).

        Returns:
            A queue that will receive copies of all events
        """
        event_queue = asyncio.Queue(maxsize=100)

        async def forward_event(event: EventPayload):
            try:
                # Create a copy to avoid reference issues
                event_copy = EventPayload(
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    data=event.data.copy() if event.data else {}
                )
                event_queue.put_nowait(event_copy)
            except asyncio.QueueFull:
                # Drop event if consumer queue is full
                pass

        # Subscribe to all event types
        for event_type in EventType:
            await self.subscribe(event_type, forward_event)

        return event_queue

    @property
    def queue_size(self) -> int:
        """Get the current queue size."""
        return self.queue.qsize()

    @property
    def subscriber_count(self) -> int:
        """Get the total number of subscribers across all event types."""
        return sum(len(callbacks) for callbacks in self.subscribers.values())


# Global event emitter instance
event_emitter = AsyncEventEmitter()


async def emit_task_event(event_type: EventType, task_id: str, **kwargs):
    """
    Convenience function to emit task-related events.

    Args:
        event_type: The type of task event
        task_id: The task ID
        **kwargs: Additional event data
    """
    event = TaskEventPayload(
        event_type=event_type,
        timestamp=datetime.now().isoformat(),
        task_id=task_id,
        data=kwargs
    )
    await event_emitter.emit(event)


async def emit_system_status(total_tasks: int, running_tasks: int, completed_tasks: int,
                           failed_tasks: int, interrupted_tasks: int, max_concurrent: int):
    """
    Convenience function to emit system status events.

    Args:
        total_tasks: Total number of tasks
        running_tasks: Number of currently running tasks
        completed_tasks: Number of completed tasks
        failed_tasks: Number of failed tasks
        interrupted_tasks: Number of interrupted tasks
        max_concurrent: Maximum concurrent tasks allowed
    """
    event = SystemStatusPayload(
        event_type=EventType.SYSTEM_STATUS,
        timestamp=datetime.now().isoformat(),
        data={},
        total_tasks=total_tasks,
        running_tasks=running_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        interrupted_tasks=interrupted_tasks,
        max_concurrent=max_concurrent
    )
    await event_emitter.emit(event)


async def emit_executor_activity(activity_type: str, description: str, executor: str = "unknown",
                                task_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
                                is_sensitive: bool = False):
    """
    Convenience function to emit executor activity events.

    Args:
        activity_type: Type of activity (tool_call, planning, file_operation, etc.)
        description: Human-readable description of the activity
        executor: Which executor this came from (claude, cline, aider, etc.)
        task_id: Associated task ID if applicable
        details: Additional structured details about the activity
        is_sensitive: Whether this event contains sensitive information
    """
    event = ExecutorActivityPayload(
        event_type=EventType.EXECUTOR_ACTIVITY,
        timestamp=datetime.now().isoformat(),
        data={},
        activity_type=activity_type,
        description=description,
        executor=executor,
        task_id=task_id,
        details=details or {},
        is_sensitive=is_sensitive
    )
    await event_emitter.emit(event)