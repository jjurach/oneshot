# Project Plan: Raw NDJSON Activity Stream Logging

## Objective

Create diagnostic `*-log.json` files containing pure NDJSON streams of raw executor activity data for system improvement and debugging. Log files will be used alongside oneshot output to diagnose issues and improve executor-specific activity JSON parsing. Only pure NDJSON data goes into log files - corrupt/incomplete data that cannot form valid JSON is discarded with warning messages.

## Key Requirements

- **Pure NDJSON Only:** Log files contain only valid JSON lines - no metadata, timestamps, or wrapper objects
- **Data Integrity:** Corrupt/incomplete data that cannot form valid JSON is discarded with warning messages
- **Diagnostic Purpose:** Raw logs will be analyzed with session output to improve activity parsing
- **Future Use:** Historical logs will enhance executor-specific JSON pattern recognition

## Implementation Steps

### Phase 1: NDJSON Logger Utility
**Goal:** Create utility for pure NDJSON logging with strict validation

1. **Create NDJSON logger class** (`src/oneshot/providers/activity_logger.py`)
   - `ActivityLogger` class for pure NDJSON streaming
   - Methods: `log_json_line()`, `validate_and_write()`, `finalize_log()`
   - Strict JSON validation - discard malformed data with warnings
   - No buffering or reconstruction of incomplete JSON

2. **Implement validation and error handling**
   - Validate each JSON object using `json.loads()` before writing
   - Log warnings for discarded corrupt data: `WARNING: Discarded malformed JSON: {partial_data}`
   - Return success/failure status for each logging attempt
   - Error messages help identify parsing issues for future improvement

3. **File management utilities**
   - Generate log file path: `{session_file_base}-log.json`
   - Lazy initialization (create file on first valid activity)
   - Automatic cleanup of empty log files
   - Proper file flushing and closing

### Phase 2: Integration into Activity Pipeline
**Goal:** Hook logger into executor activity processing

1. **Integrate into activity interpreter** (`src/oneshot/providers/activity_interpreter.py`)
   - Modify `interpret_activity()` to accept logger parameter
   - Pass raw JSON activities to logger before interpretation
   - Log warnings when JSON validation fails

2. **Connect to executor output processing** (`src/oneshot/oneshot.py`)
   - Create `ActivityLogger` instance in session initialization
   - Pass logger to `_process_executor_output()` calls
   - Log file created when first valid activity detected

3. **Session lifecycle management**
   - Initialize logger when session starts
   - Flush log on session completion or interruption
   - Clean up empty log files if no valid activities recorded

## Success Criteria

✅ **Data Purity:**
- Log files contain only valid NDJSON lines (one JSON object per line)
- No metadata, timestamps, or wrapper objects in log files
- Compatible with `jq`, standard NDJSON tools, and log analysis scripts

✅ **Error Handling:**
- Corrupt data discarded with informative warning messages
- No attempts to fix or reconstruct incomplete JSON
- Warning messages logged to stderr for debugging

✅ **File Management:**
- Log files created beside session files: `session.json` → `session-log.json`
- Lazy initialization prevents empty files
- Automatic cleanup of unused log files

✅ **Diagnostic Value:**
- Raw NDJSON streams provide clean data for analysis
- Warning messages help identify parsing failure points
- Files correlate directly with session output for debugging

## Testing Strategy

### Unit Tests (`tests/test_activity_logger.py`)
1. **JSON Validation Tests**
   - Test valid JSON objects are written correctly
   - Test malformed JSON is discarded with warnings
   - Test partial/incomplete JSON handling
   - Test file creation and cleanup

2. **Integration Tests**
   - Test logger integration with activity interpreter
   - Verify NDJSON format purity
   - Test session lifecycle (create, flush, cleanup)
   - Test with real executor output samples

### Manual Tests
1. **Diagnostic Usage Testing**
   - Run oneshot with logging enabled
   - Verify log files contain pure NDJSON
   - Correlate log data with session output
   - Test log analysis with `jq` and other tools

2. **Error Scenario Testing**
   - Test with intentionally corrupt executor output
   - Verify warning messages appear
   - Confirm corrupt data not written to logs
   - Test edge cases (empty output, malformed streams)

## Usage for System Improvement

### Current Session Analysis
- **Correlation:** Compare NDJSON logs with oneshot terminal output
- **Debugging:** Identify where activity extraction succeeds/fails
- **Pattern Recognition:** Study raw JSON structures from different executors

### Historical Log Analysis
- **Parser Improvement:** Use old logs to refine executor-specific patterns
- **Algorithm Training:** Provide clean datasets for activity recognition
- **Regression Testing:** Verify parsing improvements don't break existing patterns

### Development Workflow
```bash
# Run oneshot and capture both session and activity logs
oneshot "complex task" --session-log my_session.md

# Analyze the logs together
cat my_session-log.json | jq '.activity'  # Extract activity types
# Compare with session markdown content
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Data loss from strict validation | Low | Medium | Acceptable for diagnostic logs - warnings provide feedback |
| Log files grow too large | Medium | Low | Lazy initialization, manual cleanup if needed |
| JSON validation performance impact | Low | Low | Minimal overhead, only validates before writing |
| File system permission issues | Low | Low | Graceful fallback if log file cannot be created |

## Implementation Order

1. **Create logger utility** (Phase 1) - Core functionality
2. **Add comprehensive tests** - Verify validation and error handling
3. **Integrate into pipeline** (Phase 2) - Connect to existing activity processing
4. **Manual testing** - Verify diagnostic value and file management

## Files to Create
- `src/oneshot/providers/activity_logger.py` - Pure NDJSON logging utility
- `tests/test_activity_logger.py` - Validation and error handling tests

## Files to Modify
- `src/oneshot/oneshot.py` - Integrate logger into activity processing pipeline
- `src/oneshot/providers/activity_interpreter.py` - Add logger parameter to interpretation methods

## Dependencies & Constraints

- **Existing Infrastructure:** Uses existing activity extraction pipeline
- **No New Dependencies:** Pure Python JSON handling
- **File System Access:** Requires write permissions in session directory

## Effort Estimate

- **Logger Utility:** Small (JSON validation, file management)
- **Pipeline Integration:** Small (pass logger parameter through existing code)
- **Testing:** Medium (comprehensive validation and error scenario testing)
- **Total Scope:** Small feature focused on diagnostics

## Deliverables

1. ✅ Working NDJSON logger with strict validation
2. ✅ Integration into activity processing pipeline
3. ✅ Pure NDJSON log files beside session files
4. ✅ Warning messages for corrupt data
5. ✅ Comprehensive test suite
6. ✅ Documentation for diagnostic usage

## Next Steps After Approval

1. Implement Phase 1 (logger utility)
2. Add unit tests and verify validation
3. Implement Phase 2 (pipeline integration)
4. Manual testing with real sessions
5. Update documentation