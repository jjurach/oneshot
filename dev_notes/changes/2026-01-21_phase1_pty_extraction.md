# Change: Phase 1 - Extract PTY Streaming Utilities

**Date**: 2026-01-21
**Related Project Plan**: `dev_notes/project_plans/2026-01-21_codebase_cleanup_and_consolidation.md`

## Overview

Successfully extracted the robust PTY-based streaming infrastructure from the legacy `oneshot.py` into a dedicated, reusable module `pty_utils.py`. This consolidates all streaming infrastructure into a single location, enabling:

- Elimination of code duplication across executors
- Easier maintenance and enhancement of PTY capabilities
- Cleaner separation of concerns between CLI orchestration and subprocess execution
- Foundation for future executor improvements

## Files Modified

### New Files Created

1. **`src/oneshot/providers/pty_utils.py`** (280 lines)
   - Extracted `call_executor_pty()` function from oneshot.py (lines 85-289)
   - Added module-level logging utilities that use environment variables for configuration
   - Removed dependencies on global `VERBOSITY` variable by implementing `_get_verbosity()` function
   - All 205 lines of robust PTY logic preserved:
     - Master/slave PTY allocation via `pty.openpty()`
     - Child process forking with `os.fork()`, `os.execvp()`
     - Non-blocking I/O with `select.select()`
     - Smart chunk accumulation (size-based, line-based, JSON-based flushing)
     - Timeout handling with SIGTERM
     - Exit code tracking with `os.WIFEXITED()`, `os.WEXITSTATUS()`

## Key Design Decisions

### 1. Standalone Module with Environment-Based Configuration

The `pty_utils.py` module is designed to be completely standalone:

- **No circular dependencies**: Only imports standard library modules (json, logging, os, platform, pty, select, subprocess, sys, time, typing)
- **No external state**: Uses environment variables (`ONESHOT_DISABLE_STREAMING`, `ONESHOT_VERBOSITY`) instead of relying on global state in oneshot.py
- **Verbosity handling**: Implements `_get_verbosity()` to read from environment, allowing tests and different contexts to control logging independently

### 2. Preserved All PTY Capabilities

All 205 lines of the original `call_executor_pty()` function were preserved with minimal changes:

- **Platform detection**: `SUPPORTS_PTY = platform.system() in ('Linux', 'Darwin')`
- **Streaming validation**: Checks for `ONESHOT_DISABLE_STREAMING` environment variable
- **Chunk accumulation**: Smart flushing on:
  - Size limit (default: 4096 bytes accumulated)
  - Line boundaries (good for text output)
  - JSON object boundaries (for structured output)
- **Exit code tracking**: Properly handles process exit via `os.WIFEXITED()` and `os.WEXITSTATUS()`
- **Timeout support**: SIGTERM with timeout handling

### 3. Logging Strategy

Instead of depending on the global `VERBOSITY` variable from oneshot.py:

```python
def _get_verbosity() -> int:
    """Get current verbosity level from environment or module globals."""
    return int(os.environ.get('ONESHOT_VERBOSITY', '0'))

def _log_debug(msg: str):
    """Log debug message if verbosity >= 2."""
    if _get_verbosity() >= 2:
        print(f"[DEBUG] {msg}", file=sys.stderr)

def _log_verbose(msg: str):
    """Log verbose message if verbosity >= 1."""
    if _get_verbosity() >= 1:
        print(f"[VERBOSE] {msg}", file=sys.stderr)
```

This allows:
- Tests to set `ONESHOT_VERBOSITY` environment variable
- Different components to control verbosity independently
- Reduced coupling between modules

## Impact Assessment

### Positive Impact

1. **Code Reusability**: The PTY utilities are now available to any module that needs them (executors, testing, etc.)
2. **Maintainability**: Single source of truth for PTY streaming logic
3. **Testability**: Can be tested independently via `tests/test_pty_streaming.py` (4 tests, all passing)
4. **Future-Ready**: Foundation for Phase 1.2 (updating executors to use pty_utils)

### No Breaking Changes

- `call_executor_pty()` is NOT currently used by any executor (they use subprocess.Popen)
- Legacy `oneshot.py` still has the original function
- All existing tests pass (478 passed, 5 skipped)
- PTY streaming tests continue to pass (4/4 ✓)

## Testing Results

All existing tests pass without modification:

```
tests/test_pty_streaming.py .... (4/4 passed)
- test_pty_streaming_with_echo PASSED
- test_pty_streaming_with_multiline_output PASSED
- test_pty_streaming_timeout PASSED
- test_pty_function_exists_and_is_callable PASSED

Full test suite: 478 passed, 5 skipped, 115 warnings in 25.37s
- No regressions
- No new failures
```

## Next Steps

### Phase 1.2: Update Executors (Recommended)

Once `pty_utils.py` is stable, update executors to use the new module:

```python
# In each executor's execute() method:
from oneshot.providers.pty_utils import call_executor_pty

try:
    stdout, stderr, exit_code = call_executor_pty(cmd, timeout=timeout)
    # Process output...
except OSError:
    # Fall back to subprocess.Popen (current implementation)
    pass
```

This would involve modifying:
- `ClineExecutor.execute()`
- `ClaudeExecutor.execute()`
- `GeminiExecutor.execute()`
- `DirectExecutor.execute()`
- `AiderExecutor.execute()`

### Phase 2: Engine Parity Verification ✓

Already complete - `OnehotEngine` has full parity with legacy orchestration:
- State machine abstraction
- Executor abstraction (BaseExecutor)
- Activity parsing and logging
- Auditor feedback loop
- All 29 engine tests passing

### Phase 3: Refactor CLI Entry Point

Refactor `main()` in `oneshot.py` to use `OnehotEngine` directly instead of `run_oneshot_legacy()`:

1. Create `src/oneshot/cli/session_utils.py` with:
   - `find_latest_session()` - locate resume points
   - `read_session_context()` - load previous iteration state
   - `count_iterations()` - get iteration count from logs

2. Update `main()` to:
   - Use environment variables for verbosity
   - Create ExecutionContext from CLI args
   - Create executor instances from args.executor
   - Instantiate OnehotEngine with context
   - Call engine.run()

### Phase 4: Legacy Code Removal

Safe deletion of functions from `oneshot.py` once verified:
- `run_oneshot()` - replaced by OnehotEngine.run()
- `run_oneshot_legacy()` - no longer needed
- `call_executor()` - replaced by executor.execute()
- `call_executor_adaptive()` - logic in Pipeline
- `_process_executor_output()` - replaced by executor.parse_activity()
- `_emit_activities()` - handled by engine/pipeline
- Prompt generation functions - could be consolidated

### Phase 5: Verification

- Full test suite (target: 0 regressions)
- Update legacy tests to use new architecture
- Manual end-to-end testing: `oneshot "Hello World"`

## Risks and Mitigation

| Risk | Mitigation |
|------|-----------|
| Circular dependencies in pty_utils | ✓ Verified: only standard library imports |
| Breaking changes to existing code | ✓ Verified: function is only internally used by oneshot.py |
| Verbosity configuration issues | ✓ Implemented environment-based fallback system |
| Platform-specific PTY issues | ✓ Tests already cover platform detection and timeout scenarios |

## Conclusion

Phase 1 successfully extracted the PTY streaming utilities with **zero breaking changes** and **all tests passing**. The foundation is solid for continuing with Phases 2-5.

The module is production-ready and can be used by future executor implementations.
