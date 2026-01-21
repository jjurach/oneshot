"""Tests for oneshot.state module (Phase 1 - The Brain).

Table-driven tests for state transitions and action logic.
"""

import pytest
from oneshot.state import (
    OnehotState,
    ActionType,
    Action,
    StateMachine,
    InvalidTransitionError,
)


class TestOnehotState:
    """Test OnehotState enumeration."""

    def test_all_states_defined(self):
        """Verify all required states are defined."""
        required_states = {
            OnehotState.CREATED,
            OnehotState.COMPLETED,
            OnehotState.FAILED,
            OnehotState.REJECTED,
            OnehotState.INTERRUPTED,
            OnehotState.WORKER_EXECUTING,
            OnehotState.AUDITOR_EXECUTING,
            OnehotState.AUDIT_PENDING,
            OnehotState.REITERATION_PENDING,
            OnehotState.RECOVERY_PENDING,
        }
        for state in required_states:
            assert state in OnehotState


class TestActionType:
    """Test ActionType enumeration."""

    def test_all_action_types_defined(self):
        """Verify all required action types are defined."""
        required_types = {
            ActionType.RUN_WORKER,
            ActionType.RUN_AUDITOR,
            ActionType.RECOVER,
            ActionType.EXIT,
            ActionType.WAIT,
        }
        for action_type in required_types:
            assert action_type in ActionType


class TestAction:
    """Test Action dataclass."""

    def test_action_creation(self):
        """Test creating an action."""
        action = Action(ActionType.RUN_WORKER)
        assert action.type == ActionType.RUN_WORKER
        assert action.payload == {}

    def test_action_with_payload(self):
        """Test action with payload."""
        payload = {"reason": "success"}
        action = Action(ActionType.EXIT, payload=payload)
        assert action.type == ActionType.EXIT
        assert action.payload == payload


