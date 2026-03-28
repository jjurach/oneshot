# Project Plan: Improve JSON Stream Parsing for Cline Output

## Objective
Enhance `_process_executor_output()` to properly handle cline's streaming JSON output by:
1. Splitting the raw output by JSON object boundaries (pattern: `}\n{\n  `)
2. Parsing each JSON object individually
3. Extracting and concatenating "text" properties from specific activity types:
   - Activities with `"say":"completion_result"`
   - Activities with `"ask":"plan_mode_respond"`
4. Improving debug output to verify the parsing is working correctly

## Current State
- `_process_executor_output()` at line 773 in `src/oneshot/oneshot.py`
- Currently processes raw output through activity interpreter but doesn't explicitly handle JSON object boundaries
- May miss important text content from multi-object streams due to improper splitting

## Implementation Steps

### Step 1: Add JSON Stream Splitting Helper Function
- Create a new function `split_json_stream(raw_output: str) -> List[Dict[str, Any]]`
- Implement logic to:
  - Split by pattern `}\n{` to isolate JSON objects
  - Handle edge cases (incomplete objects, trailing/leading whitespace)
  - Add logging for debug mode to show:
    - Number of JSON objects found
    - Preview of each object
    - Any parsing errors

### Step 2: Extract Text Properties from Specific Activities
- Create a function `extract_activity_text(json_object: Dict) -> Optional[str]`
- Logic:
  - Check if object has `"say"` key with value `"completion_result"`
  - Check if object has `"ask"` key with value `"plan_mode_respond"`
  - Extract the `"text"` property if either condition is true
  - Return None if neither condition matches
- Add debug logging showing which activities have text and their content

### Step 3: Integrate into `_process_executor_output()`
- Before calling activity interpreter, try the new JSON stream splitting approach
- Collect all "text" values from completion_result and plan_mode_respond activities
- Preserve backward compatibility with existing activity interpreter path
- Add enhanced debug output:
  - Line 1458: Add `filtered_lines` variable reference (currently undefined)
  - Show raw JSON stream structure
  - Show extracted text aggregation
  - Show comparison with activity interpreter results

### Step 4: Add Comprehensive Debug Output
- When `VERBOSITY >= 2`:
  - Log raw output structure (JSON object count, sizes)
  - Log each parsed JSON object preview
  - Log text extraction results
  - Log final concatenated text
- Format debug messages clearly for visual inspection

### Step 5: Test with Command
- Execute: `oneshot --debug --verbose "what is the capital of portugal?"`
- Verify:
  - JSON objects are properly split and counted
  - Text properties are correctly extracted
  - Debug output shows expected structure
  - No errors or warnings in parsing

## Success Criteria
1. ✅ JSON stream is split correctly by `}\n{` pattern
2. ✅ Each JSON object is parsed without errors
3. ✅ Text from `"say":"completion_result"` is extracted
4. ✅ Text from `"ask":"plan_mode_respond"` is extracted
5. ✅ Debug output clearly shows the structure with `--debug --verbose` flags
6. ✅ Test command runs successfully without errors
7. ✅ Extracted text is logged clearly in debug output
8. ✅ Backward compatibility maintained (existing code still works)

## Testing Strategy
1. **Unit-level**: Manually test JSON splitting with sample cline output patterns
2. **Integration-level**: Run with `--debug --verbose` flags and verify output structure
3. **Visual verification**: Check that debug logs show:
   - Number of JSON objects parsed
   - Text content from each relevant activity
   - Proper aggregation of multi-object streams
4. **Regression**: Ensure existing functionality still works

## Risk Assessment
- **Low Risk**: Adding new helper functions doesn't modify existing logic
- **Low Risk**: Using defensive JSON parsing with error handling prevents crashes
- **Low Risk**: Debug-only output doesn't affect production behavior
- **Mitigation**: Preserve existing activity interpreter path as fallback
- **Mitigation**: Add comprehensive error logging for debugging

## Implementation Notes
- Line 1458 has reference to undefined `filtered_lines` - this should be fixed during implementation
- Focus on backward compatibility - new code should augment, not replace
- Debug output should be clear and structured for easy visual inspection
