# Project Plan: Claude Activity Visualization Integration

## Objective

Integrate the existing activity interpretation and formatting system into the real-time executor streaming flow to provide users with meaningful Claude activity information while hiding sensitive metadata (costs, tokens, usage statistics). This will allow users to see what Claude is actually doing during session execution.

## Current State Analysis

### What Already Exists
1. **ActivityInterpreter** (`activity_interpreter.py`): Parses executor output and extracts meaningful activity patterns
   - Filters out sensitive metadata (tokens, costs, usage)
   - Extracts tool calls, planning, file operations, errors
   - Returns structured `ActivityEvent` objects

2. **ActivityFormatter** (`activity_formatter.py`): Formats activity events for display
   - Color-coded output by activity type
   - Icon support for activity types
   - Multiple display modes (single event, multiple events, streaming, summary)

3. **Event System** (`events.py`): Async event emitter with pub/sub
   - `EXECUTOR_ACTIVITY` event type exists but is not being populated
   - Web UI and TUI already listen for events

### What's Missing
1. **Integration in call_executor()**: Activity interpreter is not being called during streaming
2. **Real-time Streaming**: Activities not being emitted as Claude executes
3. **Sensitive Data Filtering**: Output containing costs/tokens still shown to users
4. **Event Emission**: `EXECUTOR_ACTIVITY` events not being published

## Implementation Steps

### Step 1: Modify oneshot.py to use ActivityInterpreter
- Import `ActivityInterpreter` in `oneshot.py`
- During streaming in `call_executor()`, capture output chunks
- For each chunk, call `interpreter.interpret_activity()` to extract activities
- Emit `EXECUTOR_ACTIVITY` events with extracted activities
- Store activities in task context for later display

**Files to modify:**
- `src/oneshot/oneshot.py` - `call_executor()` and `call_executor_async()` functions

### Step 2: Integrate with Event System
- Create activity stream emitter that publishes to `event_emitter`
- Emit `EXECUTOR_ACTIVITY` events with:
  - task_id (from context)
  - executor_name (claude, cline, etc.)
  - activities (list of ActivityEvent objects)
  - timestamp
- Ensure events are non-blocking and don't slow down execution

**Files to modify:**
- `src/oneshot/providers/__init__.py` - ExecutorProvider to pass activity_emitter

### Step 3: Add Activity Display to call_executor()
- After executor completes, format and display activity summary
- Call `ActivityFormatter.get_activity_summary()` to show statistics
- Show key activities (tool calls, file operations, errors)
- Filter activities to only show non-sensitive ones

**Files to modify:**
- `src/oneshot/oneshot.py` - output formatting after execution

### Step 4: Update TUI to Show Real-time Activities
- TUI already listens to `EXECUTOR_ACTIVITY` events
- Add activity panel to task detail view
- Show activity stream as it happens
- Display activity summary for completed tasks

**Files to modify:**
- `src/oneshot/tui.py` - potentially add activity panel

### Step 5: Update Web UI to Stream Activities
- Web UI already has WebSocket streaming
- Emit activity events through existing `/ws/events` endpoint
- Format activities for JSON serialization
- Display activities in activity panel on dashboard

**Files to modify:**
- `src/oneshot/web_ui.py` - ensure activities are properly JSON serialized

### Step 6: Metadata Filtering
- Use `ActivityInterpreter.filter_metadata()` to clean output before user display
- Hide token counts, costs, cache statistics
- Preserve informative content (tool names, file paths, reasoning steps)
- Show a note like "Some usage statistics hidden for clarity"

**Files to modify:**
- `src/oneshot/oneshot.py` - filter output in display phase
- `src/oneshot/providers/base.py` - potentially add filtering

## Success Criteria

1. ✅ Activities are extracted from Claude output during execution
2. ✅ Sensitive metadata (costs, tokens) is removed from displayed output
3. ✅ Real-time activity stream is visible in CLI/Web UI
4. ✅ Activity summary shows key operations (tool calls, file operations, etc.)
5. ✅ Streaming doesn't slow down execution significantly
6. ✅ Activity events are properly emitted and received by UI components
7. ✅ No breaking changes to existing executor functionality

## Testing Strategy

1. **Unit Tests**: Test ActivityInterpreter and ActivityFormatter in isolation
   - Test metadata filtering with various token/cost formats
   - Test activity extraction with sample Claude output
   - Test formatting with and without colors/icons

2. **Integration Tests**: Test end-to-end with sample executor output
   - Mock claude executor with activity-rich output
   - Verify activities are extracted and emitted
   - Verify events are received by UI

3. **Manual Testing**:
   - Run with actual Claude executor
   - Observe real-time activity streaming
   - Verify metadata is filtered
   - Check performance impact

4. **CLI Test**:
   - Execute sample command with activity tracing enabled
   - Verify output shows activities, not raw metadata
   - Verify summary statistics are present

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Output parsing misses activities | Medium | Medium | Use robust regex patterns, test with real outputs |
| Event emission impacts performance | Low | Low | Use non-blocking async events, set queue limits |
| Breaks existing executors | Low | High | Maintain backward compatibility, test all executor types |
| Memory usage from buffering activities | Low | Medium | Limit activity buffer size per task |
| Sensitive data still leaks | Low | High | Test filtering patterns thoroughly |

## Architecture Notes

### Data Flow
```
claude executor output
    ↓
PTY streaming captures chunks
    ↓
ActivityInterpreter.interpret_activity()
    ↓
Extract structured ActivityEvent objects
    ↓
Emit EXECUTOR_ACTIVITY events
    ↓
TUI/Web UI display activities in real-time
    ↓
After execution, show activity summary
```

### Event Format
```python
{
    'type': 'EXECUTOR_ACTIVITY',
    'task_id': 'task-123',
    'executor': 'claude',
    'activities': [
        {
            'activity_type': 'tool_call',
            'description': 'Tool call: grep config.json',
            'details': {...}
        },
        ...
    ],
    'timestamp': '2026-01-19T18:23:45Z'
}
```

### Implementation Priority
1. Core integration in `call_executor()` (Step 1, 2)
2. Event emission (Step 2)
3. CLI output filtering (Step 3)
4. UI enhancements (Steps 4, 5)
5. Metadata filtering (Step 6)

## Dependencies
- Existing `ActivityInterpreter` and `ActivityFormatter` classes
- Existing event system infrastructure
- Async event handling capability
