# Implementation Reference

This document provides practical implementation patterns and reference implementations for oneshot.

## Quick Reference

- **[Adding a New Executor]**: See [Section](#adding-a-new-executor)
- **[State Machine Transitions]**: See [Section](#state-machine-transitions)

## Project-Specific Patterns

### Adding a New Executor

**Use Case:** When adding support for a new AI coding tool or provider.

**Implementation:**

Executors should inherit from the base executor class and implement the required interface.

```python
from oneshot.executors.base import BaseExecutor

class NewExecutor(BaseExecutor):
    async def execute(self, prompt: str):
        # Implementation...
        pass
```

### State Machine Transitions

**Use Case:** Defining new steps in the autonomous workflow.

**Implementation:**

Uses `python-statemachine`.

```python
from statemachine import StateMachine, State

class TaskMachine(StateMachine):
    idle = State(initial=True)
    working = State()
    done = State(final=True)

    start = idle.to(working)
    finish = working.to(done)
```

## Testing Patterns

### Async Test Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_async_feature():
    # Test...
    pass
```

## See Also

- [Architecture](architecture.md) - System design
- [Workflows](workflows.md) - Development workflows
- [Definition of Done](definition-of-done.md) - Quality standards

---
Last Updated: 2026-02-01
