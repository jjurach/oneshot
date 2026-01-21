# Change: CLI Refactor to Use OnehotEngine (Phase 3)

**Date:** 2026-01-21
**Related Project Plan:** `dev_notes/project_plans/2026-01-21_codebase_cleanup_and_consolidation.md`
**Status:** In Progress

## Overview

This change implements Phase 3 of the codebase cleanup: refactoring the CLI entry point (`main()` in `oneshot.py`) to use the new `OnehotEngine` instead of the legacy `run_oneshot_legacy()` function.

**Key Changes:**
1. Move session file discovery/loading logic from `run_oneshot_legacy()` to CLI layer
2. Create executor instances using the new provider infrastructure
3. Instantiate `OnehotEngine` with loaded context and executors
4. Update `main()` to call `engine.run()` instead of `run_oneshot_legacy()`

## Files Modified

### `src/oneshot/oneshot.py`
- **Modified main() function:**
  - Add logic to find/load session files for resume functionality
  - Create executor instances (worker and auditor)
  - Instantiate `OnehotEngine` with:
    - Executor instances
    - Execution context (loaded from file if resuming, new if starting)
    - Max iterations
    - Inactivity timeout
    - Prompt headers (passed to engine for prompt generation)
  - Call `engine.run()` to execute the task
  - Return success/failure status

- **New helper function: `_create_executor_instance(executor_type: str, model: Optional[str]) -> BaseExecutor`**
  - Creates appropriate executor (claude, cline, gemini, aider, direct)
  - Handles model selection

- **New helper function: `_load_or_create_context(resume: bool, session_file: Optional[Path], task_prompt: str) -> ExecutionContext`**
  - Loads existing context from file if resuming
  - Creates new context if starting fresh

## Implementation Strategy

### Step 1: Create Executor Factory
Create a helper function to instantiate the correct executor based on type and model.

### Step 2: Load/Create Context
Implement context loading for resume functionality:
- If resume=True and session_file provided, load from that file
- If resume=True without session_file, find latest session
- Otherwise create new context

### Step 3: Refactor main()
Update main() to:
1. Parse arguments (already done)
2. Create executors (worker and auditor)
3. Load/create context
4. Instantiate OnehotEngine with context, executors, and parameters
5. Call engine.run()
6. Return appropriate exit code

### Step 4: Verify Feature Parity
Ensure all features from legacy implementation are supported:
- [ ] Prompt headers (worker, auditor, reworker)
- [ ] Max iterations
- [ ] Inactivity timeout
- [ ] Session persistence
- [ ] Session logging
- [ ] Resume functionality

## Success Criteria

1. CLI entry point uses `OnehotEngine` instead of legacy functions
2. All existing CLI flags/options work as before
3. Resume functionality works correctly
4. Session logging works correctly
5. Existing tests pass (no regressions)
6. Manual testing confirms end-to-end functionality

## Testing Strategy

1. Unit tests for new helper functions
2. Integration tests for CLI with various argument combinations
3. Manual testing:
   - Basic execution: `oneshot "test prompt"`
   - Resume: `oneshot --resume`
   - Custom models: `oneshot --worker-model claude-3-5-sonnet-20241022 "test"`
   - Session logging: `oneshot --session-log test.md "test"`

## Risk Assessment

**Low Risk:**
- New code is isolated in helper functions
- Existing tests provide regression protection
- OnehotEngine is already proven (Phase 5 complete)
- Backward compatibility maintained through same CLI interface

**Mitigation:**
- Run full test suite before committing
- Manual end-to-end testing
- Use git diff to review all changes before commit

## Related Files

- `src/oneshot/engine.py` - OnehotEngine orchestrator
- `src/oneshot/context.py` - ExecutionContext
- `src/oneshot/providers/base.py` - BaseExecutor interface
- `src/oneshot/providers/*_executor.py` - Executor implementations
- `tests/test_engine.py` - Engine tests
- `tests/test_cli.py` - CLI tests

## Notes

- This refactor enables removal of legacy functions in Phase 4
- OnehotEngine already handles state machine, pipeline, and activity formatting
- Prompt generation in engine.py needs verification for header support
