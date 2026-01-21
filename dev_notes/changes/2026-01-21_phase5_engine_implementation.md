# Change: Phase 5 Core Architecture Refactoring - The Orchestrator (OnehotEngine)

## Related Project Plan
`dev_notes/project_plans/2026-01-20_refactor_phase_5_orchestrator.md`

## Overview
Implemented the `OnehotEngine` class, the main orchestration loop that ties together the State Machine, Executors, and Streaming Pipeline. This completes Phase 5 of the core architecture refactoring, transforming from the monolithic imperative `run_oneshot` function to a modular, event-driven architecture.

## Components Implemented

### 1. **src/oneshot/engine.py** (New File)
A complete implementation of the `OnehotEngine` class with the following responsibilities:

#### Core Loop
- `run()`: Main orchestration loop that cycles through states, queries the state machine for actions, and executes them
- Signal handling for graceful interruption (SIGINT)
- Context-based persistence of state transitions

#### Worker Execution
- `_execute_worker()`: Runs the worker agent with inactivity timeout monitoring
- Handles normal completion, inactivity timeouts, crashes, and interruptions
- Supports iteration management with max_iterations enforcement
- Integrates streaming pipeline for real-time output processing

#### Auditor Execution
- `_execute_auditor()`: Runs the auditor agent to validate worker results
- Automatically extracts and parses verdicts (DONE, RETRY, IMPOSSIBLE)
- Transitions state based on auditor decision

#### Recovery Flow
- `_execute_recovery()`: Forensic analysis for dead worker processes
- Supports "Zombie Success" detection - salvaging work from crashed processes
- Categorizes recovery outcomes: success, partial, or dead

#### Pipeline Coordination
- `_pump_pipeline()`: Coordinates the streaming pipeline (ingest → timestamp → timeout → log → parse)
- Integrates with the existing `build_pipeline()` from pipeline.py
- Optional UI callback for real-time rendering

#### Prompt Generation
- `_generate_worker_prompt()`: Creates task prompts with iteration context
- `_generate_auditor_prompt()`: Generates auditor review prompts with work results

#### Verdict Extraction
- `_extract_auditor_verdict()`: Parses auditor output for verdicts
- Keyword-based heuristic detection for DONE/RETRY/IMPOSSIBLE

#### State Management
- `_save_state()`: Persists state transitions to execution context (oneshot.json)
- `_get_context_value()`: Safe context value retrieval with fallbacks
- `_should_exit_success()`: Determines if exit is successful

### 2. **tests/test_engine.py** (New File)
Comprehensive test suite with 29 tests covering:

#### Initialization Tests (3 tests)
- Default initialization
- Custom values initialization
- Signal handler installation

#### State Management Tests (3 tests)
- State persistence
- Safe context value retrieval
- Fallback context access

#### Worker Execution Tests (4 tests)
- Successful execution flow
- Iteration increment handling
- Max iterations enforcement
- Inactivity timeout handling

#### Auditor Execution Tests (4 tests)
- Successful audit flow
- Verdict extraction for DONE
- Verdict extraction for RETRY
- Verdict extraction for IMPOSSIBLE

#### Recovery Tests (3 tests)
- Successful recovery
- Partial recovery
- Dead process handling

#### Prompt Generation Tests (3 tests)
- First iteration prompt
- Reiteration prompt with context
- Auditor prompt with work results

#### Verdict Extraction Tests (4 tests)
- DONE verdict detection
- RETRY verdict detection
- IMPOSSIBLE verdict detection
- Unknown verdict handling

#### Exit Condition Tests (4 tests)
- Success exit on COMPLETED
- Failure exit on FAILED
- Failure exit on INTERRUPTED
- Failure exit on REJECTED

#### Main Loop Test (1 test)
- Simple success path through the main loop

### Key Design Features

1. **Modular Architecture**: Clear separation between state logic, execution, and I/O
2. **Error Handling**: Comprehensive handling of timeouts, crashes, and interruptions
3. **Recovery Capability**: Forensic analysis for "Zombie Success" detection
4. **Graceful Interruption**: SIGINT handling with proper state transitions
5. **Streaming Integration**: Direct integration with the existing pipeline
6. **Context Safety**: Defensive programming with fallback context access
7. **Extensibility**: Easy to add new actions, states, or executor types

### Interface Integration

The engine integrates with:
- **StateMachine** (state.py): State transitions and action selection
- **ExecutionContext** (context.py): State persistence and metadata
- **Executors** (providers/base.py): Worker and Auditor execution
- **Pipeline** (pipeline.py): Streaming data processing
- **ResultExtractor** (protocol.py): Result parsing from logs

## Files Modified
- Created: `src/oneshot/engine.py` (498 lines)
- Created: `tests/test_engine.py` (470 lines)

## Testing Results
- ✅ 29 new engine tests: PASSED
- ✅ 475 total tests: PASSED (no regressions)
- ✅ 5 skipped tests
- ✅ 0 failures

## Architecture Alignment
Fully implements the architecture specification in `docs/streaming-and-state-management.md`:
- ✅ The Orchestrator (Engine) main loop
- ✅ State machine integration
- ✅ Executor abstraction usage
- ✅ Pipeline streaming integration
- ✅ Recovery handling for RECOVERY_PENDING state
- ✅ Interruption handling for INTERRUPTED state
- ✅ Context persistence and transitions

## Next Steps
The implementation is complete and tested. The following steps remain:
1. Integration with CLI (oneshot_cli.py) - currently optional
2. Documentation updates (if needed)
3. Demo script validation (if applicable)

## Code Quality
- Follows existing code patterns and style
- Comprehensive error handling with defensive programming
- Clear separation of concerns
- Type hints throughout
- Extensive docstrings
- 100% test coverage of major code paths
