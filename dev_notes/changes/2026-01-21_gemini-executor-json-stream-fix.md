# Change: Gemini Executor JSON Stream Parsing Fix

**Related Project Plan**: `dev_notes/project_plans/2026-01-21_01-43-44_gemini-executor-diagnostics.md`

## Overview

Fixed critical bug in the Gemini executor's `parse_streaming_activity()` method that was causing all streaming output to be filtered out, resulting in empty responses. The executor was looking for "Action:", "Observation:", and "Error:" keywords that are not present in Gemini's stream-json output format.

## Root Cause

The original implementation filtered output lines based on patterns specific to agentic frameworks (ReAct-style action/observation patterns). However, Gemini's stream-json format outputs JSON objects with type fields:
- `"type": "init"` - Session initialization
- `"type": "message"` - User/assistant messages with streaming deltas
- `"type": "result"` - Final result with statistics

Since none of these JSON objects contain "Action:", "Observation:", or "Error:" keywords, all JSON lines were filtered out, leaving only informational text like "YOLO mode is enabled..."

## Files Modified

### `src/oneshot/providers/gemini_executor.py`

**Method**: `parse_streaming_activity(self, raw_output: str) -> Tuple[str, Dict[str, Any]]`

**Changes**:
1. Rewrote method to properly parse Gemini's stream-json format
2. Added JSON object parsing with fallback to info lines
3. Extract assistant message content from "message" type objects with role="assistant"
4. Extract result statistics from final "result" type object
5. Combine streaming message deltas into coherent summary
6. Enrich auditor_details with:
   - `format`: Identifies as "stream-json"
   - `message_count`: Count of assistant messages
   - `assistant_messages`: List of message content
   - `json_objects_count`: Count of parsed JSON objects
   - `info_lines`: Non-JSON informational output
   - `final_status`: Result status from final object
   - `result_stats`: Token usage and timing information

## Implementation Details

The new implementation:
1. Strips ANSI color codes (using inherited `_strip_ansi_colors()` method)
2. Separates lines into JSON objects and info lines
3. Parses each line starting with `{` as potential JSON
4. Extracts assistant messages from objects where `type=="message"` and `role=="assistant"`
5. Extracts final result statistics when `type=="result"`
6. Combines assistant message content into a single summary string
7. Falls back to info lines if no assistant messages found
8. Provides comprehensive auditor details for logging

## Validation

### Testing Results
- **Unit tests**: All 37 executor framework tests pass
- **Full test suite**: All 475 tests pass, 5 skipped
- **Regressions**: None detected

### Functional Validation
```
Input: "what is 2+2?"
Output: "The --prompt (-p) flag has been deprecated... 2 + 2 = 4"
Auditor Details:
  - executor_type: "gemini"
  - format: "stream-json"
  - message_count: 2
  - assistant_messages: [deprecation warning, "2 + 2 = 4"]
  - result_stats: {total_tokens: 16433, output_tokens: 56, duration_ms: 3079}
```

### Output Format
The executor now correctly:
- Extracts content from Gemini's streaming JSON format
- Combines multi-message streams into coherent output
- Provides detailed token usage and performance metrics
- Maintains backward compatibility with the ExecutionResult interface

## Impact Assessment

**Scope**: Isolated to gemini_executor module, no changes to other executors

**Benefits**:
- Gemini executor now produces non-empty output from successful executions
- Accurate message content extraction from streaming format
- Detailed auditor information for debugging and monitoring
- Proper handling of Gemini's specific stream-json format

**Backward Compatibility**:
- No breaking changes to public interface
- ExecutionResult format unchanged
- Auditor details structure enhanced (additive only)

**Risk**: Very low - changes isolated to JSON parsing logic within gemini_executor

## Testing Strategy Used

1. **Root cause analysis**: Examined test data from `tmp/test-cases/gemini2/` and compared actual Gemini output format
2. **Diagnostic testing**: Ran `gemini --yolo --output-format stream-json` to establish baseline format
3. **Unit testing**: Verified new parsing logic handles JSON streams correctly
4. **Regression testing**: Full pytest suite passes with no failures
5. **Integration testing**: Verified executor produces correct output for simple queries

## Success Criteria Met

✅ gemini_executor correctly parses streaming JSON from gemini-cli
✅ Output format matches Gemini's native `--output-format stream-json` format
✅ Accurate result summary provided to auditor
✅ Debug output clearly shows transformation steps
✅ All executor tests pass with no regressions
✅ Diagnostic commands complete successfully without errors
