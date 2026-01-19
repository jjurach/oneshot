# Change: Fix NDJSON Activity Logging JSON Parsing

## Related Project Plan
dev_notes/project_plans/2026-01-19_11-29-00_raw_ndjson_activity_logging.md

## Overview
Fixed the raw NDJSON activity logging feature by implementing proper multi-line JSON object extraction in the ActivityInterpreter. The original implementation assumed single-line JSON objects, but Cline's streaming output contains multi-line JSON objects.

## Files Modified

### src/oneshot/providers/activity_interpreter.py
- **Added import**: `import logging` for debug logging
- **Modified method**: `interpret_activity()` - replaced simplistic line-by-line JSON parsing with call to new `_extract_json_objects()` method
- **Added method**: `_extract_json_objects()` - properly extracts complete JSON objects from text containing multi-line JSON, handling nested braces and escaped strings correctly
- **Enhanced logging**: Added debug logging for JSON extraction failures

### tests/test_activity_interpreter.py
- **Added tests**: 4 new unit tests for JSON object extraction:
  - `test_extract_json_objects_single_line` - Tests extraction of single-line JSON objects
  - `test_extract_json_objects_multi_line` - Tests extraction of multi-line JSON objects
  - `test_extract_json_objects_mixed_content` - Tests extraction from mixed JSON/non-JSON content
  - `test_extract_json_objects_malformed` - Tests graceful handling of malformed JSON

## Impact Assessment

### Positive Impact
- ✅ **NDJSON log files are now created** - The activity logger will properly extract and log JSON objects from Cline's streaming output
- ✅ **Valid NDJSON format** - Log files contain only valid JSON objects, one per line as intended
- ✅ **Robust parsing** - Handles multi-line JSON objects, nested structures, and escaped strings correctly
- ✅ **Error resilience** - Malformed JSON is skipped with debug logging, doesn't break the logging process

### Risk Assessment
- **Low Risk**: The changes only affect JSON extraction for logging purposes, doesn't impact core functionality
- **Backward Compatible**: Existing activity interpretation for UI display continues to work unchanged
- **Tested**: Comprehensive unit tests ensure the JSON extraction works correctly

## Testing
- ✅ **Unit tests pass**: All 4 new JSON extraction tests pass
- ✅ **Existing tests pass**: All existing activity interpreter tests continue to pass
- ✅ **Integration verified**: Manual testing with sample Cline output shows correct JSON extraction and NDJSON logging

## Next Steps
The NDJSON activity logging feature is now functional. Users can run oneshot with Cline executor and expect to see `*-log.json` files created alongside session files, containing pure NDJSON streams of executor activity data for diagnostic and analysis purposes.