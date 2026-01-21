# Change: Phase 4 Implementation - The Hands (Executors Refactoring)

## Related Project Plan
- `dev_notes/project_plans/2026-01-20_refactor_phase_4_hands.md`

## Overview
Implemented Phase 4 of the Core Architecture Refactoring: "The Hands" (Executors). This phase transitions the executor architecture from simple function-based execution (`run_task()`) to a sophisticated context manager pattern with streaming output and forensic recovery capabilities.

**Key Achievement**: All five executors (Direct, Cline, Claude, Gemini, Aider) now support:
1. **Context Manager Pattern**: Streaming output with automatic resource cleanup
2. **Recovery Capability**: Forensic analysis of dead sessions from external state
3. **Process Management**: Proper subprocess lifecycle handling with timeout and force-kill support

## Files Modified

### 1. `src/oneshot/providers/base.py`
**Summary**: Added core interfaces for Phase 4

Changes:
- Added `RecoveryResult` dataclass to represent recovery operation results
- Added `@abstractmethod execute()` with `@contextmanager` decorator for streaming execution
- Added `@abstractmethod recover()` for forensic session recovery
- Maintained backward compatibility with existing `run_task()` interface

**Impact**: Establishes the new architecture contract that all executors must implement

### 2. `src/oneshot/providers/direct_executor.py`
**Summary**: Implemented context manager and recovery for HTTP API executor

Changes:
- Added imports: `contextmanager`, `RecoveryResult`
- Implemented `execute()` context manager:
  - Checks Ollama connection before execution
  - Yields complete response (no persistent process)
  - No cleanup needed for HTTP API
- Implemented `recover()` method:
  - Returns failure result (no persistent state for HTTP API)
  - Properly typed to return `RecoveryResult`

**Impact**: Direct executor ready for streaming pipeline integration

### 3. `src/oneshot/providers/cline_executor.py`
**Summary**: Implemented subprocess streaming and file-based recovery for Cline

Changes:
- Added imports: `subprocess`, `select`, `contextmanager`, `Path`, `Generator`, `RecoveryResult`
- Added `process` attribute to track subprocess lifecycle
- Implemented `execute()` context manager:
  - Creates subprocess with Popen for streaming output
  - Line-buffered stdout for real-time data flow
  - Automatic cleanup: terminate → wait(5s) → force kill
  - Returns generator via `_stream_output()` helper
- Implemented `recover()` method:
  - Forensic analysis of `~/.cline/tasks/{task_id}/ui_messages.json`
  - Parses JSON message history
  - Detects completion indicators ("completion_result" messages)
  - Returns structured recovery data with completion verdict
- Added `_stream_output()` generator helper for subprocess output handling

**Impact**: Cline executor now supports streaming pipeline and dead session recovery

### 4. `src/oneshot/providers/claude_executor.py`
**Summary**: Implemented subprocess streaming and session log recovery for Claude

Changes:
- Added imports: `subprocess`, `contextmanager`, `Path`, `Generator`, `RecoveryResult`
- Added `process` attribute to track subprocess lifecycle
- Implemented `execute()` context manager:
  - Creates subprocess with Popen for streaming output
  - Line-buffered stdout with universal newlines support
  - Automatic cleanup with timeout-based force kill
  - Returns generator for real-time output processing
- Implemented `recover()` method:
  - Multi-location log search:
    - `~/.claude/sessions/{task_id}/log.json`
    - `~/.cache/claude/{task_id}/log.json`
    - `~/.local/share/claude/{task_id}/log.json`
  - Parses JSON and list-based logs
  - Detects completion status from recovered activities
- Added `_stream_output()` generator for subprocess handling

**Impact**: Claude executor integrated with streaming architecture and session recovery

### 5. `src/oneshot/providers/gemini_executor.py`
**Summary**: Implemented subprocess streaming and execution log recovery for Gemini

