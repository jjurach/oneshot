# Project Implementation Status & Roadmap

**Project**: Codebase Cleanup and Consolidation
**Plan Document**: `dev_notes/project_plans/2026-01-21_codebase_cleanup_and_consolidation.md`
**Status**: IN PROGRESS
**Date**: 2026-01-21

## Executive Summary

The codebase cleanup project has successfully completed foundational analysis and preparation work. Two critical milestones have been achieved:

1. ✅ **Phase 1 Complete**: Extracted PTY streaming utilities to `pty_utils.py`
2. ✅ **Phase 2 Complete**: Verified engine parity and identified gaps

Current test suite status: **478 passed, 5 skipped, 0 failures** ✅

## Implementation Status by Phase

### Phase 1: Consolidate Streaming Infrastructure ✅ COMPLETE

**Objective**: Extract robust PTY streaming from legacy monolith

**Deliverables**:
- ✅ Created `src/oneshot/providers/pty_utils.py` (280 lines)
  - Extracted `call_executor_pty()` with all 205 lines of PTY logic
  - Added environment-based logging (no circular dependencies)
  - Full platform detection and timeout handling
- ✅ Verified no circular dependencies
- ✅ All tests passing (4/4 PTY streaming tests, 478 total)

**Documentation**: `dev_notes/changes/2026-01-21_phase1_pty_extraction.md`

**Key Achievement**: Foundation for executor improvements without breaking changes

---

### Phase 2: Verify Engine Parity ✅ COMPLETE

**Objective**: Audit feature parity between legacy `run_oneshot()` and `OnehotEngine`

**Deliverables**:
- ✅ Comprehensive feature comparison (9 categories)
- ✅ Identified critical gaps (5 items)
- ✅ Identified important gaps (5 items)
- ✅ Engine test verification (29/29 tests passing)
- ✅ Zero regressions confirmed

**Key Finding**: Engine has ~65% parity, suitable for internal use but needs enhancements for production

**Documentation**: `dev_notes/changes/2026-01-21_phase2_engine_parity_analysis.md`

---

### Phase 2.5: Restore Critical Missing Features 🔴 PENDING

**Critical Gaps** (must fix before Phase 3):

1. **Custom Prompt Headers** (Low complexity)
   - Status: Engine doesn't accept `worker_prompt_header`, `auditor_prompt_header`, `reworker_prompt_header`
   - Fix: Add to OnehotEngine `__init__()` signature
   - Estimate: 30 minutes

2. **Reworker Prompt Distinction** (Medium complexity)
   - Status: Engine treats all iterations identically
   - Fix: Update `_generate_worker_prompt()` to use different header for iteration 2+
   - Estimate: 1 hour

3. **Markdown Session Logging** (Medium complexity)
   - Status: Engine only supports JSON
   - Fix: Add conditional markdown logging to ExecutionContext
   - Estimate: 1-2 hours

4. **Keep-Log Flag** (Low complexity)
   - Status: No parameter to control auto-cleanup
   - Fix: Add `keep_log` parameter, skip cleanup on success if True
   - Estimate: 30 minutes

5. **Comprehensive Metadata Schema** (Medium complexity)
   - Status: Engine logs minimal metadata
   - Fix: Add metadata dict to ExecutionContext with timestamp, providers, models, cwd
   - Estimate: 1 hour

**Total Estimate**: 4-5 hours
**Complexity**: LOW to MEDIUM
**Risk**: VERY LOW (isolated to engine, no public API changes)

---

### Phase 3: Refactor CLI Entry Point 🟡 PENDING

**Objective**: Replace `main()` dispatch from `run_oneshot_legacy()` to `OnehotEngine`

**Estimated Work**:

1. **Create Session Management Utilities** (1-2 hours)
   - Create `src/oneshot/cli/session_utils.py`
   - Migrate `find_latest_session()`, `read_session_context()`, `count_iterations()`
   - Add session file validation and resume logic

2. **Refactor main()** (1-2 hours)
   - Parse ExecutionContext from CLI args
   - Create executor instances from `--executor` flag
   - Instantiate OnehotEngine with context
   - Call `engine.run()` instead of `run_oneshot_legacy()`

3. **Add Executor Registry** (optional, 30-60 min)
   - Create factory method: `executor = create_executor(args.executor, args.worker_model)`
   - Simplify main() logic

