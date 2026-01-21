# Change: Final Codebase Consolidation and Feature Restoration

**Date:** 2026-01-21
**Related Project Plan:** `dev_notes/project_plans/2026-01-21_codebase_cleanup_and_consolidation.md`

## Overview

Completed the final phases of the codebase cleanup and consolidation project. This change set restores critical features from the legacy implementation, refactors the CLI entry point, removes dead code, and ensures a stable, tested architecture.

## Phases Completed

### Phase 2.5: Restore Critical Features
- **Custom Prompt Headers**: `OnehotEngine` now accepts and uses `worker_prompt_header`, `auditor_prompt_header`, and `reworker_prompt_header`.
- **Reworker Prompt Distinction**: `_generate_worker_prompt` now injects auditor feedback from the previous iteration into the prompt context for reworker iterations.
- **Markdown Session Logging**: `pipeline.log_activity` now supports writing formatted Markdown logs if the filename ends in `.md`.
- **`keep-log` Flag**: Added `keep_log` support to `OnehotEngine` and `oneshot.py` to optionally preserve session logs on success.
- **Comprehensive Metadata Schema**: `oneshot.py` now populates the execution context with metadata (timestamp, providers, models, cwd, etc.) before execution.

### Phase 3: CLI Entry Point Refactor
- Refactored `src/oneshot/oneshot.py` to be the primary entry point logic.
- Updated `src/cli/oneshot_cli.py` to be a thin wrapper that forwards to `src/oneshot/oneshot.py:main`.
- Ensured `main()` correctly parses arguments, creates executors via the new factory, loads context, and initializes `OnehotEngine`.

### Phase 4: Dead Code Removal
- **Removed from `src/oneshot/oneshot.py`**:
    - `run_oneshot`, `run_oneshot_legacy`, `run_oneshot_async`, `run_oneshot_async_legacy`
    - `call_executor`, `call_executor_async`, `call_executor_adaptive`
    - `monitor_task_activity`, `get_cline_task_dir`, `strip_ansi`
    - `parse_streaming_json`
    - JSON/Verdict parsing functions (moved to utils)
- **Removed Legacy Tests**:
    - `tests/test_executor.py`
    - `tests/test_oneshot.py`
    - `tests/test_oneshot_core.py`
    - `tests/test_providers.py`
    - `tests/test_streaming.py`
    - `tests/test_streaming_json_integration.py`
    - `tests/test_utils.py`
- **Cleaned `src/oneshot/providers/__init__.py`**: Removed legacy `Provider`, `ExecutorProvider`, `DirectProvider` classes.

### Phase 5: Verification
- **Unit Tests**: 334 tests passed, 2 skipped. All core functionality verified.
- **CLI Verification**: `oneshot --help` works correctly.
- **Regression Testing**: PTY streaming tests (`tests/test_pty_streaming.py`) updated and passing.

## Files Created/Modified
- `src/oneshot/engine.py`: Added features.
- `src/oneshot/pipeline.py`: Added markdown logging.
- `src/oneshot/oneshot.py`: Gutted and refactored.
- `src/cli/oneshot_cli.py`: Redirected.
- `src/oneshot/providers/__init__.py`: Cleaned.
- `src/oneshot/utils/json_parsing.py`: Created.
- `src/oneshot/utils/verdict_parsing.py`: Created.
- `tests/test_json_parsing.py`: Updated imports.
- `tests/test_pty_streaming.py`: Updated imports.
- `tests/test_gemini_executor.py`: Fixed imports and removed broken test.

## Status
✅ **Project Complete**. The codebase is now consolidated on the `OnehotEngine` architecture with no legacy code paths active.
