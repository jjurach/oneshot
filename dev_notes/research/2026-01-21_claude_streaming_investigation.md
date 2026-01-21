# Claude Streaming Capabilities Research

**Status:** COMPLETED
**Date:** 2026-01-21
**Project Plan Step:** 3

## Overview

Claude Code (Anthropic's CLI) provides a native NDJSON streaming mode via `--output-format stream-json`. This is highly compatible with the `oneshot` pipeline.

## Output Mechanisms

### 1. `stream-json` (NDJSON)
When using `--output-format stream-json`, Claude emits one JSON object per line.
-   **Structure**: Each object contains fields like `type`, `say`, `ask`, and `text`.
-   **Partial Messages**: Can include partial streaming if `--include-partial-messages` is used.
-   **Framing**: Unlike Cline's indented JSON, Claude's `stream-json` is typically one object per line (NDJSON), making it even easier to parse.

### 2. Preamble & Verbose Info
Claude's `--verbose` flag adds more metadata to the stream.
-   **Content**: System info, model versions, and session IDs.
-   **Handling**: These should be treated as preamble strings if they appear before the first JSON object.

## PTY & Interactivity

While `stream-json` doesn't require a PTY, the Claude CLI itself often prefers one for handling tool interactions and ANSI styling.
-   **Recommendation**: Continue using PTY for Claude to ensure all tool outputs are captured as they would be in a real terminal.
-   **Flags**: Use `-p` (print) for non-interactive execution.

## Recommendations for Unified Schema

-   Claude's `stream-json` is very similar to Cline's event model. They can share a common set of `activity_type` mappings.
-   Key event types to capture:
    -   `message`: Assistant text output.
    -   `tool_use`: Calls to external tools (bash, edit, etc.).
    -   `tool_result`: Output from those tools.
    -   `completion`: Final summary and status.

## Test Commands

```bash
# Non-interactive NDJSON stream
claude -p --output-format stream-json "list files"
```
