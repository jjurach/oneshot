# Change: Fix Markdown Session Logging in Oneshot

## Overview
Fixed a critical bug in `src/oneshot/oneshot.py` where the `--session-log` flag with markdown files (`.md` extension) would fail with a JSON parsing error. The code was creating markdown files but then attempting to parse them as JSON during iteration logging.

## Files Modified

### `src/oneshot/oneshot.py`
- **Lines 990-1007**: Updated worker output logging to check `use_markdown_logging` flag before attempting JSON parsing. Now properly appends to markdown files with worker iteration headers.
- **Lines 1009-1017**: Fixed summary stats to calculate iteration count differently for markdown vs JSON formats.
- **Lines 1049-1066**: Updated auditor response logging to handle both markdown and JSON formats appropriately.
- **Lines 1084-1101**: Added conditional handling for completion status updates - markdown files now get appended completion markers instead of attempting JSON updates.

## Problem Description
When users ran the demo script with `--session-log demo_session.md`, the script would:
1. Successfully call the local Ollama model
2. Receive a valid JSON response from the worker
3. Fail with `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` when trying to log the response

This happened because:
- The code set `use_markdown_logging = True` when the file extension was `.md`
- A markdown header was written to the file during initialization
- During the iteration loop, the code tried to read and parse the markdown file as JSON
- This caused parsing to fail on the markdown header text

## Solution
Added proper conditional logic using the `use_markdown_logging` flag throughout the iteration loop:
- When `use_markdown_logging` is True: append text to markdown file with section headers
- When `use_markdown_logging` is False: read/write JSON as before

## Success Criteria Met
✅ `./demo-direct-executor.sh` runs successfully with default task
✅ `./demo-direct-executor.sh "What is 2+2?"` runs successfully with custom task
✅ Session log correctly saved to `dev_notes/oneshot/demo_session.md`
✅ Auditor confirms "DONE" after one iteration
✅ Both tasks complete without errors

## Impact Assessment
- **Scope**: Affects only the markdown session logging path (when `--session-log` is used with `.md` files)
- **Breaking Changes**: None - this was a broken feature now being fixed
- **Backwards Compatibility**: Fully maintained - JSON logging path unchanged
- **Testing**: Verified with two different tasks through the demo script
