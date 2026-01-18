# Project Plan: Oneshot Asynchronous Refactor

## Objective
Refactor the `oneshot` Python library from a synchronous, blocking execution model to an asynchronous, state-aware orchestration engine. The new architecture will support parallel agent executions, non-blocking I/O monitoring, and the ability to interrupt processes via state transitions.

## Implementation Steps
1. **Install Required Dependencies** (Completed)
   - Add `anyio` for structured concurrency and task groups
   - Add `python-statemachine` for finite state machine implementation
   - Update `pyproject.toml` and `requirements.txt` with new dependencies

2. **Implement State Machine** (Completed)
   - Create `OneshotStateMachine` class with states: CREATED, RUNNING, IDLE, INTERRUPTED, COMPLETED, FAILED
   - Define valid transitions: start, detect_silence, detect_activity, interrupt, finish, fail
   - Implement `on_enter_INTERRUPTED` handler to terminate processes

3. **Create OneshotTask Class** (Completed)
   - Initialize with task_id and command
   - Implement async `run()` method to start subprocess and manage state
   - Add `_read_stream()` coroutine for monitoring stdout/stderr
   - Add `_monitor_health()` coroutine for silence detection and state transitions

4. **Implement AsyncOrchestrator** (Completed)
   - Use `anyio.TaskGroup` for managing concurrent tasks
   - Implement heartbeat logic for idle detection
   - Add concurrency limiting with `anyio.CapacityLimiter`
   - Handle process termination on interrupt signals

5. **Update Core Oneshot Module** (Completed)
   - Refactor `src/oneshot/oneshot.py` to use async patterns
   - Replace synchronous subprocess calls with `asyncio.subprocess`
   - Integrate state machine and orchestrator into main execution flow

6. **Update CLI Interface** (Completed)
   - Modify `src/cli/oneshot_cli.py` to support async execution
   - Add command-line options for concurrency limits and timeout thresholds
   - Implement graceful shutdown handling

7. **Update Tests** (In Progress)
   - Refactor existing synchronous tests in `tests/test_oneshot.py` and `tests/test_cli.py`
   - Add new async tests using `pytest-asyncio`
   - Implement mocked tests for state machine transitions

## Success Criteria
- All existing synchronous functionality preserved and working
- New async execution supports parallel task running
- State machine correctly manages task lifecycles
- Processes can be interrupted via state transitions
- Idle detection works with configurable thresholds
- Concurrency limiting prevents resource exhaustion
- All tests pass including new async test cases

## Testing Strategy
- **Unit Tests**: Test state machine transitions in isolation using mocked processes
- **Integration Tests**: Test full async execution with real subprocesses but controlled commands
- **Mocked Testing**: Use `pytest-asyncio` and `unittest.mock` for Phase 1 validation:
  - Transition Integrity: Verify INTERRUPTED state triggers process.terminate()
  - Silence Detection: Mock timestamps to test IDLE state transitions
  - Concurrency Limit: Test CapacityLimiter restricts simultaneous RUNNING tasks
- **Performance Tests**: Benchmark parallel execution vs sequential
- **Edge Case Tests**: Test interrupt during various states, process failures, I/O storms

## Risk Assessment
- **Concurrency Complexity**: Async code introduces race conditions; mitigation: thorough testing with anyio's structured concurrency
- **Backward Compatibility**: Existing sync API users may break; mitigation: maintain sync wrapper functions initially
- **Resource Management**: Uncontrolled subprocess spawning; mitigation: implement capacity limiting and proper cleanup
- **State Machine Correctness**: Invalid transitions could lead to hanging processes; mitigation: comprehensive state transition testing
- **Performance Overhead**: Async overhead vs sync simplicity; mitigation: benchmark and optimize critical paths
- **Dependency Management**: New dependencies may have security issues; mitigation: pin versions and monitor updates