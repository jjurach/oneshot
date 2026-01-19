# Project Plan: Enhanced Activity Visualization for Users

## Objective

Enhance the user-facing visualization of Claude activity in real-time by displaying meaningful activities (tool calls, planning, file operations, thinking) while automatically filtering sensitive metadata (costs, token counts, usage metrics). Make the activity stream visible to users so they can understand what Claude is doing during a session.

## Current Status

✅ **Infrastructure Completed:**
- Activity interpretation and extraction system in place
- Metadata filtering working (19.4% content reduction, sensitive data removed)
- Event emission system ready (EXECUTOR_ACTIVITY events)
- Activity formatter with colors and icons available
- Integration into executor output pipeline completed (all 4 executor paths covered)

⚠️ **User-Facing Display Incomplete:**
- Activity events are being emitted but not displayed to users
- Web UI hasn't subscribed to EXECUTOR_ACTIVITY events for display
- CLI/TUI doesn't show real-time activity streams
- Users only see final output, not the process

## Implementation Steps

### Phase 1: CLI Real-Time Activity Display
**Goal:** Show activities in the terminal as they stream during execution

1. **Modify CLI executor output handling** (`src/oneshot/oneshot.py`)
   - Add new display mode flag: `--show-activity` or enabled by default for interactive terminal
   - Display activities from `_process_executor_output()` in real-time
   - Use ActivityFormatter with colors for terminal visibility
   - Show activities as they're emitted without blocking execution
   - Sample format: `[🔧 TOOL] bash -c "git status"` followed by filtered output

2. **Create activity display utility** (new file: `src/oneshot/providers/activity_display.py`)
   - `ActivityDisplayManager` class to handle real-time display
   - Methods for:
     - `display_activity()` - Show single activity in terminal
     - `display_activity_header()` - Show session start with executor info
     - `display_activity_footer()` - Show completion summary
     - `format_activity_line()` - Create compact single-line format for streaming
   - Integration with existing ActivityFormatter
   - Support for disabling via `--quiet` or `ONESHOT_QUIET` env var

3. **Integrate into executor paths** (`src/oneshot/oneshot.py`)
   - After `_process_executor_output()` returns activities, display them
   - Show each activity immediately as emitted (non-blocking)
   - Sample display order:
     ```
     Starting task with Claude executor...
     [📋 PLANNING] Analyzing requirements
     [🧠 REASONING] Determining approach
     [🔧 TOOL] bash -c "ls -la"
     [📄 FILE_OPERATION] Creating file: src/new_feature.py
     [⚙️ CODE_EXECUTION] Running tests
     ✅ Task completed successfully
     ```

4. **Add configuration options** (`src/oneshot/config.py` or command-line args)
   - `--show-activity` (default: True for TTY, False for pipe)
   - `--activity-format` (options: "compact", "detailed", "icons", "plain")
   - `--quiet` or `--no-activity` to suppress activity display
   - Environment variable: `ONESHOT_SHOW_ACTIVITY`

### Phase 2: Web UI Activity Panel
**Goal:** Display live activity stream in the web dashboard

1. **Extend WebSocket streaming** (`src/oneshot/web_ui.py`)
   - Subscribe to EXECUTOR_ACTIVITY events in `_setup_event_handling()`
   - Broadcast activities to connected WebSocket clients
   - Send activity events as JSON:
     ```json
     {
       "event_type": "EXECUTOR_ACTIVITY",
       "task_id": "task-123",
       "activity_type": "tool_call",
       "description": "bash -c \"git status\"",
       "timestamp": "2026-01-19T20:15:30Z",
       "executor": "claude"
     }
     ```

2. **Create activity stream UI component** (new file: `src/oneshot/static/activity-stream.js`)
   - Real-time activity list component
   - Auto-scroll to latest activity
   - Color-coded activity types matching ActivityFormatter
   - Icons matching ActivityFormatter
   - Collapsible details for each activity
   - Timeline view showing activity progression

3. **Update dashboard HTML** (embedded in `web_ui.py`, `_get_dashboard_html()`)
   - Add activity stream panel to left/center of dashboard
   - Activity panel shows live stream during task execution
   - Show activity count and session duration
   - Activity summary on task completion

4. **Add filtering/search in web UI**
   - Filter activities by type (tool_call, planning, file_operation, etc.)
   - Search activities by description
   - Show/hide sensitive activity types
   - Activity history for completed tasks

### Phase 3: TUI Activity Display
**Goal:** Integrate activity streaming into terminal dashboard

1. **Extend OneshotTUI** (`src/oneshot/tui.py`)
   - Add activity stream panel to the layout (right-side panel)
   - Subscribe to EXECUTOR_ACTIVITY events via event_emitter
   - Real-time activity list display using Rich library
   - Show 5-10 most recent activities in scrollable panel

2. **Create TUI activity panel** (in `tui.py`)
   - `ActivityStreamPanel` class extending Rich Panel
   - Display activities in chronological order
   - Color-coded by activity type
   - Show activity timestamp
   - Collapse long descriptions with ellipsis

3. **Keyboard shortcuts** (in `tui.py`)
   - 'A' - Toggle activity panel visibility
   - 'F' - Filter activities by type (cyclic)
   - '>' - Scroll activity panel down
   - '<' - Scroll activity panel up
   - 'C' - Clear activity history

## Success Criteria

