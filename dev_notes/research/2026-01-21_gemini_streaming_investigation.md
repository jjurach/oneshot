# Gemini Streaming & API Integration Research

**Status:** COMPLETED
**Date:** 2026-01-21
**Project Plan Step:** 4

## Overview

Google Gemini (via CLI or API) supports structured output and streaming. The `gemini` CLI used by `oneshot` implements a `stream-json` mode that simplifies integration.

## Output Mechanisms

### 1. `stream-json` (CLI)
The Gemini CLI emits NDJSON (one JSON object per line) when invoked with `--output-format stream-json`.
-   **Events**:
    -   `init`: Session metadata.
    -   `message`: Content chunks (deltas) from the model.
    -   `result`: Final usage stats and completion status.
-   **Partial JSON**: For structured output, Gemini streams chunks of the JSON string. The consumer is responsible for accumulating these chunks until a complete JSON object can be parsed.

### 2. API Streaming (`streamGenerateContent`)
The raw API returns a stream of `GenerateContentResponse` objects via SSE.
-   **Tool Use**: Tool calls (Function Calling) are delivered as structured `functionCall` objects within the stream.
-   **Reassembly**: Assistant text is delivered in parts. If the model is outputting a JSON schema, each chunk is a partial string of that JSON.

## Preamble & Info Lines

The Gemini CLI prints informational messages (e.g., "YOLO mode enabled", "Using cached credentials") to `stdout` before the JSON stream begins.
-   **Handling**: `oneshot`'s new pipeline correctly identifies these as preamble strings and avoids parsing them as JSON.

## Recommendations for Unified Schema

-   **Message Aggregation**: For `gemini` provider, `oneshot` should aggregate `message` type events into a single conversational turn in the activity log.
-   **Tool Mapping**: Gemini's `functionCall` maps directly to `tool_use` in the unified schema.
-   **Usage Stats**: Capture `input_tokens`, `output_tokens`, and `duration_ms` from the `result` event for cost/performance analysis.

## Test Commands

```bash
# Gemini CLI with NDJSON stream
gemini --prompt "write a story" --output-format stream-json --yolo
```
