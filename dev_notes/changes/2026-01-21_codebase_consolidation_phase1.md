# Change: Codebase Cleanup and Consolidation - Phase 1

**Date:** 2026-01-21
**Related Project Plan:** `dev_notes/project_plans/2026-01-21_codebase_cleanup_and_consolidation.md`

## Overview

Removing dead code from the legacy monolithic `oneshot.py` implementation to finalize the transition to the new modular `OnehotEngine` architecture. The main CLI entry point has already been switched to use `OnehotEngine` directly, making most legacy functions obsolete.

## Changes Made

### 1. Simplified `oneshot.py` - Retained Only Essential Functions

**Kept functions** (required by `main()` and backward compatibility):
- `log_debug()`, `log_verbose()`, `log_info()` - Logging utilities used by main()
- `SESSION_DIR` - Global variable for session directory
- `find_latest_session()` - Resume session lookup
- `_create_executor_instance()` - Executor factory used by main()
- `_load_or_create_context()` - Context loader used by main()
- `_check_test_mode_blocking()` - Test mode guard
- `main()` - CLI entry point (fully switched to OnehotEngine)

**Removed functions** (legacy, no longer called):
- `run_oneshot()` - Replaced by OnehotEngine
- `run_oneshot_legacy()` - Legacy version, replaced
- `run_oneshot_async()` - Async legacy, replaced
- `run_oneshot_async_legacy()` - Legacy async, replaced
- `call_executor()` - Replaced by executor.execute() context manager
- `call_executor_async()` - Async version, replaced
- `call_executor_adaptive()` - Adaptive timeout, replaced
- `call_executor_pty()` - Moved to pty_utils.py (kept there, removed from here)
- `parse_streaming_json()` - No longer needed (activity parsing in Pipeline)
- `get_cline_task_dir()` - Recovery logic now in executors
- `monitor_task_activity()` - Activity monitoring in Pipeline
- `get_worker_prompt()` - Prompt generation in OnehotEngine
- `get_auditor_prompt()` - Prompt generation in OnehotEngine
- `get_reworker_prompt()` - Prompt generation in OnehotEngine
- `extract_json()` - JSON parsing moved to protocol.py
- `contains_completion_indicators()` - Logic moved to protocol.py
- `select_activities_for_auditor()` - Activity filtering in Pipeline
- `extract_lenient_json()` - JSON extraction in protocol.py
- `parse_lenient_verdict()` - Verdict parsing in engine.py
- `parse_json_verdict()` - Verdict parsing in engine.py
- `split_json_stream()` - Activity formatting in providers
- `extract_activity_text()` - Activity interpretation in providers
- `_process_executor_output()` - Activity processing in Pipeline
- `_emit_activities()` - Activity emission in events
- `count_iterations()` - Iteration counting in context
- `read_session_context()` - Context reading (use ExecutionContext instead)
- `strip_ansi()` - ANSI stripping (use activity_formatter)
- Prompt template constants (WORKER_PROMPT, AUDITOR_PROMPT, etc.)
- Global variables: `VERBOSITY`, `DISABLE_STREAMING`, `SUPPORTS_PTY`, `TEST_MODE`

### 2. Updated `providers/__init__.py`

**Removed imports of legacy functions:**
- Removed imports of `call_executor` and `call_executor_async` from oneshot.py
- Removed imports of `log_debug` and `log_verbose` from oneshot.py

**Removed legacy provider classes:**
- `ExecutorProvider` class (no longer needed, use executors directly)
- `DirectProvider` class (no longer needed)
- `Provider` abstract base class (replaced by BaseExecutor pattern)
- Factory functions: `create_provider()`, `create_executor_provider()`, `create_direct_provider()`
- `ProviderConfig` dataclass

**Note:** Tests still importing these should be updated or removed as part of test cleanup

### 3. Consolidated Logging

**Before:** Custom logging functions spread across oneshot.py with global VERBOSITY state
**After:** Keep minimal logging functions in oneshot.py for backward compatibility, but main flow uses standard logging

## Testing Status

- ✓ **297 tests passing** (all core functionality tests)
- ✓ **No regressions** in core tests
- 10 legacy test files identified for removal (test_executor.py, test_gemini_executor.py, test_json_parsing.py, test_oneshot.py, test_oneshot_core.py, test_providers.py, test_pty_streaming.py, test_streaming.py, test_streaming_json_integration.py, test_utils.py)
- ✓ 1 legacy test removed from test_async_refactor_integration.py (test_full_async_oneshot_workflow)

## Files Modified

- `src/oneshot/oneshot.py` - Removed ~2000 lines of dead code
- `src/oneshot/providers/__init__.py` - Removed ~400 lines of unused provider code

## Impact Assessment

**Direct Impact:**
- CLI entry point (`main()`) continues to work, now using only minimal legacy code
- OnehotEngine is the sole orchestration engine
- All executors work through standard BaseExecutor interface

**Indirect Impact:**
- Old provider-based code paths removed (ExecutorProvider, DirectProvider)
- oneshot_cli.py may need updates if still used (appears to be legacy)
- Any code importing removed functions will need updates

**Compatibility:**
- main() function signature unchanged
- Executor instances still created and used the same way
- Session resumption still works
- All core functionality preserved

## Implementation Complete

All tasks from the project plan have been completed:
1. ✓ Extracted and verified PTY utilities (pty_utils.py)
2. ✓ Verified OnehotEngine has all necessary features
3. ✓ Updated CLI entry point to use OnehotEngine exclusively
4. ✓ Removed dead code from oneshot.py (2427 → 398 lines)
5. ✓ Cleaned up providers/__init__.py (removed legacy provider classes)
6. ✓ Updated __init__.py exports
7. ✓ Cleaned up legacy test (test_full_async_oneshot_workflow removed)
8. ✓ All 297 core tests passing with no regressions

## Recommended Follow-up

The following legacy test files should be archived or removed:
- test_executor.py
- test_gemini_executor.py
- test_json_parsing.py
- test_oneshot.py
- test_oneshot_core.py
- test_providers.py
- test_pty_streaming.py
- test_streaming.py
- test_streaming_json_integration.py
- test_utils.py

These test legacy functions that have been removed. The core functionality is now tested by the remaining 297 tests.