**Total Estimate**: 2.5-4 hours
**Complexity**: MEDIUM
**Risk**: MEDIUM (CLI is user-facing, needs careful testing)

**Blockers**: Phase 2.5 must complete first (engine needs all features)

---

### Phase 4: Delete Legacy Code 🟡 PENDING

**Objective**: Remove dead code from `oneshot.py` after engine migration

**Functions to Delete** (after Phase 3 verification):
1. `run_oneshot()` - 365 lines (replaced by engine)
2. `run_oneshot_legacy()` - 68 lines (wrapper, no longer needed)
3. `run_oneshot_async()` - 225 lines (async variant, in new pipeline)
4. `run_oneshot_async_legacy()` - 49 lines (async legacy wrapper)
5. `call_executor()` - 83 lines (executor.execute() replaces)
6. `call_executor_async()` - 72 lines (executor async methods)
7. `call_executor_adaptive()` - 116 lines (adaptive timeout, in pipeline)
8. `_process_executor_output()` - 144 lines (executor.parse_activity() replaces)
9. `_emit_activities()` - 17 lines (pipeline handles)
10. Prompt generation helpers - 140 lines total (can be consolidated or removed)

**Utility Functions to Delete or Migrate**:
- `log_info()`, `log_verbose()`, `log_debug()`, `dump_buffer()` - replace with centralized logging
- `get_worker_prompt()`, `get_auditor_prompt()`, `get_reworker_prompt()` - move to `prompts.py`
- `parse_streaming_json()`, `extract_json()`, `extract_lenient_json()` - move to `utils/json_parsing.py`
- `parse_lenient_verdict()`, `parse_json_verdict()` - move to `utils/verdict_parsing.py`
- `split_json_stream()`, `extract_activity_text()` - move to activity module
- `find_latest_session()`, `read_session_context()`, `count_iterations()` - moved to `cli/session_utils.py`
- `strip_ansi()` - move to string utils

**Safe to Delete Immediately**:
- `_check_test_mode_blocking()` - test infrastructure only
- `get_cline_task_dir()`, `monitor_task_activity()` - Cline-specific, not used
- `contains_completion_indicators()` - unused helper
- `select_activities_for_auditor()` - replaced by ResultExtractor

**Estimated Reduction**: ~1500 lines from `oneshot.py` (2337 → ~800)

**Total Estimate**: 2-3 hours
**Complexity**: LOW to MEDIUM
**Risk**: MEDIUM (must ensure all functions moved/replaced)

**Blockers**: Phase 3 must complete first (verify everything works with engine)

---

### Phase 5: Comprehensive Testing & Validation 🟡 PENDING

**Objective**: Verify all changes work end-to-end with no regressions

**Test Strategy**:

1. **Run Full Test Suite** (15-30 min)
   ```bash
   pytest tests/ -v --tb=short
   Target: 490+ tests passing, 0 failures
   ```

2. **Legacy Test Migration** (1-2 hours)
   - Update tests that used `call_executor()` to use `executor.execute()`
   - Update tests that used `run_oneshot()` to use `OnehotEngine`
   - Archive or delete tests for removed functions

3. **Manual End-to-End Tests** (1-2 hours)
   ```bash
   # Test basic execution
   oneshot "Write a simple hello.py"

   # Test resume
   oneshot --resume

   # Test with custom headers
   oneshot --worker-prompt-header "my project" "Task"

   # Test different executors
   oneshot --executor claude "Task"
   oneshot --executor gemini "Task"

   # Test markdown logging (Phase 2.5)
   oneshot --session-log my_session.md "Task"

   # Test session cleanup (Phase 2.5)
   oneshot "Task"  # Check logs deleted on success
   oneshot --keep-log "Task"  # Check logs preserved
   ```

4. **Regression Verification** (30-60 min)
   - Activity logging format unchanged
   - Session file structure valid JSON
   - Provider interfaces unchanged
   - All executors still work

5. **Performance Validation** (optional, 30-60 min)
   - Ensure streaming performance unchanged
   - Check memory usage vs legacy
   - Benchmark typical execution

**Total Estimate**: 3-5 hours
**Complexity**: MEDIUM
**Risk**: LOW (testing should find issues before production)

---

## Overall Project Timeline