Changes:
- Added imports: `contextmanager`, `Path`, `Generator`, `RecoveryResult`
- Added `process` attribute for lifecycle tracking
- Implemented `execute()` context manager:
  - Creates subprocess with proper working directory context
  - Line-buffered output with environment isolation
  - Automatic process termination with force-kill fallback
- Implemented `recover()` method:
  - Multi-location search for execution logs:
    - `~/.gemini/logs/{task_id}/output.log`
    - `~/.cache/gemini/{task_id}/log.json`
    - `./{working_dir}/.gemini/{task_id}/log.json`
  - Handles both JSON and plain text logs
  - Status detection for completion verdict
- Added `_stream_output()` generator

**Impact**: Gemini executor ready for streaming pipeline with working directory support

### 6. `src/oneshot/providers/aider_executor.py`
**Summary**: Implemented subprocess streaming and git-based recovery for Aider

Changes:
- Added imports: `contextmanager`, `Path`, `Generator`, `RecoveryResult`
- Added `process` attribute for lifecycle tracking
- Implemented `execute()` context manager:
  - Creates subprocess with DEVNULL stdin (non-interactive)
  - Runs in git_dir context for proper repository handling
  - Line-buffered output with automatic cleanup
- Implemented `recover()` method:
  - Git history analysis: `git log --oneline -20`
  - Extracts commit hashes and messages
  - Optional log file search (`.aider.chat.history.md`, `.aider.log`)
  - Verdict detection from commit messages ("done" keyword)
  - Returns git commit information for audit trail
- Added `_stream_output()` generator

**Impact**: Aider executor leverages git state for robust recovery

## Testing

### New Test Suite: `tests/test_executors_lifecycle.py`
Created comprehensive lifecycle tests covering:

**DirectExecutor Tests**:
- Context manager success path
- Connection error handling
- Recovery returns no-op result

**ClineExecutor Tests**:
- Process creation and streaming
- Process cleanup on context exit
- Force-kill on terminate timeout
- Task file recovery
- Missing file handling

**ClaudeExecutor Tests**:
- Process creation and streaming
- Automatic process termination
- Multi-location log recovery

**GeminiExecutor Tests**:
- Process execution context manager
- Process cleanup verification
- Log recovery attempts

**AiderExecutor Tests**:
- Process execution and cleanup
- Git history recovery

**General Contract Tests**:
- All executors have `execute()` method
- All executors have `recover()` method
- All recovery methods return `RecoveryResult`

**Status**: ✅ All 20 lifecycle tests passing

## Backward Compatibility
- Existing `run_task()` abstract method remains unchanged
- All existing tests continue to pass (428+ passing)
- New interfaces additive, non-breaking

## Architecture Alignment
Phase 4 implementation aligns with the Core Architecture Refactoring specification:
- ✅ BaseExecutor ABC with context manager interface
- ✅ RecoveryResult dataclass for forensic operations
- ✅ Subprocess streaming via generators
- ✅ Resource cleanup with timeout/force-kill pattern
- ✅ Recovery logic for all executor types
- ✅ Comprehensive lifecycle test coverage

## Integration Notes

### Pipeline Integration
The new `execute()` context manager is designed to integrate with the streaming pipeline:
```python
with executor.execute(prompt) as stream:
    for line in stream:
        # Pass to pipeline for processing
```

### Recovery Usage
The `recover()` method enables dead session analysis:
```python
result = executor.recover(task_id)
if result.success:
    for activity in result.recovered_activity:
        # Resume or audit
```

### Timeout Handling
Subprocess cleanup implements proper timeout pattern:
1. Send SIGTERM (graceful shutdown)
2. Wait 5 seconds for graceful exit
3. Send SIGKILL if still running (force kill)

This supports the InactivityMonitor in the pipeline (docs/streaming-and-state-management.md)

## Next Steps
Phase 4 executors are ready for:
1. Pipeline integration (receive stream processing logic)
2. State machine binding (engine.py integration)
3. Inactivity monitor testing
4. End-to-end orchestration tests
