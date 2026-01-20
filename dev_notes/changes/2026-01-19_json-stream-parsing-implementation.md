# Change: Improve JSON Stream Parsing for Cline Output

## Related Project Plan
`dev_notes/project_plans/2026-01-19_improve-json-parsing.md`

## Overview
Enhanced `_process_executor_output()` to properly handle cline's streaming JSON output by:
1. Removing ANSI escape codes that cline includes
2. Using brace-counting to identify complete JSON objects
3. Extracting text from specific activity types

### Key Improvements
1. **Robust JSON Stream Splitting**: New `split_json_stream()` function:
   - Removes ANSI escape codes (e.g., `[38;5;252;3m`)
   - Uses brace-counting algorithm to find complete JSON objects
   - Handles any whitespace or formatting between objects
   - More reliable than simple pattern matching
2. **Activity Text Extraction**: New `extract_activity_text()` function extracts text from:
   - Activities with `"say":"completion_result"`
   - Activities with `"ask":"plan_mode_respond"`
3. **Extracted JSON as Primary Output**: Critical fix!
   - Returns extracted JSON text as `worker_output` instead of activity summary
   - Ensures auditor receives actual JSON responses
   - Enables proper JSON extraction for auditor validation
   - Closes the loop: extraction → output → auditor processing
4. **Enhanced Debug Logging**: Comprehensive debug output showing:
   - ANSI code removal and cleaned output length
   - JSON object count and structure
   - Text extraction results
   - Aggregated text content
5. **Bug Fix**: Fixed undefined `filtered_lines` variable at line 1582 (changed to `filtered_count`)

## Files Modified

### src/oneshot/oneshot.py
- **Lines 773-833**: Added `split_json_stream()` helper function
  - Removes ANSI escape codes from output first
  - Uses brace-counting algorithm to identify complete JSON objects
  - Handles any whitespace/formatting between objects
  - Returns list of parsed JSON objects
  - Includes debug logging for ANSI removal and object count

- **Lines 835-870**: Added `extract_activity_text()` helper function
  - Checks for specific cline activity types
  - Extracts "text" property from matching activities
  - Supports `"say":"completion_result"` activities
  - Supports `"ask":"plan_mode_respond"` activities
  - Includes debug logging for text extraction

- **Lines 905-1011**: Enhanced `_process_executor_output()` function
  - Calls `split_json_stream()` to parse JSON objects from cline output
  - Iterates through objects to extract text via `extract_activity_text()`
  - Aggregates extracted text segments into `aggregated_text`
  - **Returns extracted JSON as primary output** instead of activity summary
  - Improves auditor ability to extract and parse worker responses
  - Handles both meaningful activities and no activities cases
  - Maintains backward compatibility with existing activity interpreter

- **Line 1582**: Fixed undefined `filtered_lines` variable
  - Changed from `len(filtered_lines)` to `len(filtered_count)`
  - References the correctly computed activity count

## Impact Assessment

### Positive Impacts
- Better parsing of cline's multi-object JSON streaming output
- Clear extraction of relevant activity text
- Enhanced debug visibility into JSON structure and parsing
- Fix for undefined variable bug

### Backward Compatibility
- All changes are additive (new functions, enhanced existing function)
- Existing activity interpreter still called and used
- No changes to public API or function signatures
- Debug logging is conditional on VERBOSITY level

### Testing Status
- Implementation complete and integrated
- Debug and verbose logging enabled for inspection
- Ready for testing with: `oneshot --debug --verbose "query"`

## Technical Notes

### JSON Stream Parsing Algorithm
Cline outputs consecutive JSON objects interspersed with ANSI color codes:
```
[ANSI CODES]
{...object1...}
[ANSI CODES]
{...object2...}
[ANSI CODES]
{...object3...}
```

**Algorithm:**
1. Remove all ANSI escape codes using regex: `\x1B\[[0-9;]*m` and `\[38;5;\d+m`
2. Iterate through cleaned output character-by-character
3. Track opening `{` and closing `}` braces
4. When brace count reaches 0, a complete JSON object has been found
5. Parse each complete object with `json.loads()`

This approach is robust to any whitespace, formatting, or ordering between objects.

### Activity Types Extracted
- `"say":"completion_result"` - Contains final completion results
- `"ask":"plan_mode_respond"` - Contains plan mode responses

### Debug Output Tags
- `[JSON STREAM]`: JSON parsing and splitting details
- `[ACTIVITY TEXT]`: Text extraction from activities
- `[EXECUTOR OUTPUT]`: Overall output processing summary

## Validation
See debug output from `oneshot --debug --verbose` for:
- `[JSON STREAM] Split output into N parts` - Shows boundary detection
- `[JSON STREAM] Successfully parsed N JSON objects` - Shows parsing success
- `[ACTIVITY TEXT] Found completion_result:` - Shows extracted completion text
- `[EXECUTOR OUTPUT] Extracted N text segments` - Shows aggregation result
