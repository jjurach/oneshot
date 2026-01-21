# Cross-Provider Streaming Analysis & Recommendations

**Status:** COMPLETED
**Date:** 2026-01-21
**Project Plan Step:** 6

## Executive Summary

The research phase (Steps 1-4) confirms that while each provider has unique output patterns, they all fall into two main categories: **Structured JSON Streamers** (Cline, Claude, Gemini) and **Text/Markdown Loggers** (Aider). The proposed **Unified Streaming JSON Schema** (Step 5) provides a robust framework to harmonize these differences into a single, predictable activity log.

## Provider Comparison Matrix

| Feature | Cline | Claude | Gemini | Aider |
| :--- | :--- | :--- | :--- | :--- |
| **Native JSON Stream** | Yes (Indented) | Yes (NDJSON) | Yes (NDJSON) | No (Text/MD) |
| **Thinking/Reasoning** | Yes (`say:reasoning`) | Yes (`thinking`) | Indirectly | Yes (Conversational) |
| **Tool Use Format** | `ask` events | `tool_use` events | `functionCall` | Text patterns |
| **PTY Required** | Recommended | Recommended | No | No |
| **Main Log Source** | gRPC/Stdout | Stdout (SSE) | Stdout (NDJSON) | Stdout/`.aider.chat.history.md` |

## Key Findings

1.  **Framing Consistency**: Cline is the only provider that outputs indented JSON by default, which requires multi-line framing logic ( `{` ... `}` ). All other JSON streamers use single-line NDJSON.
2.  **Preamble Noise**: All providers emit informational "noise" at startup (version info, model selection, etc.). The `oneshot` pipeline MUST treat everything before the first valid JSON as a `preamble` event.
3.  **Real-time vs. Atomic**: Aider is currently configured with `--no-stream`, which hides its "thinking" phase. Switching to `--stream` is critical for high-fidelity activity logging.
4.  **Deduplication**: Cline's internal message tracking can lead to duplicate events in the stream if not handled carefully (though `oneshot`'s pipeline currently logs what it receives).

## Recommendations for Phase 3 Implementation

### 1. Executor Refactoring
-   Implement a `map_to_unified()` method in each `BaseExecutor`.
-   Migrate parsing logic from `parse_streaming_activity` (which often handles the whole block) to a per-event mapping function that works within the streaming pipeline.

### 2. Pipeline Enhancements
-   The current `oneshot.pipeline` is now robust enough to handle the framing.
-   Add a `Sequencer` stage to the pipeline to add `sequence_number` to events, ensuring order is preserved even if timestamps are identical.

### 3. PTY Standardization
-   Encapsulate PTY allocation into a reusable utility for `ClaudeExecutor` and `ClineExecutor`.
-   Ensure PTYs are correctly cleaned up on session termination to avoid zombie processes.

### 4. Recovery Parity
-   Standardize the `RecoveryResult` format to use the Unified Schema.
-   Ensure Aider's recovery uses both `.aider.chat.history.md` and the git log for a complete picture.

## Phase 3 Roadmap Outline

1.  **Shared Utilities**: Create PTY and Sequencer helpers.
2.  **Translator Implementation**: Build mapping logic for each provider.
3.  **Pipeline Integration**: Plug translators into the main engine loop.
4.  **Verification**: Cross-executor test suite using the Unified Schema as the oracle.
