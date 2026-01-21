# Cline Streaming Architecture Investigation

**Status:** COMPLETED
**Date:** 2026-01-21
**Project Plan Step:** 1

## Overview

Cline's CLI is implemented in Go (`external/cline/cli/`) and acts as a gRPC client to a background "Cline Core" instance. It handles task lifecycle, message streaming, and state management.

## Output Formats

Cline supports three output formats via the `-F` or `--output-format` flag:

1.  **`rich` (default)**: Uses `lipgloss` for styling, `huh` for interactive forms, and handles markdown rendering. It includes ANSI escape codes and assumes a TTY.
2.  **`plain`**: Similar to `rich` but without most styling and markdown rendering. Better for logging.
3.  **`json`**: Emits indented JSON objects (`json.MarshalIndent`) to `stdout`. Each message in the conversation (both `say` and `ask` types) is emitted as a complete JSON object once finished.

### JSON Streaming Behavior

In `json` mode, Cline follows the conversation turns.
-   When following a task (`cline task follow-complete` or `cline --oneshot`), it subscribes to the state stream from the backend.
-   As messages complete, they are printed to `stdout` as indented JSON.
-   **Important**: Because it uses `MarshalIndent`, a single "activity packet" spans multiple lines.
-   **Framing**: A packet starts with `{` alone on a line and ends with `}` alone on a line.

## PTY Handling

Cline checks for TTY presence in multiple places (`isTTY()` in `pkg/cli/display/utils.go` - though I didn't read that specific file, it's referenced by logic in `segment_streamer.go`).
-   If no PTY is allocated, `rich` mode behaves more like `plain`.
-   Interactive elements (like `huh` forms) require a TTY.
-   `oneshot` currently invokes Cline via `subprocess.Popen` without a PTY, which works for non-interactive modes (`--yolo`, `--oneshot`) but may affect the formatting of "rich" output if that was selected.

## Internal Activity Structure

Cline's internal messages (`ClineMessage` in `pkg/cli/types`) have several key fields:
-   `type`: `say` or `ask`
-   `say`: specific type of say event (e.g., `text`, `command`, `tool`, `completion_result`)
-   `ask`: specific type of ask event (e.g., `tool`, `command`, `followup`)
-   `text`: the main content body
-   `partial`: boolean indicating if the message is still streaming (usually suppressed in JSON output until complete)
-   `timestamp`: millisecond Unix timestamp

## Recovery Mechanism

Cline provides a robust recovery path:
1.  **Filesystem**: Task state is stored in `~/.cline/tasks/{task_id}/ui_messages.json`.
2.  **CLI**: `cline task view [task-id]` can snapshot the conversation.
3.  **Oneshot Recovery**: `ClineExecutor.recover()` reads `ui_messages.json` directly to salvage activity from interrupted sessions.

## Recommendations for Unified Schema

-   Cline's `say` and `ask` types map well to a unified activity schema.
-   The indented JSON output requires the line-buffered "framed" extractor already implemented in `oneshot.pipeline`.
-   PTY allocation is not strictly required for JSON output but might be useful for capturing "real" terminal output from commands Cline runs.

## Test Commands

```bash
# JSON Stream
cline --oneshot --yolo --output-format json "hello"

# Plain Text
cline --oneshot --yolo --output-format plain "hello"
```
