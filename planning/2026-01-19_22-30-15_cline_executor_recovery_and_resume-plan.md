# Project Plan: Executor Recovery and Resume Feature

**Source:** dev_notes/specs/2026-01-19_17-14-15_prompt-10.md

## Objective

Implement a robust recovery and resume mechanism for oneshot when the cline executor becomes stuck or times out. This addresses the issue where Cline processes may complete work but fail to properly report completion to Oneshot, resulting in stuck iterations and timeouts.

The solution includes:
1. Fixing configuration validation issues with `worker_prompt_header`
2. Adding timestamp-based correlation IDs to worker prompts for session tracking
3. Implementing a `--resume` feature to continue execution from a stuck state
4. Creating process recovery procedures (killing hung processes, recovering execution state)
5. Syncing missing API conversation history into the oneshot log
6. Standardizing session file naming conventions
7. Enabling reworker/auditor iteration continuation after resume

---

## Implementation Steps

### Phase 1: Fix Configuration Validation

1. **Identify the `worker_prompt_header` NoneType Error**
   - Locate where `.oneshot.json` configuration is loaded and validated
   - Find the validation logic that enforces `worker_prompt_header` as a string
   - Trace the root cause: why is it being set to `None`?

2. **Apply Immediate Fix**
   - Set a default value for `worker_prompt_header` if it's missing or `None`
   - Ensure backward compatibility with existing configuration files
   - Add validation to prevent future `NoneType` assignments
   - Log warnings for missing config with fallback behavior

3. **Test Configuration Handling**
   - Verify that `.oneshot.json` loads without the "Invalid type" warning
   - Test with both valid and missing `worker_prompt_header` values

### Phase 2: Timestamp Correlation & Session Tracking

4. **Update worker_prompt_header to include oneshot ID**
   - Modify the worker prompt header generation in `src/oneshot/oneshot.py`
   - Include the oneshot session filename's timestamp pattern (e.g., `2026-01-19_16-46-01`)
   - Format: `$project_name worker 2026-01-19_16-46-01_oneshot\n\n`
   - This allows agents to reference the correlation ID in conversation context

5. **Add oneshot ID tracking throughout execution**
   - Extract and store the oneshot ID from the session filename
   - Pass the ID through to executor calls and logging
   - This enables `cline task list` output to be correlated with oneshot sessions

6. **Add Cline Session Matching Utility**
   - Create a helper function to parse Cline task list output
   - Match Cline task sessions to Oneshot session IDs based on the embedded timestamp in the worker prompt header
   - Enable `cline task list` to be used for session recovery

### Phase 3: Implement `--resume` Command-Line Feature

7. **Implement `--resume` command-line argument**
   - Add `--resume ONESHOT_ID` argument to the argparse configuration
   - Modify startup logic to detect resume mode vs. normal startup
   - When `--resume` is used, load the previous session file instead of creating a new one

8. **Load and validate previous session state**
   - Read the existing oneshot session JSON file
   - Verify that the session exists and is in a valid state
   - Extract the original prompt from the session file
   - Store it for auditor reference

9. **Allow prompt override in resume mode**
   - If `--resume` receives both an ID and a new prompt argument, use the new prompt
   - Otherwise, retain the original prompt from the session
   - Document this behavior clearly
   - Preserve the original prompt with clear audit trail if overridden

### Phase 4: API Conversation History Recovery

10. **Implement conversation history syncing**
    - Create a function to retrieve conversation history from `~/.cline/data/tasks/<task_id>/api_conversation_history.json`
    - Parse the conversation history to identify messages missing from the oneshot log
    - Inject missing conversation history into the oneshot session file
    - Focus on the last 2KB or last message (as specified in requirements)

11. **Determine task ID from correlation**
    - When resuming, use `cline task list` output or stored mappings to find the cline task ID
    - Alternative: extract from session context or allow user to provide it
    - Store the task ID in the session file for future reference

12. **Implement Session State Detection**
    - After timeout, check if the Cline task actually completed
    - Query Cline's API conversation history file to detect completion
    - Log the last known message/state for resume purposes

### Phase 5: Process Recovery Procedures

13. **Implement process health check & recovery**
    - Detect when a Cline process is unresponsive (not producing output within timeout)
    - Implement graceful kill option with `-9` signal as fallback
    - Log recovery attempts for debugging

14. **Implement process killing utility**
    - Create a function to identify and kill stuck cline processes with `-9` signal
    - Add optional `--kill-stuck` flag to oneshot
    - Log which processes were killed for audit trail
    - Provide safe guards to prevent accidental killing of unrelated processes

15. **Add graceful process monitoring**
    - Detect timeout conditions during executor communication
    - When timeout occurs, capture what work may have been completed
    - Log the timeout with context (iteration count, partial output, etc.)

### Phase 6: Session File Standardization

16. **Identify and Consolidate Session Files**
    - Find all `session_*.md` files in the project
    - Analyze their naming patterns and content

