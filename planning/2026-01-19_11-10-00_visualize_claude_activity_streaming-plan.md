# Project Plan: Visualize Claude Activity Streaming

## Objective

Enhance the oneshot system to visualize Claude executor activity in real-time by filtering and interpreting its streaming output. Instead of showing raw logs with cost/usage metadata, stream more informative activity updates directly to the user so they can see what Claude is doing during the session.

## Current State Analysis

1. **Existing Infrastructure:**
   - PTY-based streaming is already implemented (`call_executor_pty`)
   - JSON parsing for streaming output exists (`parse_streaming_json`)
   - Activity monitoring via file timestamps (`monitor_task_activity`)
   - Event system for broadcasting task state (`events.py`)
   - ProviderLogger with filtering capability

2. **What's Working:**
   - Claude executor calls stream output via PTY
   - Task activity is monitored but not visually presented to user
   - Event emitter infrastructure is available for broadcasting updates

3. **What's Missing:**
   - Filtering of cost/usage metadata from Claude output
   - Interpretation layer to extract meaningful activity details (tool calls, reasoning, actions)
   - Real-time streaming visualization to the user during session
   - Integration of executor activity into the event system

## Implementation Steps

### Step 1: Create Activity Interpreter Module
- **File:** `src/oneshot/providers/activity_interpreter.py`
- **Purpose:** Parse Claude executor output and extract meaningful activity patterns
- **Functionality:**
  - Filter out cost/usage/token metadata
  - Identify tool calls, reasoning phases, file modifications
  - Categorize activity (planning, execution, debugging, etc.)
  - Return structured activity events suitable for UI display
- **Key Methods:**
  - `interpret_activity(raw_output: str) -> List[ActivityEvent]`
  - `filter_metadata(text: str) -> str` - Remove cost/usage info
  - `extract_tool_calls(text: str) -> List[ToolCall]`
  - `extract_actions(text: str) -> List[Action]`

### Step 2: Extend Event System
- **File:** `src/oneshot/events.py`
- **Changes:**
  - Add `EXECUTOR_ACTIVITY` event type for real-time Claude activity
  - Create `ExecutorActivityPayload` dataclass with activity details
  - Structure: activity type, description, timestamp, executor context
- **Example payload:**
  ```json
  {
    "event_type": "executor_activity",
    "timestamp": "2026-01-19T11:10:00Z",
    "activity_type": "tool_call",
    "description": "Calling bash command: git status",
    "metadata": {...}
  }
  ```

### Step 3: Integrate Activity Interpreter with Executor
- **File:** `src/oneshot/providers/__init__.py` (ExecutorProvider)
- **Changes:**
  - When receiving streaming output from executor, pass through interpreter
  - Emit `EXECUTOR_ACTIVITY` events for each meaningful activity
  - Maintain clean raw output for logging/debugging
  - Keep performance impact minimal

### Step 4: Filter Sensitive Metadata
- **File:** `src/oneshot/providers/activity_interpreter.py`
- **Patterns to filter:**
  - Token counts and costs (e.g., "input tokens: 1234", "cost: $0.05")
  - API usage metrics
  - Internal usage statistics
  - Keep: tool names, action descriptions, file paths, command summaries
- **Strategy:** Use regex patterns + keyword detection to identify and remove

### Step 5: Create Display Formatter
- **File:** `src/oneshot/providers/activity_formatter.py` (optional)
- **Purpose:** Format activity events for terminal/web display
- **Features:**
  - Colorized terminal output
  - Compact representation suitable for real-time streaming
  - Hierarchical display (parent action → sub-actions)
  - Progress indicators where applicable

### Step 6: Update CLI and Web UI
- **Files:**
  - `src/cli/oneshot_cli.py` - Subscribe to and display activity events
  - `src/oneshot/web_ui.py` - Stream activity to WebSocket clients
- **Changes:**
  - Register listener for `EXECUTOR_ACTIVITY` events
  - Display activity in real-time as it occurs
  - Buffer and aggregate for batch display if needed
  - Show activity log alongside task output

### Step 7: Testing
- **File:** `tests/test_activity_interpreter.py`
- **Coverage:**
  - Test metadata filtering (costs, tokens, usage)
  - Test tool call extraction
  - Test activity event generation
  - Test graceful handling of unexpected output formats
  - Mock Claude executor output patterns

### Step 8: Documentation and Integration
- **Files:** Update relevant docs
- **Items:**
  - Document activity event types and structure
  - Add examples of interpreted activity
  - Update architecture diagram if exists
  - Document filtering rules for sensitive data

## Success Criteria

1. ✅ Claude activity is streamed to user in real-time
2. ✅ Cost/usage metadata is hidden from user view (filtered before display)
3. ✅ Activity events contain meaningful information (tool calls, actions, reasoning)
4. ✅ CLI shows activity updates as they occur
5. ✅ Web UI displays activity stream in real-time
6. ✅ Existing output/logging still works unchanged
7. ✅ No performance degradation in executor calls
8. ✅ All tests pass

## Testing Strategy

1. **Unit Tests:**
   - Test activity interpreter against real Claude output samples
   - Test metadata filtering patterns
   - Test event generation

2. **Integration Tests:**
   - Test executor with activity streaming enabled
   - Verify events flow through emitter correctly
   - Test CLI/UI display of events

3. **Manual Testing:**
   - Run actual Claude executor and verify activity stream
   - Inspect that sensitive data is filtered
   - Check for any performance impact

## Risk Assessment

**Low Risk:**
- New module that processes output non-destructively
- Doesn't affect existing executor functionality
- Can be toggled on/off via configuration
- Falls back gracefully if interpreter fails

**Potential Issues:**
1. **Pattern Matching:** Claude output format may vary; regex patterns may miss some cases
   - *Mitigation:* Start with common patterns, test against real output samples, allow user filtering customization
2. **Performance:** Parsing and filtering large outputs
   - *Mitigation:* Process incrementally, use efficient string operations
3. **Completeness:** May not capture all meaningful activity patterns initially
   - *Mitigation:* Design as extensible, can add patterns over time

**Edge Cases:**
- Incomplete/truncated JSON in streaming output → handled by existing parser
- Binary data or unusual characters → safe filtering needed
- Very high activity frequency → may need event aggregation/throttling