class TestStateMachineTransitions:
    """Table-driven tests for state transitions."""

    def test_lifecycle_transitions(self):
        """Test lifecycle state transitions."""
        sm = StateMachine()

        # CREATED -> WORKER_EXECUTING
        next_state = sm.transition(OnehotState.CREATED, "start")
        assert next_state == OnehotState.WORKER_EXECUTING

        # WORKER_EXECUTING -> AUDIT_PENDING (Success)
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "success")
        assert next_state == OnehotState.AUDIT_PENDING

        # AUDIT_PENDING -> AUDITOR_EXECUTING
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        # AUDITOR_EXECUTING -> COMPLETED (Done)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "done")
        assert next_state == OnehotState.COMPLETED

    def test_worker_crash_transitions(self):
        """Test transitions after worker crash."""
        sm = StateMachine()

        # WORKER_EXECUTING -> RECOVERY_PENDING (Crash)
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "crash")
        assert next_state == OnehotState.RECOVERY_PENDING

        # WORKER_EXECUTING -> RECOVERY_PENDING (Inactivity)
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "inactivity")
        assert next_state == OnehotState.RECOVERY_PENDING

    def test_active_transitions(self):
        """Test active state transitions."""
        sm = StateMachine()

        # AUDIT_PENDING -> AUDITOR_EXECUTING
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        # AUDITOR_EXECUTING -> COMPLETED (Done)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "done")
        assert next_state == OnehotState.COMPLETED

        # AUDITOR_EXECUTING -> REITERATION_PENDING (Retry)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "retry")
        assert next_state == OnehotState.REITERATION_PENDING

        # AUDITOR_EXECUTING -> REJECTED (Impossible)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "impossible")
        assert next_state == OnehotState.REJECTED

    def test_recovery_transitions(self):
        """Test recovery state transitions."""
        sm = StateMachine()

        # WORKER_EXECUTING -> RECOVERY_PENDING
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "crash")
        assert next_state == OnehotState.RECOVERY_PENDING

        # RECOVERY_PENDING -> AUDIT_PENDING (Zombie Success)
        next_state = sm.transition(OnehotState.RECOVERY_PENDING, "zombie_success")
        assert next_state == OnehotState.AUDIT_PENDING

        # RECOVERY_PENDING -> REITERATION_PENDING (Zombie Partial)
        next_state = sm.transition(OnehotState.RECOVERY_PENDING, "zombie_partial")
        assert next_state == OnehotState.REITERATION_PENDING

        # RECOVERY_PENDING -> FAILED (Zombie Dead)
        next_state = sm.transition(OnehotState.RECOVERY_PENDING, "zombie_dead")
        assert next_state == OnehotState.FAILED

    def test_reiteration_transitions(self):
        """Test reiteration state transitions."""
        sm = StateMachine()

        # REITERATION_PENDING -> WORKER_EXECUTING
        next_state = sm.transition(OnehotState.REITERATION_PENDING, "next")
        assert next_state == OnehotState.WORKER_EXECUTING

        # REITERATION_PENDING -> FAILED (Max Iterations)
        next_state = sm.transition(OnehotState.REITERATION_PENDING, "max_iterations")
        assert next_state == OnehotState.FAILED

    def test_interrupt_transitions(self):
        """Test interrupt transitions from various states."""
        sm = StateMachine()

        # CREATED -> INTERRUPTED
        next_state = sm.transition(OnehotState.CREATED, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

        # WORKER_EXECUTING -> INTERRUPTED
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

        # AUDIT_PENDING -> INTERRUPTED
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

        # AUDITOR_EXECUTING -> INTERRUPTED
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

        # REITERATION_PENDING -> INTERRUPTED
        next_state = sm.transition(OnehotState.REITERATION_PENDING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

        # RECOVERY_PENDING -> INTERRUPTED
        next_state = sm.transition(OnehotState.RECOVERY_PENDING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

    def test_auditor_crash_transitions(self):
        """Test transitions when auditor crashes."""
        sm = StateMachine()

        # AUDITOR_EXECUTING -> FAILED (Crash)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "crash")
        assert next_state == OnehotState.FAILED

        # AUDITOR_EXECUTING -> FAILED (Inactivity)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "inactivity")
        assert next_state == OnehotState.FAILED

    def test_terminal_states_no_transitions(self):
        """Test that terminal states have no valid transitions."""
        sm = StateMachine()
        terminal_states = [
            OnehotState.COMPLETED,
            OnehotState.FAILED,
            OnehotState.REJECTED,
        ]
        for state in terminal_states:
            # Try various events that should fail
            with pytest.raises(InvalidTransitionError):
                sm.transition(state, "any_event")

    def test_invalid_transition_rejected_to_retry(self):
        """Test that invalid transition raises error."""
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            # Cannot transition from COMPLETED to REITERATION_PENDING
            sm.transition(OnehotState.COMPLETED, "retry")

    def test_invalid_transition_created_to_audit(self):
        """Test that invalid transition raises error."""
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            # Cannot jump from CREATED directly to AUDIT_PENDING
            sm.transition(OnehotState.CREATED, "success")

    def test_invalid_event_name(self):
        """Test that invalid event name raises error."""
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition(OnehotState.WORKER_EXECUTING, "invalid_event")


class TestStateMachineActions:
    """Test action logic based on current state."""

    def test_action_for_created_state(self):
        """Test action when in CREATED state."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.CREATED)
        assert action.type == ActionType.RUN_WORKER

    def test_action_for_worker_executing_state(self):
        """Test action when worker is executing."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.WORKER_EXECUTING)
        assert action.type == ActionType.WAIT

    def test_action_for_audit_pending_state(self):
        """Test action when audit is pending."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.AUDIT_PENDING)
        assert action.type == ActionType.RUN_AUDITOR

    def test_action_for_auditor_executing_state(self):
        """Test action when auditor is executing."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.AUDITOR_EXECUTING)
        assert action.type == ActionType.WAIT

    def test_action_for_reiteration_pending_state(self):
        """Test action when reiteration is pending."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.REITERATION_PENDING)
        assert action.type == ActionType.RUN_WORKER

    def test_action_for_recovery_pending_state(self):
        """Test action when recovery is pending."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.RECOVERY_PENDING)
        assert action.type == ActionType.RECOVER

    def test_action_for_completed_state(self):
        """Test action when task is completed."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.COMPLETED)
        assert action.type == ActionType.EXIT
        assert action.payload.get("reason") == "success"

    def test_action_for_rejected_state(self):
        """Test action when task is rejected."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.REJECTED)
        assert action.type == ActionType.EXIT
        assert action.payload.get("reason") == "success"

    def test_action_for_failed_state(self):
        """Test action when task fails."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.FAILED)
        assert action.type == ActionType.EXIT
        assert action.payload.get("reason") == "failed"

    def test_action_for_interrupted_state(self):
        """Test action when task is interrupted."""
        sm = StateMachine()
        action = sm.get_next_action(OnehotState.INTERRUPTED)
        assert action.type == ActionType.EXIT
        assert action.payload.get("reason") == "interrupted"


class TestStateMachineScenarios:
    """Integration scenarios testing complete workflows."""

    def test_successful_completion_scenario(self):
        """Test complete successful workflow."""
        sm = StateMachine()

        # 1. Start from CREATED
        assert sm.get_next_action(OnehotState.CREATED).type == ActionType.RUN_WORKER

        # 2. Worker completes successfully
        next_state = sm.transition(OnehotState.CREATED, "start")
        assert next_state == OnehotState.WORKER_EXECUTING

        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "success")
        assert next_state == OnehotState.AUDIT_PENDING
        assert sm.get_next_action(OnehotState.AUDIT_PENDING).type == ActionType.RUN_AUDITOR

        # 3. Auditor runs
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        # 4. Auditor completes with DONE verdict
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "done")
        assert next_state == OnehotState.COMPLETED
        assert sm.get_next_action(OnehotState.COMPLETED).type == ActionType.EXIT

    def test_retry_scenario(self):
        """Test retry workflow."""
        sm = StateMachine()

        # First iteration
        next_state = sm.transition(OnehotState.CREATED, "start")
        assert next_state == OnehotState.WORKER_EXECUTING

        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "success")
        assert next_state == OnehotState.AUDIT_PENDING

        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        # Auditor requests retry
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "retry")
        assert next_state == OnehotState.REITERATION_PENDING
        assert sm.get_next_action(OnehotState.REITERATION_PENDING).type == ActionType.RUN_WORKER

        # Second iteration
        next_state = sm.transition(OnehotState.REITERATION_PENDING, "next")
        assert next_state == OnehotState.WORKER_EXECUTING

        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "success")
        assert next_state == OnehotState.AUDIT_PENDING

        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        # Auditor completes successfully
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "done")
        assert next_state == OnehotState.COMPLETED

    def test_zombie_success_scenario(self):
        """Test zombie success recovery scenario."""
        sm = StateMachine()

        # Worker starts
        next_state = sm.transition(OnehotState.CREATED, "start")
        assert next_state == OnehotState.WORKER_EXECUTING

        # Worker crashes/timeout
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "crash")
        assert next_state == OnehotState.RECOVERY_PENDING
        assert sm.get_next_action(OnehotState.RECOVERY_PENDING).type == ActionType.RECOVER

        # Recovery finds zombie success
        next_state = sm.transition(OnehotState.RECOVERY_PENDING, "zombie_success")
        assert next_state == OnehotState.AUDIT_PENDING

        # Continue normally
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "done")
        assert next_state == OnehotState.COMPLETED

    def test_rejected_scenario(self):
        """Test rejected task scenario."""
        sm = StateMachine()

        # Worker starts
        next_state = sm.transition(OnehotState.CREATED, "start")
        assert next_state == OnehotState.WORKER_EXECUTING

        # Worker completes
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "success")
        assert next_state == OnehotState.AUDIT_PENDING

        # Auditor runs
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        assert next_state == OnehotState.AUDITOR_EXECUTING

        # Auditor rejects task
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "impossible")
        assert next_state == OnehotState.REJECTED
        assert sm.get_next_action(OnehotState.REJECTED).type == ActionType.EXIT

    def test_interrupt_scenario(self):
        """Test interrupt scenario at various points."""
        sm = StateMachine()

        # Interrupt from CREATED
        next_state = sm.transition(OnehotState.CREATED, "interrupt")
        assert next_state == OnehotState.INTERRUPTED
        assert sm.get_next_action(OnehotState.INTERRUPTED).type == ActionType.EXIT

        # Interrupt from WORKER_EXECUTING
        next_state = sm.transition(OnehotState.CREATED, "start")
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

        # Interrupt from AUDITOR_EXECUTING
        sm2 = StateMachine()
        sm2.transition(OnehotState.CREATED, "start")
        sm2.transition(OnehotState.WORKER_EXECUTING, "success")
        sm2.transition(OnehotState.AUDIT_PENDING, "next")
        next_state = sm2.transition(OnehotState.AUDITOR_EXECUTING, "interrupt")
        assert next_state == OnehotState.INTERRUPTED

    def test_auditor_timeout_is_fatal(self):
        """Test that auditor timeout results in FAILED."""
        sm = StateMachine()

        # Setup through to AUDITOR_EXECUTING
        sm.transition(OnehotState.CREATED, "start")
        sm.transition(OnehotState.WORKER_EXECUTING, "success")
        sm.transition(OnehotState.AUDIT_PENDING, "next")

        # Auditor timeout -> FAILED (fatal)
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "inactivity")
        assert next_state == OnehotState.FAILED

    def test_max_iterations_check(self):
        """Test max iterations transition."""
        sm = StateMachine()

        # Multiple iterations before hitting max
        next_state = sm.transition(OnehotState.CREATED, "start")
        next_state = sm.transition(OnehotState.WORKER_EXECUTING, "success")
        next_state = sm.transition(OnehotState.AUDIT_PENDING, "next")
        next_state = sm.transition(OnehotState.AUDITOR_EXECUTING, "retry")
        assert next_state == OnehotState.REITERATION_PENDING

        # Max iterations reached
        next_state = sm.transition(OnehotState.REITERATION_PENDING, "max_iterations")
        assert next_state == OnehotState.FAILED