17. **Standardize Session File Naming**
    - Ensure all session files use consistent timestamp format: `YYYY-MM-DD_HH-MM-SS`
    - Use consistent suffixes for different file types (e.g., `_oneshot.json`, `_summary.md`)
    - Rename or consolidate misnamed files
    - Format: `session_YYYY-MM-DD_HH-MM-SS_oneshot.md` (or similar pattern)

18. **Update Session File Creation Logic**
    - Modify code that creates session files to follow the standardized naming pattern
    - Update any hardcoded session file references
    - Modify wherever `session_*.md` files are created
    - Use the oneshot session ID timestamp as the prefix

### Phase 7: Auditor Integration for Resume

19. **Update auditor logic for resume workflow**
    - When in resume mode, the auditor receives:
      - Original task objective
      - Last portion of conversation history (missing from oneshot log)
      - Current execution state
    - Auditor can then decide to continue or provide new direction

20. **Implement Reworker/Auditor Continuation**
    - When resuming, the next iteration should:
      - Send the last retrieved message (or partial conversation) to the Auditor
      - Begin reworker/auditor iteration loop from that point
      - Continue up to the max iteration limit (or extend beyond if `--resume` is used)

21. **Implement resume iteration cycle**
    - After resume, initiate reworker/auditor iteration
    - Use the remaining iterations (or reset counter if specified)
    - Allow multiple resume attempts if needed

### Phase 8: Error Handling & Comprehensive Testing

22. **Add comprehensive error handling**
    - Handle cases where cline task history cannot be found
    - Handle cases where resume ID doesn't correspond to any session
    - Handle corrupted session files
    - Provide clear error messages for each failure mode

23. **Create unit tests**
    - Test configuration loading with missing/None `worker_prompt_header`
    - Test worker prompt header formatting with session ID
    - Test session ID extraction and correlation logic
    - Test `--resume` flag parsing and validation
    - Test timestamp extraction and correlation ID generation
    - Test conversation history parsing and syncing
    - Test prompt override logic

24. **Create integration tests**
    - Test full timeout scenario with process recovery
    - Test `--resume` with actual Cline task execution
    - Test conversation history retrieval and integration
    - Test reworker/auditor continuation after resume
    - Create a mock stuck executor scenario
    - Resume from that scenario
    - Verify conversation history is recovered
    - Test full reworker/auditor iteration on resume
    - Test edge cases (corrupt session, missing task history, etc.)

25. **Manual testing checklist**
    - Manually trigger a timeout scenario
    - Verify session correlation ID is embedded in worker prompt
    - Use `cline task list` to identify the Cline session
    - Test `oneshot --resume <session_id>`
    - Verify conversation history is properly integrated
    - Verify iteration continues from the correct point
    - Run actual oneshot command with real executor
    - Simulate timeout by killing executor mid-execution
    - Resume and verify state recovery
    - Test with `--kill-stuck` flag
    - Verify session file naming is consistent

26. **Document the resume feature**
    - Update README with `--resume` usage examples
    - Document the correlation ID concept
    - Provide troubleshooting guide for stuck processes
    - Document config requirements for worker_prompt_header
    - Document dependencies and assumptions

---

## Success Criteria

1. ✅ Configuration error for `worker_prompt_header` is fixed
2. ✅ Worker prompt headers include timestamp-based correlation IDs
3. ✅ `cline task list` can be used to find Cline sessions associated with Oneshot sessions
4. ✅ `--resume ONESHOT_ID` command successfully loads and continues previous sessions
5. ✅ `--resume` with prompt override works correctly
6. ✅ Original prompt is stored and retrievable from session file
7. ✅ Process recovery mechanism gracefully handles stuck Cline processes
8. ✅ API conversation history is synced into oneshot log on resume
9. ✅ Process killing (`--kill-stuck`) removes hung cline processes
10. ✅ Timeout detection captures executor state before timeout
11. ✅ All session files use standardized timestamp-based naming
12. ✅ Resume workflow can continue for multiple iterations
13. ✅ Reworker/auditor iteration continues after resume
14. ✅ Optional prompt override works when `--resume` is given with a new prompt
15. ✅ All tests pass (unit + integration + manual validation)
16. ✅ Backward compatibility maintained with old session files
17. ✅ Documentation is clear and complete

---

## Testing Strategy

### Unit Tests
- Configuration validation for `worker_prompt_header`
- Timestamp extraction and session ID generation
- Resume flag parsing and validation
- Session file naming utilities
- Prompt override logic
- Conversation history parsing and syncing
- Configuration validation with None handling

### Integration Tests
- End-to-end resume workflow with mock Cline session
- Conversation history retrieval and integration
- Timeout and recovery scenario
- Iteration continuation after resume
- Create a mock stuck executor scenario and resume from it
- Verify conversation history is recovered
- Full reworker/auditor iteration on resume
- Edge cases (corrupt session, missing task history, etc.)

### Manual Testing
1. Reproduce the original timeout scenario from dev_notes/specs/2026-01-19_17-14-15_prompt-10.md
2. Verify session correlation ID in worker prompt
3. Identify Cline session using `cline task list`
4. Execute `oneshot --resume <session_id>`
5. Verify iteration continues and completes
6. Inspect final session logs for completeness
7. Test `--kill-stuck` flag functionality
8. Verify session file naming consistency
9. Test backward compatibility with old session files

