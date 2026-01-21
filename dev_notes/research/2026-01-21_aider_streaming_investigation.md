# Aider Streaming & Logging Capabilities Research

**Status:** COMPLETED
**Date:** 2026-01-21
**Project Plan Step:** 2

## Overview

Aider is a terminal-based AI coding assistant. Unlike Cline, it does not currently provide a native JSON-streaming mode. Its primary interaction model is through the terminal, supplemented by persistent history files and git commits.

## Output Mechanisms

### 1. Terminal Output (Stdout/Stderr)
Aider prints its reasoning, file change summaries, and git commit messages to the terminal.
-   **Streaming**: Enabled by default (`--stream`). It uses ANSI codes for styling.
-   **Structured Data**: No native JSON stream.
-   **Parsing Strategy**: Capture `stdout` and look for key phrases like "Committed <hash>", "Edited <file>", or the final success message.

### 2. `.aider.chat.history.md`
Aider maintains a real-time markdown log of the conversation in the repository root.
-   **Format**: Markdown.
-   **Updates**: Append-only during the session.
-   **Use Case**: Excellent for recovery or side-channel monitoring if the stdout stream is interrupted.

### 3. `--llm-history-file`
Aider can log raw LLM interactions to a file.
-   **Format**: "USER: ... ASSISTANT: ..." text format.
-   **Use Case**: Forensic analysis of the raw model output, but less useful for structured activity tracking than the terminal output.

## Git Integration

Aider's most reliable "structured" output is the git history itself.
-   **Commits**: Aider automatically commits changes with descriptive messages (unless `--no-auto-commits` is used).
-   **Tracking**: `oneshot` should monitor the git log to verify completion and capture work evidence.

## Recommendations for Unified Schema

-   **Activity Extraction**: Use a regex-based parser on the Aider terminal stream to extract:
    -   `thinking`: Captured from Aider's conversational text.
    -   `file_operation`: Captured from "Edited...", "Created..." lines.
    -   `git_commit`: Captured from "Committed <hash>" lines.
-   **Streaming Implementation**: Switch `AiderExecutor` from `--no-stream` to `--stream` to allow real-time "thinking" updates in the `oneshot` activity log.
-   **Preamble**: Aider's startup text (model info, git status) should be treated as preamble strings.

## Test Commands

```bash
# Standard execution with streaming
aider --message "refactor main.py" --stream --yes-always --exit
```
