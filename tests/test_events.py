"""Tests for async event system."""

import pytest
import asyncio
from oneshot.events import event_emitter, EventType, EventPayload, emit_task_event


class TestEventSystem:
    """Test the async event system."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)  # Should complete quickly
    async def test_event_emission_and_subscription(self):
        """Test basic event emission and subscription."""
        events_received = []

        async def event_handler(event: EventPayload):
            events_received.append(event)

        # Subscribe to events
        await event_emitter.subscribe(EventType.TASK_STARTED, event_handler)

        # Start emitter
        await event_emitter.start()

        # Emit an event
        test_event = EventPayload(
            event_type=EventType.TASK_STARTED,
            timestamp="2023-01-01T00:00:00",
            data={"test": "data"}
        )
        await event_emitter.emit(test_event)

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        # Check event was received
        assert len(events_received) == 1
        assert events_received[0].event_type == EventType.TASK_STARTED
        assert events_received[0].data["test"] == "data"

        # Clean up
        await event_emitter.stop()
        await event_emitter.unsubscribe(EventType.TASK_STARTED, event_handler)

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)  # Should complete quickly
    async def test_task_event_convenience_function(self):
        """Test the convenience function for emitting task events."""
        events_received = []
        event_received_event = asyncio.Event()

        async def event_handler(event):
            events_received.append(event)
            event_received_event.set()

        await event_emitter.subscribe(EventType.TASK_COMPLETED, event_handler)
        await event_emitter.start()

        # Emit using convenience function
        await emit_task_event(EventType.TASK_COMPLETED, "task-123", command="echo test")

        # Wait for event to be received with timeout
        try:
            await asyncio.wait_for(event_received_event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("Event was not received within timeout")

        assert len(events_received) == 1
        assert events_received[0].task_id == "task-123"
        assert events_received[0].data["command"] == "echo test"

        await event_emitter.stop()
        await event_emitter.unsubscribe(EventType.TASK_COMPLETED, event_handler)
