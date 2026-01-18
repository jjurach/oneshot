"""Tests for OneshotStateMachine."""

import pytest
from oneshot.state_machine import OneshotStateMachine, TaskState


class TestStateMachine:
    """Test state machine functionality."""

    def test_state_machine_initial_state(self):
        """Test initial state is CREATED."""
        sm = OneshotStateMachine("test-task")
        assert sm.current_state.id == TaskState.CREATED.value

    def test_state_machine_start_transition(self):
        """Test transition from CREATED to RUNNING."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        assert sm.current_state.id == TaskState.RUNNING.value

    def test_state_machine_idle_detection(self):
        """Test transition from RUNNING to IDLE."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.detect_silence()
        assert sm.current_state.id == TaskState.IDLE.value

    def test_state_machine_activity_resume(self):
        """Test transition from IDLE back to RUNNING."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.detect_silence()
        sm.detect_activity()
        assert sm.current_state.id == TaskState.RUNNING.value

    def test_state_machine_completion(self):
        """Test transition to COMPLETED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.finish()
        assert sm.current_state.id == TaskState.COMPLETED.value

    def test_state_machine_interruption(self):
        """Test transition to INTERRUPTED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.interrupt()
        assert sm.current_state.id == TaskState.INTERRUPTED.value

    def test_state_machine_failure(self):
        """Test transition to FAILED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.fail()
        assert sm.current_state.id == TaskState.FAILED.value

    def test_state_machine_interrupt_from_idle(self):
        """Test interrupt from IDLE state."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.detect_silence()
        sm.interrupt()
        assert sm.current_state.id == TaskState.INTERRUPTED.value

    def test_state_machine_idempotent_fail(self):
        """Test fail is idempotent."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.fail()
        sm.fail()  # Second fail should not error
        assert sm.current_state.id == TaskState.FAILED.value

    def test_state_machine_idempotent_finish(self):
        """Test finish is idempotent."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.finish()
        sm.finish()  # Second finish should not error
        assert sm.current_state.id == TaskState.COMPLETED.value

    def test_state_machine_fail_after_complete(self):
        """Test that fail after complete transitions to FAILED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.finish()
        sm.fail()
        assert sm.current_state.id == TaskState.FAILED.value

    def test_state_machine_complete_from_idle(self):
        """Test completion from IDLE state."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.detect_silence()
        sm.finish()
        assert sm.current_state.id == TaskState.COMPLETED.value

    def test_state_machine_fail_from_interrupted(self):
        """Test fail from INTERRUPTED state."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.interrupt()
        sm.fail()
        assert sm.current_state.id == TaskState.FAILED.value

    def test_state_machine_activity_tracking(self):
        """Test last_activity updates."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        initial_time = sm.last_activity
        import time
        time.sleep(0.01)
        sm.update_activity()
        assert sm.last_activity > initial_time

    def test_state_machine_can_interrupt_running(self):
        """Test can_interrupt returns True for RUNNING."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        assert sm.can_interrupt() is True

    def test_state_machine_can_interrupt_idle(self):
        """Test can_interrupt returns True for IDLE."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.detect_silence()
        assert sm.can_interrupt() is True

    def test_state_machine_cannot_interrupt_completed(self):
        """Test can_interrupt returns False for COMPLETED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.finish()
        assert sm.can_interrupt() is False

    def test_state_machine_is_finished_completed(self):
        """Test is_finished returns True for COMPLETED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.finish()
        assert sm.is_finished() is True

    def test_state_machine_is_finished_failed(self):
        """Test is_finished returns True for FAILED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.fail()
        assert sm.is_finished() is True

    def test_state_machine_is_finished_interrupted(self):
        """Test is_finished returns True for INTERRUPTED."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        sm.interrupt()
        assert sm.is_finished() is True

    def test_state_machine_is_not_finished_running(self):
        """Test is_finished returns False for RUNNING."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        assert sm.is_finished() is False

    def test_state_machine_multiple_transitions(self):
        """Test multiple state transitions in sequence."""
        sm = OneshotStateMachine("test-task")
        sm.start()
        assert sm.current_state.id == TaskState.RUNNING.value
        sm.detect_silence()
        assert sm.current_state.id == TaskState.IDLE.value
        sm.detect_activity()
        assert sm.current_state.id == TaskState.RUNNING.value
        sm.detect_silence()
        assert sm.current_state.id == TaskState.IDLE.value
        sm.finish()
        assert sm.current_state.id == TaskState.COMPLETED.value