✅ **CLI Display:**
- Activities visible in real-time when running `oneshot` command
- Sensitive metadata (costs/tokens) not shown
- Can be disabled with `--quiet` flag
- Works on all platforms (Unix/Windows)
- No performance impact on execution

✅ **Web UI Display:**
- Activity stream visible in web dashboard during task execution
- Activities update in real-time via WebSocket
- Can filter/search activities
- Activity history persists for completed tasks
- Looks good on mobile and desktop

✅ **TUI Display:**
- Activity stream panel shows in terminal dashboard
- Activities display in real-time
- Can toggle and filter activities
- Scrollable when list exceeds visible area

✅ **Data Quality:**
- No sensitive metadata (costs, tokens, usage) in any display
- Meaningful descriptions for all activity types
- Activity timestamps accurate
- Activity counts and summaries accurate

✅ **Backward Compatibility:**
- Existing CLI usage unchanged (activities shown by default)
- Web UI works without activity display (graceful fallback)
- TUI works without activity panel (graceful fallback)
- No breaking changes to any APIs

## Testing Strategy

### Unit Tests
1. **Activity Display Tests** (`tests/test_activity_display.py`)
   - Test `ActivityDisplayManager` methods
   - Verify activity formatting with different modes
   - Test filtering of sensitive metadata
   - Test configuration option handling

2. **Integration Tests**
   - Test CLI display with sample activities
   - Test Web UI WebSocket streaming
   - Test TUI activity panel
   - Test with all executor types (claude, cline, aider, gemini)

### Manual Tests
1. **CLI Manual Testing:**
   - Run `oneshot --help` and verify `--show-activity` documented
   - Run task and verify activities display in real-time
   - Run with `--quiet` and verify no activities shown
   - Run with `--activity-format plain` and verify no colors/icons
   - Verify no cost/token information visible

2. **Web UI Manual Testing:**
   - Start web server and connect browser
   - Execute task and verify activities stream in real-time
   - Verify activity list updates without page refresh
   - Test activity filtering
   - Check mobile responsiveness

3. **TUI Manual Testing:**
   - Start TUI and run task
   - Verify activity panel shows activities
   - Test keyboard shortcuts for filtering/scrolling
   - Verify no performance degradation

### Integration with Existing Tests
- Verify all 216 existing tests still pass
- Verify activity interpreter tests (25) still pass
- Add new tests for display functionality (target: +30 tests)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Activity display slows execution | Low | Medium | Use async event emission (already in place) |
| Regex patterns miss activities | Low | Low | Use proven patterns from existing interpreter tests |
| WebSocket connection drops in web UI | Medium | Medium | Add reconnect logic with exponential backoff |
| Terminal rendering issues on Windows | Medium | Low | Test on Windows, fallback to plain format |
| Activity event queue grows too large | Low | Medium | Limit queue size, discard old events if needed |
| UI components overwhelmed by activity volume | Medium | Medium | Implement batching and rate limiting |

## Implementation Order (Recommended)

1. **Start with CLI** (Phase 1, Step 1-2) - Smallest scope, immediate user value
2. **Test CLI thoroughly** - Verify no regressions
3. **Add Web UI** (Phase 2, Step 1-2) - Medium scope, builds on CLI work
4. **Add TUI** (Phase 3) - Largest scope, uses same patterns as Web UI
5. **Add filtering/search** (Phase 2, Step 4 and Phase 3, Step 3) - Optional enhancement

## Files to Create
- `src/oneshot/providers/activity_display.py` - Display management
- `src/oneshot/static/activity-stream.js` - Web UI component
- `tests/test_activity_display.py` - Display unit tests
- `tests/test_activity_visualization.py` - Integration tests

## Files to Modify
- `src/oneshot/oneshot.py` - CLI activity display integration
- `src/oneshot/web_ui.py` - WebSocket activity streaming
- `src/oneshot/tui.py` - TUI activity panel
- `src/oneshot/config.py` - Configuration options (if exists)

## Dependencies & Constraints

- **Already Available:**
  - ActivityInterpreter (extracts activities)
  - ActivityFormatter (formats for display)
  - AsyncEventEmitter (broadcasts events)
  - ExecutorActivityPayload (event data structure)

- **External Dependencies:**
  - Rich library (already used in TUI)
  - FastAPI WebSockets (already used in web UI)
  - No new dependencies needed

## Effort Estimate Components
(Not a time estimate, but complexity breakdown)

- **CLI Display:** Moderate complexity (integration + display logic)
- **Web UI:** Medium complexity (WebSocket handling + UI components)
- **TUI:** Medium complexity (Rich library integration)
- **Testing:** Significant (comprehensive test coverage required)
- **Total Scope:** 3 medium-sized features with full test coverage

## Deliverables

1. ✅ Working CLI activity display (visible in real-time terminal output)
2. ✅ Working Web UI activity panel (streaming via WebSocket)
3. ✅ Working TUI activity panel (integrated in dashboard)
4. ✅ Configuration options (show-activity, format, quiet flags)
5. ✅ Comprehensive test suite (unit + integration)
6. ✅ Documentation of new features
7. ✅ No breaking changes to existing functionality

## Next Steps After Approval

1. Implement Phase 1 (CLI display) first
2. Run tests to verify no regressions
3. Manual testing on multiple platforms
4. Implement Phase 2 (Web UI) and Phase 3 (TUI)
5. Full integration testing
6. Documentation and commit
