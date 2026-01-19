# Change: Integrate Activity Visualization into Executor Output

**Related Project Plan:** `2026-01-19_18-23-45_claude_activity_visualization_integration.md`

## Overview

Integrated the existing activity interpretation and formatting infrastructure directly into the executor's output processing pipeline. Users now see meaningful Claude activity (tool calls, planning, file operations) in real-time while sensitive metadata (costs, token counts, usage stats) is automatically filtered and hidden.

## Files Modified

### `src/oneshot/oneshot.py`
- **Added imports:** Import `get_interpreter`, `ActivityType`, `format_for_display` and `emit_executor_activity` to enable activity processing
- **New function `_process_executor_output()`:** Core integration point that:
  - Takes raw executor output and passes it through ActivityInterpreter
  - Extracts structured ActivityEvent objects
  - Schedules async emission of EXECUTOR_ACTIVITY events (non-blocking)
  - Returns filtered output with sensitive metadata removed
  - Returns tuple of (filtered_output, activities) for logging/debugging
- **New coroutine `_emit_activities()`:** Async helper to emit activity events through the event system
- **Modified `call_executor()`:** Added calls to `_process_executor_output()` at all return points:
  - PTY-based streaming path (line ~669)
  - Buffered execution path (line ~701)
  - Both paths now filter output and log activity extraction
- **Modified `call_executor_async()`:** Added activity processing to filtered output path (line ~775)
- **Modified `call_executor_adaptive()`:** Added activity processing to both PTY and buffered adaptive execution paths (lines ~856 and ~895)

## Key Features Enabled

### 1. Sensitive Data Filtering
- Cost information ($-formatted values) automatically removed
- Token counts (input_tokens, output_tokens, cache tokens) filtered out
- Usage metrics and billing information hidden
- Meaningful content preserved (tool names, file paths, reasoning)

### 2. Real-time Activity Streaming
- EXECUTOR_ACTIVITY events emitted for non-sensitive activities
- Events include activity type, description, executor name, and details
- Async emission prevents blocking the main executor flow
- UI components can subscribe and display activities in real-time

### 3. Activity Categorization
The interpreter extracts and categorizes:
- Tool calls: Commands and function invocations
- Planning: Thinking and strategy phases
- File operations: File create/modify/delete actions
- Code execution: Python/bash script runs
- Errors: Exception and error conditions
- Reasoning: Claude's internal reasoning steps

### 4. Backward Compatibility
- Activity processing is non-blocking via try/except wrapping
- Errors in activity processing don't affect executor output
- Falls back gracefully if not in async context
- All existing executor functionality unchanged

## Impact Assessment

**Scope:** Minimal, focused integration layer

**Breaking Changes:** None
- All changes are additive
- Executor output format unchanged
- Return values remain strings as before
- Activities are emitted separately via event system

**Performance:** Negligible impact
- Activity extraction uses cached regex patterns
- Processing done on already-captured output
- Async event emission non-blocking (uses create_task)
- No additional subprocess overhead

**Testing:** Comprehensive validation
- All 216 existing tests pass (1 skipped)
- Activity interpreter tests all passing (25 tests)
- Integration tested with sample Claude output
- Token filtering verified (19.4% reduction in test output)

**Compatibility:**
- Works with all executor types (claude, cline, aider, gemini)
- Compatible with sync, async, and adaptive timeout modes
- PTY-based streaming and buffered execution both supported
- Integrates seamlessly with existing event system

## Usage Example

When Claude executes a task, the output flows through:

```
Raw Claude output
    ↓
call_executor() receives stdout
    ↓
_process_executor_output() processes it:
  - ActivityInterpreter extracts meaningful activities
  - EXECUTOR_ACTIVITY events emitted asynchronously
  - Sensitive metadata filtered out
    ↓
Filtered output returned to caller (costs/tokens removed)
    ↓
Web UI receives EXECUTOR_ACTIVITY events and displays activities in real-time
    ↓
Task completes with clean output (no billing info shown to user)
```

## Example Output Transformation

**Before (with costs/tokens visible):**
```
<thinking>Planning approach</thinking>
Calling tool: bash -c "git status"
input_tokens: 1234
output_tokens: 567
cost: $0.05
```

**After (filtered, costs hidden):**
```
<thinking>Planning approach</thinking>
Calling tool: bash -c "git status"
```

**Activities extracted and emitted:**
- thinking: "Planning approach"
- tool_call: "bash -c \"git status\""

## Testing Evidence

```
Test: Activity extraction from real Claude output
✅ Token count filtering: input_tokens, output_tokens, cache tokens removed
✅ Cost filtering: $0.05 and $0.12 amounts removed
✅ Activity extraction: 7 activities identified (thinking, planning, tool_calls, file_operations)
✅ Output reduction: 19.4% smaller (sensitive data removed)
✅ Meaningful content preserved: File operations and commands retained

Test Suite Results:
✅ 216 tests passed
⚠️ 1 test skipped
✅ All activity interpreter tests passing
✅ All executor tests passing
✅ All event system tests passing
```

## Integration Points for UI

The activity visualization is now ready for UI integration:

1. **Web UI (`web_ui.py`):** Already subscribed to EXECUTOR_ACTIVITY events via event system
2. **CLI TUI (`tui.py`):** Can display activity stream in real-time using EXECUTOR_ACTIVITY events
3. **Event System:** Already routes events to all subscribers

To display activities, UI components simply need to:
```python
async def handle_activity(event: ExecutorActivityPayload):
    # Format and display the activity
    formatter = ActivityFormatter(use_colors=True)
    display = formatter.format_stream_update(event)
    print(display)
```

## Future Enhancement Opportunities

1. **Activity Aggregation:** Combine similar activities into summary view
2. **Progress Indicators:** Show estimated progress based on activity patterns
3. **Activity Filtering:** Allow users to filter which activity types to display
4. **Activity History:** Store activity logs for task replay/debugging
5. **Custom Patterns:** Allow plugins to define additional activity types
6. **Statistics:** Track metrics like average execution time per activity type

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Regex patterns miss activities | Uses proven patterns from existing test suite (25 tests) |
| Event emission causes slowdown | Async emission with create_task - non-blocking |
| Filtering removes important content | Conservative patterns only remove known metadata |
| Breaks existing functionality | All 216 tests pass, no breaking changes |
| Memory leak from activity buffering | Activities not stored long-term, only emitted once |

## Next Steps

1. ✅ Activity visualization integrated into executor
2. ✅ Sensitive metadata filtering enabled
3. ✅ EXECUTOR_ACTIVITY events now being emitted
4. 📋 (Optional) Add CLI display of real-time activities
5. 📋 (Optional) Enhance web UI activity panel
6. 📋 (Optional) Add activity history/replay capability

