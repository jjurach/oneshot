# Unified Streaming JSON Schema Specification

**Status:** PROPOSED
**Date:** 2026-01-21
**Project Plan Step:** 5

## Objective

Define a common NDJSON schema for `oneshot` activity logging that harmonizes output from all executors (Cline, Claude, Aider, Gemini) into a single, predictable format for UI rendering and post-execution analysis.

## The "Oneshot Activity" Packet

Each line in the `<id>-oneshot-log.json` file MUST be a valid JSON object following this structure.

### Root Structure

| Field | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `float` | Unix timestamp (seconds since epoch) when `oneshot` received the event. |
| `ts_ms` | `int` | Milliseconds since epoch (for higher precision sorting). |
| `executor` | `string` | The provider ID (`cline`, `claude`, `aider`, `gemini`, `direct`). |
| `oneshot_id`| `string` | The unique ID of the oneshot session. |
| `type` | `string` | High-level event category (see below). |
| `data` | `object\|string` | Event-specific payload. |
| `is_heartbeat`| `bool` | `true` if this is a synthetic heartbeat for inactivity monitoring. |

---

### Event Types (`type`)

#### 1. `preamble`
Text output from the executor *before* structured activity starts.
-   **Data**: The raw string content.
-   **Usage**: Display as-is in the console/UI.

#### 2. `thought`
Internal reasoning or "thinking" output from the model.
-   **Data**: `{ "text": "..." }`
-   **Providers**: Claude (`thinking`), Cline (`say:reasoning`), Aider (conversational text).

#### 3. `message`
A conversational message to the user.
-   **Data**: `{ "role": "assistant|user", "content": "..." }`
-   **Providers**: Gemini (`message`), Cline (`say:text`), Aider (output).

#### 4. `tool_use`
Indicates the agent is invoking an external tool.
-   **Data**: `{ "tool": "bash|edit|read", "command": "...", "reason": "..." }`
-   **Providers**: Cline (`ask:command`, `ask:tool`), Claude (`tool_use`), Gemini (`functionCall`).

#### 5. `tool_output`
The result/output of a tool execution.
-   **Data**: `{ "tool": "...", "content": "...", "exit_code": 0 }`
-   **Providers**: Cline (`say:command_output`), Claude (`tool_result`), Aider (git commits/file edits).

#### 6. `completion`
Final result and status of the task.
-   **Data**: `{ "status": "success|failure", "result": "...", "stats": { ... } }`
-   **Providers**: All (summarized from final output or specific events).

---

## Mapping Example: Cline to Unified

**Original Cline Output:**
```json
{
  "say": "command",
  "text": "ls -l",
  "ts": 1768954851123
}
```

**Unified Oneshot Activity:**
```json
{
  "timestamp": 1768954851.123,
  "ts_ms": 1768954851123,
  "executor": "cline",
  "oneshot_id": "task-456",
  "type": "tool_use",
  "data": {
    "tool": "bash",
    "command": "ls -l"
  },
  "is_heartbeat": false
}
```

## Implementation Strategy

1.  **Executor-Specific Translators**: Each `BaseExecutor` subclass will implement a `translate_to_unified(raw_event)` method.
2.  **Pipeline Integration**: The `parse_activity` stage in `src/oneshot/pipeline.py` will use these translators to wrap raw output into the unified schema before logging.
3.  **UI Resilience**: The TUI and Web UI will consume this unified schema, ensuring consistent rendering regardless of the underlying provider.
