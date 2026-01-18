# Project Plan: Oneshot Asynchronous Refactor

## 1. Overview
Refactor the `oneshot` Python library from a synchronous, blocking execution model to an asynchronous, state-aware orchestration engine. The new architecture will support parallel agent executions, non-blocking I/O monitoring, and the ability to interrupt processes via state transitions.

---

## 2. Technical Stack
* **Runtime:** Python 3.10+
* **Asynchronous Core:** `asyncio` (Standard Library)
* **Structured Concurrency:** `anyio` (Task Groups, Concurrency Limiting)
* **Lifecycle Management:** `python-statemachine` (FSM for agent states)
* **Subprocess Management:** `asyncio.subprocess` (Non-blocking I/O)

---

## 3. Architecture Design

### A. State Machine Definition
The `OneshotStateMachine` manages the lifecycle of a single execution task.

| State | Description |
| :--- | :--- |
| **CREATED** | Initial state before process spawn. |
| **RUNNING** | Subprocess is active and emitting logs. |
| **IDLE** | Subprocess is active but no I/O detected for > threshold. |
| **INTERRUPTED** | Terminal state triggered by user/system kill signal. |
| **COMPLETED** | Terminal state for successful exit (Code 0). |
| **FAILED** | Terminal state for error exit (Non-zero). |

### B. The Orchestrator
A central `AsyncOrchestrator` using `anyio.TaskGroup` to:
1. Initialize tasks and attach them to the event loop.
2. Monitor file descriptors for activity.
3. Handle "Heartbeat" logic to transition tasks to `IDLE`.
4. Trigger `process.terminate()` when the state machine enters `INTERRUPTED`.

---

## 4. Implementation Code (Skeleton)

```python
import asyncio
import anyio
from datetime import datetime
from statemachine import StateMachine, State

class OneshotStateMachine(StateMachine):
    # Lifecycle States
    CREATED = State(initial=True)
    RUNNING = State()
    IDLE = State()
    INTERRUPTED = State()
    COMPLETED = State(final=True)
    FAILED = State(final=True)

    # Valid Transitions
    start = CREATED.to(RUNNING)
    detect_silence = RUNNING.to(IDLE)
    detect_activity = IDLE.to(RUNNING)
    interrupt = (RUNNING | IDLE | CREATED).to(INTERRUPTED)
    finish = (RUNNING | IDLE).to(COMPLETED)
    fail = (RUNNING | IDLE | CREATED).to(FAILED)

    def __init__(self, task_id, process_handle=None):
        self.task_id = task_id
        self.process = process_handle
        super().__init__()

    def on_enter_INTERRUPTED(self):
        if self.process:
            self.process.terminate()

class OneshotTask:
    def __init__(self, task_id, command):
        self.task_id = task_id
        self.command = command
        self.machine = OneshotStateMachine(task_id)
        self.last_activity = datetime.now()

    async def run(self):
        self.machine.start()
        self.process = await asyncio.create_subprocess_shell(
            self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.machine.process = self.process
        
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._read_stream, self.process.stdout)
            tg.start_soon(self._monitor_health)

    async def _read_stream(self, stream):
        while True:
            line = await stream.readline()
            if not line: break
            self.last_activity = datetime.now()
            if self.machine.is_IDLE: self.machine.detect_activity()
        
        if not self.machine.is_INTERRUPTED:
            self.machine.finish()

    async def _monitor_health(self):
        while not (self.machine.is_COMPLETED or self.machine.is_FAILED):
            await anyio.sleep(1)
            if (datetime.now() - self.last_activity).total_seconds() > 10:
                if self.machine.is_RUNNING: self.machine.detect_silence()
5. Phase 1 Testing Strategy (Mocked)
We will use pytest-asyncio and unittest.mock to validate the state machine without launching real shell processes.

Test Case: Transition Integrity
Action: Start a task and then call task.machine.interrupt().

Expectation: The state moves to INTERRUPTED and process.terminate() is called exactly once.

Test Case: Silence Detection
Action: Mock the last_activity timestamp to be 15 seconds in the past.

Expectation: The health monitor coroutine triggers detect_silence() and state becomes IDLE.

Test Case: Concurrency Limit
Action: Launch 5 tasks with an anyio.CapacityLimiter(2).

Expectation: Only 2 tasks move to RUNNING state simultaneously; others stay in CREATED.

6. Future Expansion
[ ] UI Integration: Expose the state machine transitions via an async event emitter for web/TUI dashboards.

[ ] Persistence: Save task states and log fragments to a SQLite backend for recovery after crashes.

