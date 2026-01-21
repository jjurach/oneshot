# Project Plan: Core Architecture Refactoring - Phase 4: The Hands

**Status:** COMPLETED

## Overview
This phase defines the interface for all Executors and implements the concrete classes. It shifts from "Function that returns string" to "Context Manager that yields a stream." Crucially, it adds the `recover()` capability for forensic analysis of dead workers.

## Related Documents
- `docs/streaming-and-state-management.md` (Architecture Specification)

## Objectives
- Define `BaseExecutor` ABC.
- Refactor all supported executors to implement the new interface.
- Implement `recover()` logic for all executors where possible.

## Components & Code Samples

### 1. Base Infrastructure (`src/oneshot/executors/base.py`)

**Concept:** Resource Management (RAII) and Interface Definition.

```python
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator, Any, List
from dataclasses import dataclass

@dataclass
class RecoveryResult:
    success: bool
    recovered_activity: List[Any]
    verdict: str = None

class BaseExecutor(ABC):
    @contextmanager
    @abstractmethod
    def execute(self, prompt: str) -> Generator[Any, None, None]:
        """
        Yields a stream of output.
        Must clean up process on exit.
        """
        pass

    @abstractmethod
    def recover(self, task_id: str) -> RecoveryResult:
        """
        Analyze external state to salvage a dead session.
        """
        pass
```

### 2. Executor Implementations

**Concept:** Subprocess streaming with cleanup.

```python
class ClineExecutor(BaseExecutor):
    @contextmanager
    def execute(self, prompt: str):
        process = subprocess.Popen(..., stdout=subprocess.PIPE)
        try:
            # Important: Use an iterator that can handle timeouts/select
            # for the InactivityMonitor to work.
            yield self._stream_output(process)
        finally:
            if process.poll() is None:
                process.terminate()
    
    def recover(self, task_id: str):
        path = Path(f"~/.cline/tasks/{task_id}/ui_messages.json")
        if path.exists():
            # ... parse logic ...
            return RecoveryResult(True, [...], "DONE")
        return RecoveryResult(False, [])
```

## Checklist

### Part 1: Base & Pilot
- [ ] **Base Infrastructure**
    - [ ] Create `src/oneshot/executors/base.py`.
    - [ ] Define `BaseExecutor` ABC and `RecoveryResult`.
    - [ ] Create `tests/test_executors_base.py` and pass.
- [ ] **Direct Executor**
    - [ ] Refactor `DirectExecutor` in `src/oneshot/executors/direct.py`.
    - [ ] Implement `execute` (streaming HTTP response).
    - [ ] Implement `recover` (No-op).
    - [ ] Update `tests/test_direct_executor.py` to use new interface and pass.

### Part 2: Complex Agents
- [ ] **Cline Executor**
    - [ ] Refactor `ClineExecutor` in `src/oneshot/executors/cline.py`.
    - [ ] Implement `execute` (subprocess stream).
    - [ ] Implement `recover` (File forensics).
    - [ ] Update `tests/test_oneshot_cline_integration.py` (or create new test) and pass.
- [ ] **Claude Executor**
    - [ ] Refactor `ClaudeExecutor` in `src/oneshot/executors/claude.py`.
    - [ ] Implement `execute` (subprocess stream).
    - [ ] Investigate and implement `recover` if possible.
    - [ ] Verify via manual test or mocked test.
- [ ] **Gemini Executor**
    - [ ] Refactor `GeminiExecutor` in `src/oneshot/executors/gemini.py`.
    - [ ] Implement `execute`.
    - [ ] Implement `recover`.
    - [ ] Update `tests/test_gemini_executor.py` and pass.
- [ ] **Aider Executor**
    - [ ] Refactor `AiderExecutor` in `src/oneshot/executors/aider.py`.
    - [ ] Implement `execute`.
    - [ ] Implement `recover` (Git check).
    - [ ] Verify via test.

## Test Plan: `tests/test_executors_lifecycle.py`

**Pattern:** Resource cleanup verification.

```python
def test_executor_cleanup():
    executor = ClineExecutor()
    
    # Simulate an error inside the context
    try:
        with executor.execute("task") as stream:
            raise RuntimeError("Crash!")
    except RuntimeError:
        pass
        
    # Verify the subprocess was killed
    assert executor.process.poll() is not None
```

- [ ] **Create `tests/test_executors_lifecycle.py`**
    - Generic test suite that runs against *all* registered executors to verify the `contextmanager` contract (process starts, process dies).
- [ ] **Test Recovery Specifics:**
    - Each executor needs a specific test mocking its file system artifacts to verify `recover()` parses them correctly.
