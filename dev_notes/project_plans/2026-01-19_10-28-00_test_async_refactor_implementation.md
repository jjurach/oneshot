# Project Plan: Test Async Refactor Implementation

## 1. Overview
Test the implementation of the async refactor plan described in `dev_notes/specs/2026-01-18_13-48-51_prompt-01.md`. The refactor converts the oneshot library from synchronous blocking execution to an asynchronous, state-aware orchestration engine with parallel task execution, non-blocking I/O monitoring, and interrupt capabilities.

## 2. Technical Stack
* **Testing Framework:** pytest with pytest-asyncio
* **Mocking:** unittest.mock for subprocess and async mocking
* **Async Testing:** anyio for structured concurrency testing
* **Process Management:** PTY allocation and subprocess mocking

## 3. Implementation Steps

### Phase 1: Baseline Testing
- Run existing test suite to verify current functionality
- Ensure all state machine tests pass
- Verify orchestrator basic functionality
- Check PTY streaming works with real processes

### Phase 2: State Machine Validation
- Test all state transitions match prompt specifications
- Verify process termination on INTERRUPTED state
- Test activity tracking and idle detection
- Validate transition guards and constraints

### Phase 3: Orchestrator Testing
- Test concurrency limiting with CapacityLimiter(2)
- Verify parallel execution of multiple tasks
- Test heartbeat monitoring for idle tasks
- Validate graceful shutdown on interrupt signals

### Phase 4: Integration Testing
- Test full async oneshot execution with real prompts
- Verify streaming output with PTY allocation
- Test adaptive timeouts and activity monitoring
- Validate session logging in async mode

### Phase 5: Edge Case Testing
- Test process interruption during execution
- Verify cleanup on various failure modes
- Test concurrent task limits and queuing
- Validate error propagation and handling

## 4. Success Criteria
- All existing tests pass (100% success rate)
- State machine behaves exactly as specified in prompt
- Orchestrator handles concurrency limits correctly
- PTY streaming provides real-time output
- Async execution completes successfully with real workloads
- Graceful handling of interrupts and timeouts
- Session logging works in async mode

## 5. Testing Strategy

### Unit Tests (Existing)
- State machine transition integrity
- Orchestrator concurrency limits
- Process management and cleanup

### Integration Tests (To Add)
- Full async oneshot workflow
- Real PTY streaming with subprocesses
- Concurrent task execution limits
- Interrupt signal handling

### Mocked Tests (Existing)
- State machine without real processes
- Orchestrator with mocked tasks
- PTY allocation failure scenarios

## 6. Risk Assessment
- **High:** Async testing complexity - mitigated by pytest-asyncio and anyio
- **Medium:** PTY allocation platform differences - tested on Linux
- **Low:** State machine logic errors - comprehensive unit tests exist
- **Low:** Process cleanup issues - tested in multiple failure scenarios

## 7. Dependencies
- pytest>=7.0.0 with pytest-asyncio
- anyio>=3.0.0 for structured concurrency
- statemachine library for FSM implementation
- pty module (Unix/Linux only)

## 8. Deliverables
- Updated test suite with integration tests
- Test execution report showing all requirements met
- Validation that implementation matches prompt specifications
- Documentation of any gaps or improvements needed