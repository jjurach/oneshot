# Change: Phase 2 - Core Architecture Refactoring (The Context)

## Related Project Plan
- `dev_notes/project_plans/2026-01-20_refactor_phase_2_context.md`

## Overview
Implemented the Context layer for the Oneshot core refactoring. This layer manages the shared memory and data protocol between the Worker and Auditor agents, providing atomic persistence and high-quality result extraction from noisy log streams.

## Files Modified

### New Files Created

#### 1. `src/oneshot/context.py`
- **ExecutionContext** class: Core persistence layer for session state
  - Atomic file writing using temporary file + rename pattern
  - Schema migration for backward compatibility
  - Full CRUD operations for state, metadata, variables, and results
  - State history tracking with timestamps and process IDs
  - Methods:
    - `save()`: Atomic write to JSON file
    - `set_state()`, `get_state()`: State management with history
    - `set_worker_result()`, `get_worker_result()`: Worker output storage
    - `set_auditor_result()`, `get_auditor_result()`: Auditor verdict storage
    - `set_metadata()`, `get_metadata()`: Session metadata
    - `set_variable()`, `get_variable()`: Task variables
    - `increment_iteration()`: Iteration counter
    - `to_dict()`: Export entire context

**Key Design:**
- Uses `tempfile.NamedTemporaryFile()` + `os.replace()` for atomic writes
- Prevents data corruption if process crashes during write
- Maintains complete state transition history for auditing and recovery
- Version 1 schema with migration support for future upgrades

#### 2. `src/oneshot/protocol.py`
- **ResultExtractor** class: Extracts high-quality output from noisy logs
  - Parses NDJSON format (`oneshot-log.json`)
  - Scores candidates based on heuristics:
    - "DONE" keyword: +10 points
    - JSON structure: +5 points
    - "status" field: +8 points
    - "result" field: +5 points
    - Substantial length (>50 chars): +3 points
    - Valid JSON bonus: +2 points
  - Robustly handles malformed JSON lines (skips gracefully)
  - Returns best-scored candidate or None
  - Methods:
    - `extract_result(log_path)`: Main extraction method
    - `_score_text(text)`: Heuristic scoring
    - `_format_event(event)`: Event to text conversion

- **PromptGenerator** class: Context-aware prompt generation
  - Injects session context into prompts for continuity
  - Methods:
    - `generate_worker_prompt()`: Task + feedback + previous work + variables
    - `generate_auditor_prompt()`: Task + worker result for review
    - `generate_recovery_prompt()`: Forensic analysis prompts
  - Tracks iteration number for multi-loop scenarios
  - Preserves context across retries

**Key Design:**
- Scoring weights are configurable (via `score_weights` dict)
- Handles multiple event format variations (output, stdout, text, content, message, data)
- Graceful degradation: returns None for empty logs instead of raising errors

### Test Files Created

#### 3. `tests/test_context.py` (19 tests)
Coverage areas:
- **Basic Operations** (4 tests):
  - Create new context
  - File creation on save
  - Load existing context
  - Invalid JSON error handling

- **Atomic Write** (3 tests):
  - No corruption on multiple writes
  - Temp file cleanup
  - Concurrent save pattern robustness

- **State Management** (2 tests):
  - History recording with metadata
  - Persistence across reloads

- **Metadata & Variables** (3 tests):
  - Set/get operations
  - Default values
  - Persistence

- **Results Storage** (3 tests):
  - Worker/Auditor result operations
  - Isolation between results
  - Persistence across reloads

- **Iteration Counter** (2 tests):
  - Increment operations
  - Persistence

- **Export** (1 test):
  - `to_dict()` returns copy (immutability)

- **Migration** (1 test):
  - Schema migration adds missing fields

#### 4. `tests/test_protocol.py` (26 tests)
Coverage areas:
- **Result Scoring** (6 tests):
  - DONE keyword scoring
  - JSON structure scoring
  - Status/result field scoring
  - Substantial length scoring
  - Combined scoring
  - Empty text handling

- **Event Formatting** (5 tests):
  - Standard field extraction (output, stdout, text, content, message, data)
  - Dict stringification
  - Empty dict handling

- **Result Extraction** (7 tests):
  - Single best candidate selection
  - JSON preference over plain text
  - Malformed JSON line skipping
  - Empty log handling
  - Best-score selection
  - Nonexistent file graceful handling
  - Complex realistic log parsing

- **Worker Prompt Generation** (4 tests):
  - Basic prompt structure
  - Feedback injection
  - Previous work context
  - Variable substitution

- **Auditor Prompt Generation** (2 tests):
  - Basic prompt structure
  - Iteration number tracking

- **Recovery Prompt Generation** (2 tests):
  - Basic recovery prompt
  - Executor logs inclusion

## Impact Assessment

### Positive Impacts
- **Persistence**: Atomic writes prevent data loss on crashes
- **Resilience**: Malformed data doesn't crash extraction (graceful degradation)
- **Traceability**: Full history tracking enables audit trails and recovery
- **Context Continuity**: Multi-iteration loops maintain full context
- **Testability**: 45 comprehensive tests provide confidence in both happy and error paths

### Architectural Alignment
- Follows Phase 1 patterns (type-safe, pure functions where possible)
- Integrates with `OnehotState` enum and `StateMachine` from Phase 1
- Designed to work with Pipeline (Phase 3) for streaming integration
- Provides foundation for Engine (Phase 4) orchestration

### Code Quality
- All tests pass (45/45)
- No regressions in existing code
- Follows existing naming conventions and patterns
- Comprehensive docstrings for all public methods
- Type annotations throughout

## Testing Strategy
- Unit tests for all public methods
- Integration tests for multi-step workflows (save/load cycles)
- Error handling tests (invalid JSON, missing files)
- Backward compatibility tests (schema migration)

## Next Steps
Phase 3 (Pipeline - The Nervous System) will consume ResultExtractor and ExecutionContext to:
- Process streaming output from executors
- Extract and store results
- Trigger state transitions via Engine

## Commit Information
- **Commit Hash**: 14e5c82
- **Author**: Claude Haiku 4.5
- **Timestamp**: 2026-01-21
- **Files Changed**: 4 (2 implementation, 2 test)
- **Lines Added**: 1,143
