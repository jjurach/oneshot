# Project Plan: Codebase Cleanup and Consolidation

**Date:** 2026-01-21
**Status:** Draft

## Objective
Remove dead code, consolidate redundant implementations, and finalize the transition to the new modular architecture (Phases 1-5).

## Context
The codebase currently contains two parallel implementations of the core orchestration logic:
1.  **Legacy:** `src/oneshot/oneshot.py` (Monolithic, procedural, contains robust PTY streaming).
2.  **New:** `src/oneshot/engine.py` (Modular, class-based, "Phase 5 Orchestrator") + `src/oneshot/providers/*` (Executors).

The goal is to retire the legacy implementation while preserving its robust PTY streaming capabilities by migrating them to the new architecture.

## Tasks

### Phase 1: Consolidate Streaming Infrastructure
- [ ] **Extract PTY Utility**:
    - Create `src/oneshot/providers/pty_utils.py`.
    - Move `call_executor_pty` and `call_executor_adaptive` logic from `src/oneshot/oneshot.py` to this new module.
    - Ensure `pty_utils.py` has no circular dependencies.
- [ ] **Update Executors**:
    - Refactor `ClineExecutor`, `ClaudeExecutor`, `GeminiCLIExecutor`, `DirectExecutor` to use `pty_utils.call_executor_pty` in their `execute` methods.
    - Remove the redundant/inferior `subprocess.Popen` implementations in these classes.
    - Ensure `_stream_output` methods are updated or removed as needed.

### Phase 2: Verify New Engine Parity
- [ ] **Audit `OnehotEngine`**:
    - Compare `src/oneshot/engine.py` logic with `src/oneshot/oneshot.py` `run_oneshot` function.
    - Ensure features like "resume session", "markdown logging", "activity intervals", and "auditor feedback loop" are fully supported in `OnehotEngine` (or `StateMachine`/`Pipeline`).
    - Note: `oneshot.py` handles "Resume" by reading files. `OnehotEngine` accepts `context`. The CLI entry point should handle the file reading and pass the `context` to the `Engine`.

### Phase 3: Switch Entry Point
- [ ] **Refactor `src/oneshot/oneshot.py`**:
    - Keep `main()` and argument parsing.
    - Replace calls to `run_oneshot_legacy` and `run_oneshot` with `OnehotEngine` instantiation and execution.
    - Ensure CLI flags correctly map to `OnehotEngine` configuration.
    - Move "Resume" logic (finding/loading session files) to `main()` or a helper in `src/oneshot/cli/session_utils.py`.

### Phase 4: Dead Code Removal
- [ ] **Remove Legacy Functions**:
    - Delete `run_oneshot`, `run_oneshot_legacy`, `run_oneshot_async`, `run_oneshot_async_legacy` from `src/oneshot/oneshot.py`.
    - Delete `call_executor`, `call_executor_async`, `call_executor_adaptive`, `call_executor_pty` from `src/oneshot/oneshot.py` (after verifying migration).
    - Delete `_process_executor_output` and `_emit_activities` from `oneshot.py` (ensure logic is covered by `Pipeline` and `Executor`).
- [ ] **Cleanup Imports**:
    - Remove unused imports in `src/oneshot/oneshot.py`.

### Phase 5: Verification
- [ ] **Run Tests**:
    - Run existing tests to ensure no regression.
    - Run `tests/test_oneshot.py` likely tests the legacy functions. These tests need to be updated to test `OnehotEngine` or the new CLI entry point.
- [ ] **Test Cleanup**:
    - Identify tests targeting legacy functions (`test_executor.py` targets `call_executor`).
    - Migrate valid test cases to `test_executor_framework.py` or `test_engine.py`.
    - Delete or archive legacy tests.
- [ ] **Manual Test**:
    - Run `oneshot "Hello World"` to verify end-to-end functionality.

## Timeline
- **Start:** Immediate
- **Completion:** TBD

## Resources
- `src/oneshot/engine.py`: Target Orchestrator
- `src/oneshot/providers/base.py`: Target Executor Interface
- `src/oneshot/oneshot.py`: Legacy Source
