# Streaming Activity and State Management Architecture

## Overview

This document specifies the architecture for the `oneshot` core refactoring. The goal is to move from a monolithic imperative function (`run_oneshot`) to a modular, state-driven architecture that supports robust streaming, inactivity detection, interruption recovery, and granular state tracking.

The system is decomposed into four distinct layers:
1.  **State (The Brain)**: Pure logic and persistence. Decides *what* to do.
2.  **Pipeline (The Nervous System)**: Streaming data processing using generators.
3.  **Executors (The Hands)**: Process management yielding streams.
4.  **Engine (The Orchestrator)**: The main loop connecting the components.

---

## 1. Architectural Decomposition

### 1.1 `src/oneshot/state.py` (The Brain)
*   **Responsibility**: Encapsulates the business logic and persistence. It maintains the "Truth" of the session.
*   **Key Components**:
    *   `OnehotState` (Enum): The definitive list of possible states.
    *   `ExecutionContext` (Class): Represents the loaded `oneshot.json` file (metadata, history, variables).
    *   `StateMachine` (Class): Contains the transition logic.
*   **Principle**: Pure logic. It does not execute commands. It receives an `Event` (e.g., "Worker finished with exit code 0") and returns a `NextAction` (e.g., "Run Auditor").

### 1.2 `src/oneshot/pipeline.py` (The Nervous System)
*   **Responsibility**: Handles the flow of information from the running process to the log files and the user.
*   **Key Concept**: **Python Generators**.
*   **Structure**: A composed pipeline that processes the executor's output stream in a single pass:
    1.  **Ingest**: Read raw chunks/lines from the executor.
    2.  **Timestamp**: Wrap in `OneshotActivity` with ingestion time.
    3.  **Inactivity Monitor**: Pass-through generator that raises `InactivityTimeout` if no data yields for N seconds.
    4.  **Log**: Append to `oneshot-log.json` (Side effect).
    5.  **Parse**: Extract semantic meaning (JSON parsing, sensitive data redaction).
    6.  **Yield**: Pass processed events to the UI/Engine.

### 1.3 `src/oneshot/executors/` (The Hands)
*   **Responsibility**: Interface with external agents (Claude, Cline, Aider, etc.).
*   **Key Concept**: **Context Managers yielding Generators**.
*   **Interface**:
    ```python
    @contextlib.contextmanager
    def execute(self, prompt: str) -> Generator[str, None, None]:
        # setup subprocess (using non-blocking I/O)
        yield stdout_stream
        # cleanup/terminate subprocess on exit
    
    def recover(self, task_id: str) -> RecoveryResult:
        # Forensic analysis of external state (files, logs)
        pass
    ```
*   **Benefit**: Automatic cleanup of child processes if the user hits Ctrl-C or Inactivity Timeout occurs.

### 1.4 `src/oneshot/engine.py` (The Orchestrator)
*   **Responsibility**: The main event loop.
*   **Logic**:
    1.  Load State.
    2.  Ask StateMachine for `NextAction`.
    3.  If Action is `RUN`, invoke Executor + Pipeline.
    4.  Feed Executor exit status back to StateMachine.
    5.  Repeat until Terminal State.

---

## 2. The State Machine Specification

We distinguish between **Process States** (is a subprocess running?) and **Semantic States** (what does this mean for the task?).

### 2.1 State Definitions (`OnehotState` Enum)

#### Lifecycle States
*   `CREATED`: Session initialized, no work started.
*   `COMPLETED`: **Success**. The Auditor returned a "DONE" verdict.
*   `FAILED`: **Exhaustion**. Max iterations reached, or unrecoverable error (crash).
*   `REJECTED`: **Refusal**. The Auditor determined the task cannot be completed (e.g., "I need a credit card", "Permission denied").
*   `INTERRUPTED`: **Paused**. The user sent SIGINT (Ctrl-C) or SIGTERM. The session is healthy and can be resumed.

#### Active States (Hot)
*   `WORKER_EXECUTING`: The worker agent subprocess is running.
*   `AUDITOR_EXECUTING`: The auditor agent subprocess is running.

#### Checkpoint States (Safe Resume/Transition Points)
*   `AUDIT_PENDING`: The Worker finished successfully (exit code 0). The system is waiting to run the Auditor.
    *   *Resume Action:* Start Auditor immediately.
*   `REITERATION_PENDING`: The Auditor finished with a "retry" verdict. The system is waiting to run the Worker again.
    *   *Resume Action:* Start Worker (Iteration N+1) immediately.
