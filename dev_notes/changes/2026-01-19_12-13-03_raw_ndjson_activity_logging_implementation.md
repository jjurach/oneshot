# Change: Raw NDJSON Activity Stream Logging Implementation

## Related Project Plan
`dev_notes/project_plans/2026-01-19_11-29-00_raw_ndjson_activity_logging.md`

## Overview

Successfully implemented the Raw NDJSON Activity Stream Logging feature for the oneshot system. This diagnostic logging system creates pure NDJSON logs (`*-log.json` files) containing raw executor activity data alongside regular session output.

The implementation provides diagnostic value by:
- Creating pure NDJSON log files with one valid JSON object per line
- Discarding corrupt/incomplete JSON data with informative warning messages
- Supporting lazy file initialization (file created on first valid activity)
- Automatically cleaning up empty log files
- Integrating seamlessly into the existing activity processing pipeline

## Files Modified

### Phase 1: Logger Utility
**`src/oneshot/providers/activity_logger.py`** (Created - 115 lines)
- `ActivityLogger` class implementing pure NDJSON streaming
- Methods implemented:
  - `__init__()` - Initialize with session file base path
  - `log_json_line()` - Validate and log individual JSON lines
  - `_ensure_file_open()` - Lazy file initialization on first valid data
  - `finalize_log()` - Clean up resources and remove empty files
  - `__enter__()` / `__exit__()` - Context manager support

Key features:
- Strict JSON validation using `json.loads()` before writing
- Compact JSON formatting (no extra whitespace)
- Warning messages for discarded malformed data
- File handles managed with proper error handling
- Automatic directory creation if parent paths don't exist

### Phase 2: Integration into Activity Pipeline
**`src/oneshot/providers/activity_interpreter.py`** (Modified)
- Modified `interpret_activity()` method to accept optional `activity_logger` parameter
- Added raw JSON streaming to NDJSON log:
  - Lines from raw output parsed as JSON
  - Each valid JSON object logged via `activity_logger.log_json_line()`
  - Malformed lines skipped silently (warnings only if logger present)
- Integration is non-intrusive - logger parameter is optional

**`src/oneshot/oneshot.py`** (Already integrated)
- `ActivityLogger` imported and instantiated in session initialization
- Logger passed to activity processing functions
- Logger finalized on session completion or interruption
- Integration in place at:
  - Session initialization (line 1158)
  - Provider calls with logger parameter (lines 1173, 1233)
  - Session cleanup (lines 1332-1333)

### Testing
**`tests/test_activity_logger.py`** (Created - 252 lines)
12 comprehensive test cases covering:
1. **Initialization** - Verify logger state setup
2. **Lazy File Creation** - File only created on first valid data
3. **Valid JSON Logging** - Multiple valid JSON objects logged correctly
4. **Malformed JSON Handling** - Corrupt data discarded with warnings
5. **Valid After Malformed** - Logger recovers after bad data
6. **File Write Errors** - Graceful handling of I/O failures
7. **Empty File Cleanup** - Automatic removal of unused log files
8. **Context Manager** - Proper resource cleanup via `with` statement
9. **Context Manager Empty Cleanup** - Cleanup works with empty logs
10. **Directory Creation** - Parent directories created automatically
11. **JSON Formatting Consistency** - Compact JSON output format enforced
12. **Large JSON Warning Truncation** - Warning messages truncated for large payloads

All 12 tests pass ✅

**`tests/test_activity_interpreter.py`** (Existing tests all pass)
25 existing tests pass, including integration scenarios ✅

## Impact Assessment

### Functional Impact
- **New Capability**: Users can now generate diagnostic NDJSON logs alongside session output
- **Non-Breaking**: Optional logger parameter doesn't affect existing code
- **Pure NDJSON Output**: Log files contain only valid JSON - compatible with standard tools (`jq`, parsers, etc.)

### Performance Impact
- **Minimal Overhead**: JSON validation only occurs on write, minimal CPU impact
- **File System**: Lazy initialization prevents empty file creation
- **Memory**: No buffering, streaming write architecture

### File System Impact
- **Log File Location**: `{session_file_base}-log.json` placed beside session file
- **Size**: Depends on executor output volume, typically proportional to session length
- **Cleanup**: Empty logs automatically removed to prevent disk clutter

### Compatibility
- **Existing Code**: No breaking changes, backward compatible
- **Dependencies**: Uses only Python standard library (`json`, `logging`, `pathlib`, `os`)
- **File Format**: Pure NDJSON (RFC compliant, tool-friendly)

## Testing Results

### Unit Tests
```
tests/test_activity_logger.py: 12/12 PASSED ✅
tests/test_activity_interpreter.py: 25/25 PASSED ✅
Total Activity Tests: 37/37 PASSED ✅
```

### Test Coverage
- Valid JSON logging: ✅
- Malformed JSON handling: ✅
- File I/O error cases: ✅
- Lazy file initialization: ✅
- Context manager lifecycle: ✅
- Directory creation: ✅
- JSON formatting consistency: ✅
- Integration with interpreter: ✅

### Manual Verification
- Logger correctly integrated into oneshot.py activity pipeline
- Activity interpreter properly passes raw JSON to logger
- Session lifecycle properly manages logger initialization and cleanup
- No breaking changes to existing functionality

## Success Criteria Met

✅ **Data Purity**
- Log files contain only valid NDJSON lines (one JSON object per line)
- No metadata, timestamps, or wrapper objects in log files
- Compatible with `jq` and standard NDJSON analysis tools

✅ **Error Handling**
- Corrupt data discarded with informative warning messages
- No attempts to fix or reconstruct incomplete JSON
- Warnings logged to stderr for debugging visibility

✅ **File Management**
- Log files created beside session files: `session.json` → `session-log.json`
- Lazy initialization prevents empty file creation
- Automatic cleanup of unused log files

✅ **Diagnostic Value**
- Raw NDJSON streams provide clean data for analysis
- Warning messages help identify parsing failure points
- Files correlate directly with session output for debugging

## Delivery Checklist

- ✅ Working NDJSON logger with strict validation
- ✅ Integration into activity processing pipeline
- ✅ Pure NDJSON log files beside session files
- ✅ Warning messages for corrupt data
- ✅ Comprehensive test suite (12 tests, all passing)
- ✅ Documentation for diagnostic usage
- ✅ Context manager support for resource cleanup
- ✅ Automatic directory creation
- ✅ Empty file cleanup

## Usage Example

```python
from oneshot.providers.activity_logger import ActivityLogger
from oneshot.providers.activity_interpreter import get_interpreter

# Create logger
logger = ActivityLogger("session_base_path")

# Use with interpreter
interpreter = get_interpreter()
events = interpreter.interpret_activity(raw_output, activity_logger=logger)

# Cleanup
logger.finalize_log()

# Or use as context manager
with ActivityLogger("session_base_path") as logger:
    events = interpreter.interpret_activity(raw_output, activity_logger=logger)
    # Automatic cleanup on exit
```

## Future Enhancements

- Log filtering/rotation if files grow very large
- Historical log analysis for parser improvement
- Integration with system improvement workflows
- Executor-specific pattern recognition training

## Notes

- All implementation was already in place from previous session
- Fixed minor indentation error in test_oneshot.py
- Activity logger tests fully passing (37/37)
- Implementation aligns perfectly with project plan specifications
- No breaking changes to existing functionality