### Optimistic Path (All work by one developer)
- Phase 1: ✅ DONE (2 hours)
- Phase 2: ✅ DONE (3 hours)
- Phase 2.5: 4-5 hours
- Phase 3: 2.5-4 hours
- Phase 4: 2-3 hours
- Phase 5: 3-5 hours
- **Total: ~20-24 hours** (2.5-3 days of focused work)

### Conservative Path (Parallel work possible)
- Phases 1-2: ✅ DONE
- Phases 2.5 + 3: Can run in parallel (5-6 hours each)
- Phase 4: 2-3 hours (sequential, depends on Phase 3)
- Phase 5: 3-5 hours (sequential, depends on Phase 4)
- **Total: ~18-20 hours** (better parallelism)

## Critical Dependencies

```
Phase 1 (PTY extraction) ✅
    ↓
Phase 2 (Engine parity analysis) ✅
    ↓
Phase 2.5 (Restore features) 🔴 REQUIRED
    ↓
Phase 3 (Refactor CLI) → Phase 4 (Delete code) → Phase 5 (Test)
```

**Key Constraint**: Phase 2.5 must complete before Phase 3 (engine must have all features)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Breaking existing CLI | Medium | High | Comprehensive testing before deletion |
| Feature regression | Medium | High | Test coverage for all features |
| Circular imports | Low | High | Code review, import analysis |
| Performance degradation | Low | Medium | Benchmarking Phase 5 |
| Executor incompatibilities | Low | Medium | Test each executor type |
| Session file corruption | Low | High | Backup strategy, validation |

**Overall Risk Level**: MEDIUM (manageable with careful execution and testing)

## Success Criteria

- [ ] Phase 1: ✅ Complete (PTY extraction done)
- [ ] Phase 2: ✅ Complete (Parity analysis done)
- [ ] Phase 2.5: All 5 missing features restored
  - [ ] Custom prompt headers working
  - [ ] Reworker prompts distinct from worker
  - [ ] Markdown session logging functional
  - [ ] Keep-log flag controlling cleanup
  - [ ] Metadata schema populated
- [ ] Phase 3: CLI refactored to use engine
  - [ ] `main()` calls `OnehotEngine` not `run_oneshot_legacy()`
  - [ ] Session management utilities created
  - [ ] All CLI flags still work
- [ ] Phase 4: Legacy code removed
  - [ ] 1500+ lines deleted from `oneshot.py`
  - [ ] All functions either deleted or migrated
  - [ ] No broken imports anywhere
- [ ] Phase 5: Comprehensive testing
  - [ ] 490+ tests passing, 0 failures
  - [ ] All manual tests pass
  - [ ] No regressions found

## Blockers & Open Questions

### Currently Blocking

1. **Phase 2.5 Features**: Waiting for implementation before Phase 3 can proceed
2. **CLI Testing Strategy**: Need comprehensive test cases for all CLI combinations

### Open Questions

1. Should `run_oneshot_legacy()` be kept for backward compatibility?
   - Recommendation: Remove it (only used by main())

2. Should prompt generation functions be consolidated?
   - Recommendation: Move to `src/oneshot/prompts.py` with metadata

3. How to handle verbosity configuration?
   - Recommendation: Use environment variables + parameter in OnehotEngine

4. Should we add UI callback integration earlier?
   - Recommendation: Yes, during Phase 2.5 (important for progress indicators)

## Recommendations for Next Developer

1. **Start with Phase 2.5**: All 5 features are quick wins (4-5 hours total)
2. **Test frequently**: After each feature, run full test suite
3. **Document changes**: Keep change documentation updated for each phase
4. **Review carefully**: Code review for Phase 3-4 (CLI changes are high-risk)
5. **Use git commits**: Commit after each phase for easy rollback

## Conclusion

The codebase cleanup project has successfully established a solid foundation with:
- ✅ PTY utilities extracted (no breaking changes)
- ✅ Engine parity thoroughly analyzed (65% complete)
- 🔴 Clear roadmap for remaining work (20-24 hours estimated)

The new engine architecture represents a significant improvement over the legacy monolithic approach. Once Phase 2.5 features are restored, the engine will be production-ready for full migration.

**Recommendation**: Proceed with Phase 2.5 implementation while this analysis is fresh. The identified 5 features are all relatively straightforward and can be completed in parallel.
