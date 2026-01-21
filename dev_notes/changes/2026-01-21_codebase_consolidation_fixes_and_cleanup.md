# Change: Codebase Consolidation Fixes and CLI Refactoring

**Date:** 2026-01-21
**Related Project Plan:** `dev_notes/project_plans/2026-01-21_codebase_cleanup_and_consolidation.md`

## Overview

Applied critical fixes to the new `OnehotEngine` architecture and refactored the CLI entry point to fully utilize the unified provider system. These changes resolve bugs found in the initial consolidation and complete the migration from legacy code paths.

## Fixes and Improvements

### 1. ExecutionContext Improvements
- **Added `load()` Method**: Restored the missing `load()` classmethod in `ExecutionContext` required for session resumption.
- **Fixed Initialization**: Ensured `__init__` properly loads existing data from disk.
- **Task Persistence**: Fixed a bug in `oneshot.py` where the task prompt was not being saved to the context, causing the engine to use "Undefined task".
- **Unique IDs**: Ensured `oneshot_id` is generated and persisted for new sessions.

### 2. Engine Enhancements
- **Robust Value Retrieval**: Updated `OnehotEngine._get_context_value` to prefer direct data access over getter methods. This prevents issues with Mock objects in tests returning nested Mocks instead of fallback values.
- **Metadata Support**: Improved retrieval of values from `metadata` and `variables` sub-dictionaries in the context.
- **Session Logging**: Added `session_log_path` parameter to `OnehotEngine` to allow explicit control over where activity logs are stored.

### 3. CLI Refactoring (Phase 3 Complete)
- **Executor Registry**: Replaced manual executor instantiation in `oneshot.py` with the centralized `ExecutorRegistry`.
- **Session Utilities**: Migrated session-finding and reading logic to a new `src/oneshot/cli/session_utils.py` module for better separation of concerns.
- **Comprehensive Metadata**: Updated `main()` to populate the context with full execution metadata (providers, models, timeouts, etc.) before starting the engine.

## Verification Results

- **Unit Tests**: Ran full suite, **355 tests passed**, 2 skipped.
- **Bug Verification**: Confirmed that `ExecutionContext.load()` and task persistence work correctly.
- **Regression Check**: Verified that the new `_get_context_value` logic correctly handles both real ExecutionContext objects and Mock objects used in tests.

## Status
✅ **Consolidation Verified and Fixed**. The codebase is now stable, fully refactored, and all core features from the legacy implementation are successfully restored and tested in the new architecture.