*   **`RECOVERY_PENDING`**: The Worker process died, was killed due to inactivity, or crashed. The system needs to perform forensic analysis to determine if the work was actually completed.
    *   *Resume Action:* Run `executor.recover()` to check for "Zombie Success".

### 2.2 Transition Logic Table

| Current State | Event / Condition | Next State | Notes |
| :--- | :--- | :--- | :--- |
| `CREATED` | `run()` called | `WORKER_EXECUTING` | Start Iteration 1 |
| **`WORKER_EXECUTING`** | Exit Code 0 | `AUDIT_PENDING` | Worker done, ready to audit |
| | Inactivity Timeout | `RECOVERY_PENDING` | Kill process, check for results |
| | Exit Code != 0 | `RECOVERY_PENDING` | Crash detected, check for results |
| | SIGINT (Ctrl-C) | `INTERRUPTED` | User paused |
| **`RECOVERY_PENDING`** | Recovery finds "Success" | `AUDIT_PENDING` | Zombie Success salvaged |
| | Recovery finds "Partial" | `REITERATION_PENDING` | Salvage partial work |
| | Recovery finds Nothing | `FAILED` | Truly dead |
| **`AUDIT_PENDING`** | `next()` called | `AUDITOR_EXECUTING` | Start Auditor |
| **`AUDITOR_EXECUTING`**| Exit Code 0 + Verdict "DONE" | `COMPLETED` | Task Success |
| | Exit Code 0 + Verdict "RETRY" | `REITERATION_PENDING` | Loop back |
| | Exit Code 0 + Verdict "IMPOSSIBLE"| `REJECTED` | Agent refused task |
| | Exit Code != 0 | `FAILED` | Auditor crashed |
| | SIGINT (Ctrl-C) | `INTERRUPTED` | User paused |
| | Inactivity Timeout | `FAILED` | Auditor timeout is fatal |
| **`REITERATION_PENDING`**| `next()` called | `WORKER_EXECUTING` | Start Iteration N+1 |
| | Max Iterations Reached | `FAILED` | Give up |

---

## 3. Resume and Recovery Strategy

### 3.1 Inactivity & "Zombie Success"
**Scenario**: The agent completes the task but the pipe hangs or the CLI crashes before reporting success.
**Solution**:
1.  **Inactivity Monitor** in `pipeline.py` raises `InactivityTimeout` after N seconds of silence.
2.  Orchestrator kills the process group.
3.  State transitions to `RECOVERY_PENDING`.
4.  Engine calls `executor.recover(task_id)`.
5.  Executor inspects its own logs/storage (e.g., `~/.cline/tasks/...`) for the *real* last message.
6.  If a "DONE" message is found, it is replayed into the `oneshot-log.json`, and state moves to `AUDIT_PENDING`.

### 3.2 Resuming from `INTERRUPTED`
When `oneshot --resume <id>` is called on an `INTERRUPTED` state:
1.  **Check History**: Look at the last entry in `state_history`.
2.  **Determine Context**:
    *   If last state was `WORKER_EXECUTING` -> Transition to `RECOVERY_PENDING`. (Assume the interruption might have killed a successful worker).
    *   If last state was `AUDIT_PENDING` -> Transition to `AUDIT_PENDING`.
    *   If last state was `AUDITOR_EXECUTING` -> Re-run Auditor.

### 3.3 Resuming from `REJECTED`
**Action**: Deny resume.
**Reason**: The agent explicitly refused the task. Resuming creates a loop of refusal. The user must create a *new* session with modified prompts/inputs.

---

## 4. File Formats

### 4.1 `oneshot.json` (State File)
Updated to include granular state tracking.

```json
{
  "oneshot_id": "uuid",
  "state": "RECOVERY_PENDING",
  "iteration_count": 2,
  "max_iterations": 5,
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "history": [
    {"state": "CREATED", "ts": 123},
    {"state": "WORKER_EXECUTING", "ts": 124, "pid": 1001},
    {"state": "RECOVERY_PENDING", "ts": 200, "reason": "inactivity_timeout"}
  ]
}
```

### 4.2 `oneshot-log.json` (Activity Log)
Remains as NDJSON. The `pipeline.py` module ensures strictly valid JSON lines.

```json
{"ts": 1700001, "type": "activity", "executor": "cline", "data": {...}}
{"ts": 1700002, "type": "state_change", "from": "WORKER_EXECUTING", "to": "RECOVERY_PENDING"}
```