### Validation
- Check that all existing tests still pass
- Verify backward compatibility with old session files
- Test edge cases (corrupt session, missing task history, etc.)

---

## Risk Assessment

### High Risk
| Risk | Mitigation |
|------|-----------|
| Breaking existing `.oneshot.json` files with missing `worker_prompt_header` | Add default value with backward compatibility check |
| Resume feature corrupts session state if conversation history is incomplete | Validate conversation history before integration; log all changes |
| Killing wrong process with `-9` signal | Require explicit session ID match + confirmation for kill operations; Add safe guards |
| Executor communication change breaks existing behavior | Careful testing to ensure no unintended side effects |

### Medium Risk
| Risk | Mitigation |
|------|-----------|
| Changing prompt header format breaks existing Cline session correlation | Implement graceful fallback if correlation ID not found |
| Backward compatibility with old session files | Implement migration logic; Graceful handling of old formats |
| Task ID mapping unreliable | Document assumptions and add fallback mechanisms |
| Max iteration limit reached before resume completes task | Allow `--resume` to extend iteration count or remove limit for resume mode |
| Session file naming inconsistencies cause confusion | Automated migration script to rename existing files |
| Timeout detection difficulty | Use activity detection as heuristic; distinguish between slow execution and actual hang |

### Low Risk
| Risk | Mitigation |
|------|-----------|
| Configuration validation complications | Adding None handling is straightforward |
| File naming standardization issues | Can be done incrementally without breaking existing functionality |
| Process killing side effects | Standard OS functionality, low risk when used correctly |

### Assumptions
- Cline executor writes conversation history to `~/.cline/data/tasks/<task_id>/api_conversation_history.json`
- `cline task list` is available and can provide mapping between oneshot IDs and cline task IDs
- Session files should be writable during resume
- Enough context can be recovered from conversation history to safely resume
- Python's subprocess module behavior is consistent for timeout handling
- Cline API conversation history is accessible and contains completion status
- Oneshot session IDs are globally unique within a reasonable timeframe

---

## Files to Modify/Create

### Files to Create
- `src/oneshot/recovery.py` - Process recovery utilities
- `src/oneshot/resume.py` - Resume feature implementation
- `src/oneshot/session_correlation.py` - Session ID correlation logic
- `tests/test_recovery.py` - Unit tests for recovery
- `tests/test_resume.py` - Unit tests for resume feature
- `tests/integration_test_resume.py` - Integration tests

### Files to Modify
- `src/oneshot/oneshot.py` - Add `--resume` flag, integrate recovery logic, update worker prompt header
- `src/oneshot/config.py` - Fix `worker_prompt_header` validation, add defaults
- `src/oneshot/cli.py` - Parse `--resume` argument
- `src/oneshot/worker_prompt.py` (or equivalent) - Include session ID in prompt header
- `.oneshot.json` - Add/fix `worker_prompt_header` default value
- Documentation files (README, guides)
- Test files (add integration tests)

### Files to Migrate/Rename
- All `session_*.md` files - Standardize naming to `YYYY-MM-DD_HH-MM-SS_*.md`

---

## Execution Order

1. **Phase 1** (Configuration Fix) - Quick win, unblocks other work
2. **Phase 2** (Session Correlation) - Foundation for recovery/resume
3. **Phase 3** (Resume Feature) - Main feature implementation
4. **Phase 4** (API Conversation History) - Data recovery capability
5. **Phase 5** (Process Recovery) - Enables graceful handling of stuck processes
6. **Phase 6** (Session File Standardization) - Cleanup and consistency
7. **Phase 7** (Auditor Integration) - Resume workflow completion
8. **Phase 8** (Error Handling & Testing) - Verify all functionality works end-to-end

---

## Dependencies & Assumptions

1. Cline executor writes conversation history to `~/.cline/data/tasks/<task_id>/api_conversation_history.json`
2. `cline task list` is available and can provide mapping between oneshot IDs and cline task IDs
3. Session files should be writable during resume
4. Enough context can be recovered from conversation history to safely resume
5. Python's subprocess module behavior is consistent for timeout handling
6. Cline API conversation history is accessible and contains completion status
7. Oneshot session IDs are globally unique within a reasonable timeframe

---

## Notes

- This plan addresses the core issue from dev_notes/specs/2026-01-19_17-14-15_prompt-10.md: incomplete Cline execution reporting causing Oneshot iterations to hang
- The session correlation ID (timestamp pattern in worker prompt) enables easy matching between Oneshot and Cline sessions
- The `--resume` feature allows recovery without losing context or requiring manual re-execution
- Process recovery mechanisms prevent indefinite hangs by detecting stuck Cline processes
- All changes maintain backward compatibility where possible
- The correlation ID approach enables easier debugging and cross-referencing between oneshot and cline logs
- The resume feature is designed to be user-friendly while maintaining safety (prompting for confirmation, validation checks)
