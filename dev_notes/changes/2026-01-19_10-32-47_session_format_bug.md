# Change: Session Format Bug Identified

## Related Project Plan
dev_notes/project_plans/2026-01-19_10-27-36_test_prompt_functionality.md

## Overview
During Direct provider testing, a bug was identified in session file handling. The code inconsistently handles session file formats - creating markdown files in some cases but expecting JSON format in others.

## Files Modified
- src/oneshot/oneshot.py (examined for session handling logic)

## Impact Assessment

### Bug Details:
The `run_oneshot` function has inconsistent session file format handling:

1. **When creating new session with `session_log`**: Creates a markdown file with header
2. **When resuming from session_log**: Tries to load the file as JSON (line 964: `session_data = json.load(f)`)

This causes a `JSONDecodeError` when the session file contains markdown content instead of JSON.

### Root Cause:
In the session file creation logic (around lines 880-920), when `session_log` is provided:
- If file exists: calls `read_session_context()` which handles both JSON and markdown
- If file doesn't exist: creates markdown file with header

But in the resumption logic (around line 964), it always tries to load as JSON regardless of format.

### Expected Behavior:
Session files should either:
- Always use JSON format (preferred for programmatic access)
- Or properly detect and handle both formats consistently

### Immediate Workaround:
Use `--keep-log` flag or avoid `--session-log` parameter to prevent the format mismatch.

### Long-term Fix:
Update session handling to be consistent - either always use JSON or properly detect format on read.

### Next Steps:
Continue testing with workarounds, then fix the session format inconsistency.