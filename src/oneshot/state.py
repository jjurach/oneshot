"""
Oneshot State Machine (Phase 1 - The Brain)

Pure business logic, state transitions, and action definitions.
This module encapsulates the authoritative state machine and action selection logic.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Set, Any, Optional


class OnehotState(Enum):
    """Authoritative enumeration of all possible states in the Oneshot lifecycle."""

    # Lifecycle terminal states
    CREATED = auto()
    COMPLETED = auto()
    FAILED = auto()
    REJECTED = auto()
    INTERRUPTED = auto()

    # Active states (subprocess running)
    WORKER_EXECUTING = auto()
    AUDITOR_EXECUTING = auto()

    # Checkpoint states (safe transition points)
    AUDIT_PENDING = auto()
    REITERATION_PENDING = auto()
    RECOVERY_PENDING = auto()


class ActionType(Enum):
    """Types of actions the Engine can execute."""
    RUN_WORKER = auto()
    RUN_AUDITOR = auto()
    RECOVER = auto()
    EXIT = auto()
    WAIT = auto()


@dataclass
class Action:
    """
    Represents an action that the Engine should execute.

    Attributes:
        type: The type of action to perform.
        payload: Additional context data for the action.
    """
    type: ActionType
    payload: Dict[str, Any] = field(default_factory=dict)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class StateMachine:
    """
    Core state machine implementing the Oneshot state logic.

    Responsibilities:
    - Validate transitions between states
    - Determine the next action based on current state
    - Manage the authoritative transition table
    """

    # Authoritative state transition table
    # Maps: current_state -> set of valid next states
    TRANSITIONS: Dict[OnehotState, Set[OnehotState]] = {
        # From CREATED
        OnehotState.CREATED: {
            OnehotState.WORKER_EXECUTING,
            OnehotState.INTERRUPTED,
        },

        # From WORKER_EXECUTING
        OnehotState.WORKER_EXECUTING: {
            OnehotState.AUDIT_PENDING,
            OnehotState.RECOVERY_PENDING,
            OnehotState.FAILED,
            OnehotState.INTERRUPTED,
        },

        # From AUDIT_PENDING
        OnehotState.AUDIT_PENDING: {
            OnehotState.AUDITOR_EXECUTING,
            OnehotState.INTERRUPTED,
        },

        # From AUDITOR_EXECUTING
        OnehotState.AUDITOR_EXECUTING: {
            OnehotState.COMPLETED,
            OnehotState.REITERATION_PENDING,
            OnehotState.REJECTED,
            OnehotState.FAILED,
            OnehotState.INTERRUPTED,
        },

        # From REITERATION_PENDING
        OnehotState.REITERATION_PENDING: {
            OnehotState.WORKER_EXECUTING,
            OnehotState.FAILED,
            OnehotState.INTERRUPTED,
        },

        # From RECOVERY_PENDING
        OnehotState.RECOVERY_PENDING: {
            OnehotState.AUDIT_PENDING,
            OnehotState.REITERATION_PENDING,
            OnehotState.FAILED,
            OnehotState.INTERRUPTED,
        },

        # Terminal states (can only self-loop)
        OnehotState.COMPLETED: set(),
        OnehotState.FAILED: set(),
        OnehotState.REJECTED: set(),
        OnehotState.INTERRUPTED: set(),
    }

    # Map event types to transition outcomes
    # Format: (current_state, event_type) -> next_state
    _EVENT_TRANSITIONS = {
        (OnehotState.CREATED, "start"): OnehotState.WORKER_EXECUTING,
        (OnehotState.CREATED, "interrupt"): OnehotState.INTERRUPTED,

        (OnehotState.WORKER_EXECUTING, "success"): OnehotState.AUDIT_PENDING,
        (OnehotState.WORKER_EXECUTING, "crash"): OnehotState.RECOVERY_PENDING,
        (OnehotState.WORKER_EXECUTING, "inactivity"): OnehotState.RECOVERY_PENDING,
        (OnehotState.WORKER_EXECUTING, "interrupt"): OnehotState.INTERRUPTED,

        (OnehotState.AUDIT_PENDING, "next"): OnehotState.AUDITOR_EXECUTING,
        (OnehotState.AUDIT_PENDING, "interrupt"): OnehotState.INTERRUPTED,

        (OnehotState.AUDITOR_EXECUTING, "done"): OnehotState.COMPLETED,
        (OnehotState.AUDITOR_EXECUTING, "retry"): OnehotState.REITERATION_PENDING,
        (OnehotState.AUDITOR_EXECUTING, "impossible"): OnehotState.REJECTED,
        (OnehotState.AUDITOR_EXECUTING, "crash"): OnehotState.FAILED,
        (OnehotState.AUDITOR_EXECUTING, "inactivity"): OnehotState.FAILED,
        (OnehotState.AUDITOR_EXECUTING, "interrupt"): OnehotState.INTERRUPTED,

        (OnehotState.REITERATION_PENDING, "next"): OnehotState.WORKER_EXECUTING,
        (OnehotState.REITERATION_PENDING, "max_iterations"): OnehotState.FAILED,
        (OnehotState.REITERATION_PENDING, "interrupt"): OnehotState.INTERRUPTED,

        (OnehotState.RECOVERY_PENDING, "zombie_success"): OnehotState.AUDIT_PENDING,
        (OnehotState.RECOVERY_PENDING, "zombie_partial"): OnehotState.REITERATION_PENDING,
        (OnehotState.RECOVERY_PENDING, "zombie_dead"): OnehotState.FAILED,
        (OnehotState.RECOVERY_PENDING, "interrupt"): OnehotState.INTERRUPTED,
    }

    def __init__(self):
        """Initialize the state machine."""
        self.current_state = OnehotState.CREATED

    def transition(self, current: OnehotState, event_type: str) -> OnehotState:
        """
        Determine the next state given a current state and event.

        Args:
            current: The current state.
            event_type: The event that occurred (e.g., "success", "crash", "interrupt").

        Returns:
            The next state to transition to.

        Raises:
            InvalidTransitionError: If the transition is not valid.

        Examples:
            >>> sm = StateMachine()
            >>> sm.transition(OnehotState.CREATED, "start")
            <OnehotState.WORKER_EXECUTING: 1>

            >>> sm.transition(OnehotState.WORKER_EXECUTING, "success")
            <OnehotState.AUDIT_PENDING: 9>
        """
        key = (current, event_type)

        if key not in self._EVENT_TRANSITIONS:
            raise InvalidTransitionError(
                f"Invalid transition: ({current.name}, {event_type})"
            )

        next_state = self._EVENT_TRANSITIONS[key]

        # Validate against transition table
        if next_state not in self.TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(
                f"Transition from {current.name} to {next_state.name} is not allowed"
            )

        return next_state

    def get_next_action(self, state: OnehotState) -> Action:
        """
        Determine the next action to execute based on the current state.

        Args:
            state: The current state.

        Returns:
            An Action object describing what the Engine should do next.

        Examples:
            >>> sm = StateMachine()
            >>> action = sm.get_next_action(OnehotState.CREATED)
            >>> action.type
            <ActionType.RUN_WORKER: 1>

            >>> action = sm.get_next_action(OnehotState.AUDIT_PENDING)
            >>> action.type
            <ActionType.RUN_AUDITOR: 2>
        """
        if state == OnehotState.CREATED:
            return Action(ActionType.RUN_WORKER)

        elif state == OnehotState.WORKER_EXECUTING:
            return Action(ActionType.WAIT)

        elif state == OnehotState.AUDIT_PENDING:
            return Action(ActionType.RUN_AUDITOR)

        elif state == OnehotState.AUDITOR_EXECUTING:
            return Action(ActionType.WAIT)

        elif state == OnehotState.REITERATION_PENDING:
            return Action(ActionType.RUN_WORKER)

        elif state == OnehotState.RECOVERY_PENDING:
            return Action(ActionType.RECOVER)

        elif state in (OnehotState.COMPLETED, OnehotState.REJECTED):
            return Action(ActionType.EXIT, payload={"reason": "success"})

        elif state in (OnehotState.FAILED, OnehotState.INTERRUPTED):
            return Action(ActionType.EXIT, payload={"reason": state.name.lower()})

        else:
            # Fallback for unknown state
            raise ValueError(f"Unknown state: {state}")
