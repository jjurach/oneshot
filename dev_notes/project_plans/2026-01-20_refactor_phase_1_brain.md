# Project Plan: Core Architecture Refactoring - Phase 1: The Brain

**Status:** COMPLETED

## Overview
This phase focuses on implementing the pure business logic, state transitions, and persistence layer. This is the "Brain" of the application, responsible for deciding *what* to do next without performing any side effects.

## Related Documents
- `docs/streaming-and-state-management.md` (Architecture Specification)

## Objectives
- Define the authoritative State Enum.
- Implement the State Machine transition logic.
- Define the Action dataclasses that the Engine will execute.

## Components & Code Samples

### 1. `src/oneshot/state.py`

**Concept:** Pure Logic Enums and State Machine.

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

class OnehotState(Enum):
    # Lifecycle
    CREATED = auto()
    COMPLETED = auto()
    FAILED = auto()
    REJECTED = auto()
    INTERRUPTED = auto()
    
    # Active
    WORKER_EXECUTING = auto()
    AUDITOR_EXECUTING = auto()
    
    # Checkpoints
    AUDIT_PENDING = auto()
    REITERATION_PENDING = auto()
    RECOVERY_PENDING = auto()

class ActionType(Enum):
    RUN_WORKER = auto()
    RUN_AUDITOR = auto()
    RECOVER = auto()
    EXIT = auto()
    WAIT = auto()

@dataclass
class Action:
    type: ActionType
    payload: Dict[str, Any] = field(default_factory=dict)

class StateMachine:
    TRANSITIONS = {
        OnehotState.CREATED: {OnehotState.WORKER_EXECUTING, OnehotState.INTERRUPTED},
        OnehotState.WORKER_EXECUTING: {
            OnehotState.AUDIT_PENDING,
            OnehotState.RECOVERY_PENDING,
            OnehotState.FAILED,
            OnehotState.INTERRUPTED
        },
        # ... full table ...
    }

    def transition(self, current: OnehotState, event_type: str) -> OnehotState:
        # Logic to map (current, event) -> next
        pass

    def get_next_action(self, state: OnehotState) -> Action:
        if state == OnehotState.CREATED:
            return Action(ActionType.RUN_WORKER)
        elif state == OnehotState.AUDIT_PENDING:
            return Action(ActionType.RUN_AUDITOR)
        # ... logic ...
```

## Checklist
- [ ] Create `src/oneshot/state.py`
- [ ] Define `OnehotState` Enum
- [ ] Define `Action` and `ActionType` dataclasses
- [ ] Implement `StateMachine` class structure
- [ ] Define strict `TRANSITIONS` table
- [ ] Implement `transition()` method with validation
- [ ] Implement `get_next_action()` method logic

## Test Plan: `tests/test_state_machine.py`

**Pattern:** Table-driven tests for transitions.

```python
import pytest
from oneshot.state import OnehotState, StateMachine, ActionType

def test_valid_transitions():
    sm = StateMachine()
    
    # Format: (Start State, Event, Expected End State)
    scenarios = [
        (OnehotState.CREATED, "start", OnehotState.WORKER_EXECUTING),
        (OnehotState.WORKER_EXECUTING, "success", OnehotState.AUDIT_PENDING),
        (OnehotState.WORKER_EXECUTING, "crash", OnehotState.RECOVERY_PENDING),
        (OnehotState.RECOVERY_PENDING, "recovered", OnehotState.AUDIT_PENDING),
    ]
    
    for start, event, expected in scenarios:
        assert sm.transition(start, event) == expected

def test_invalid_transitions():
    sm = StateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.transition(OnehotState.CREATED, "audit_success") # Impossible

def test_action_logic():
    sm = StateMachine()
    action = sm.get_next_action(OnehotState.AUDIT_PENDING)
    assert action.type == ActionType.RUN_AUDITOR
```

- [ ] **Test Lifecycle Transitions:**
    - `CREATED` -> `WORKER_EXECUTING`
    - `WORKER_EXECUTING` -> `AUDIT_PENDING` (Success)
    - `WORKER_EXECUTING` -> `FAILED` (Crash)
    - `WORKER_EXECUTING` -> `INTERRUPTED` (Ctrl-C)
- [ ] **Test Active Transitions:**
    - `AUDIT_PENDING` -> `AUDITOR_EXECUTING`
    - `AUDITOR_EXECUTING` -> `COMPLETED` (Done)
    - `AUDITOR_EXECUTING` -> `REITERATION_PENDING` (Retry)
    - `AUDITOR_EXECUTING` -> `REJECTED` (Impossible)
- [ ] **Test Recovery Transitions:**
    - `WORKER_EXECUTING` -> `RECOVERY_PENDING` (Inactivity/Crash)
    - `RECOVERY_PENDING` -> `AUDIT_PENDING` (Zombie Success)
    - `RECOVERY_PENDING` -> `FAILED` (Dead)