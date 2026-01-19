# Research: Streaming JSON Format Analysis for Cross-Provider Executors

## Objective

Analyze existing JSON output files to understand streaming JSON format requirements and identify errors in the current streaming and JSON serialization implementation across different executor providers.

## Current State Analysis

### Existing JSON Output Files Analyzed

Found 15 JSON output files across the oneshot directory:
- 9 NDJSON log files (claude-code session logs)
- 6 structured JSON output files (oneshot execution results)

### File Structure

The current structured JSON output follows this pattern:

```json
{
  "metadata": {
    "timestamp": "ISO-8601 timestamp",
    "prompt": "user input prompt",
    "worker_provider": "executor",
    "worker_executor": "claude|cline|aider|gemini",
    "worker_model": null,
    "auditor_provider": "executor",
    "auditor_executor": "claude|cline|aider|gemini",
    "auditor_model": null,
    "max_iterations": 5,
    "working_directory": "/path/to/working/dir"
  },
  "iterations": [
    {
      "iteration": 1,
      "worker_output": "string with activity summary"
    }
  ]
}
```

### Errors Found in Current Implementation

#### 1. **Truncated Activity Summaries**
- **Issue**: Worker output contains truncated error messages and activity descriptions
- **Example**: `"Error: <module 'oneshot.providers' from '/home/phaedrus/AiSpace/oneshot/src/oneshot/providers/__i..."`
- **Impact**: Full error context is lost, making debugging difficult
- **Root Cause**: Activity formatter truncates long error messages without preserving complete information

#### 2. **Incomplete Error Messages in Activity Output**
- **Issue**: Error activities are cut off mid-sentence
- **Example**: In 2026-01-19_14-36-36_oneshot.json iteration 4: `"Error: asse"` (incomplete assertion error)
- **Impact**: Exact error types cannot be determined
- **Root Cause**: String truncation logic in activity formatter or activity interpreter

#### 3. **Missing Full Event Metadata in Streaming**
- **Issue**: Current JSON only includes `iteration` number and `worker_output`, lacking per-event streaming information
- **Missing Fields**:
  - Event timestamps (within iteration)
  - Event types (tool_call, error, planning, etc.) as separate structured fields
  - Event sequence numbers for ordering
  - Detailed payload for each activity
- **Impact**: Cannot perform real-time streaming analysis or rebuild execution timeline
- **Root Cause**: Current implementation aggregates all activities into a single formatted string rather than streaming individual JSON events

#### 4. **Provider-Specific Output Inconsistency**
- **Issue**: Different executors (claude, cline) may produce different output formats
- **Example**: Some files show activity emoji summaries, others show different formatting
- **Impact**: Consumers cannot rely on consistent structure across providers
- **Root Cause**: Activity formatter not enforced across all provider implementations

### Current Activity Summary Format

The existing output uses:
- Emoji-based activity classification (🔧 Tool Call, 📄 File Operation, 💭 Thinking, 📋 Planning, ❌ Error)
- Aggregated counts per event type
- Key activities list with truncation
- Human-readable but not machine-parseable structure

Example from file:
```
🤖 AI Activity Summary (65 events):
  🔧 Tool Call: 3
  📄 File Operation: 60
  📋 Planning: 2

📝 Key Activities:
  • Tool call: bash -c \"git status\"...
  • File operation: src/new_feature.py
  • ... and 62 more activities
```

## Recommendations for Streaming JSON Implementation

### 1. Define Unified Streaming Event Format

```json
{
  "type": "activity_event",
  "timestamp": "2026-01-19T15:06:12.399056",
  "sequence": 1,
  "provider": "claude",
  "iteration": 1,
  "event": {
    "type": "tool_call|error|planning|file_operation|thinking",
    "description": "Full, untruncated description",
    "metadata": {
      "tool_name": "bash",
      "command": "git status",
      "exit_code": 0
    }
  }
}
```

### 2. Implement Per-Event Streaming

- Emit individual JSON objects for each activity instead of aggregating into a summary
- Each event includes full context without truncation
- Maintain event sequence for reconstruction

### 3. Add Streaming Output Format Support

- `--output-format stream-json`: Emit JSONL (JSON Lines) with individual events
- `--output-format aggregated-json`: Keep current format for compatibility
- `--output-format human`: Current human-readable format

### 4. Fix Truncation Issues

- Store full error messages and descriptions
- Implement proper string escaping for JSON
- Use structured fields instead of formatted strings where possible

## Test Case: "What is the capital of Australia?"

This simple query should:
1. Generate a response from each executor (Claude, Cline, Aider, Gemini)
2. Produce consistent JSON output structure across all providers
3. Include complete, untruncated error information (if any errors occur)
4. Allow real-time streaming of events during execution

Expected response: "Canberra" (or similar variation)

### Streaming Events Expected

For a simple query like "what is the capital of australia?":
1. **query_received** - Query is received
2. **execution_started** - Executor begins processing
3. **thinking** - Model thinking process (if applicable)
4. **tool_call** - Any tool calls made (likely none for this simple query)
5. **response_generated** - Response is being generated
6. **response_completed** - Response complete
7. **execution_completed** - Executor finished

Each event should be fully structured JSON, not formatted strings.

## Files to Analyze for Errors

### Examined Files
- `/home/phaedrus/AiSpace/oneshot/2026-01-19_14-36-36_oneshot.json` - Contains 4 iterations with errors
- `/home/phaedrus/AiSpace/oneshot/2026-01-19_14-58-17_oneshot.json` - Contains 3 iterations with errors
- `/home/phaedrus/AiSpace/oneshot/2026-01-19_15-06-12_oneshot.json` - Empty iterations (just completed)

### Error Patterns Identified

1. **Truncated error objects**: `<module 'oneshot.providers' from '/home/phaedrus/AiSpace/oneshot/src/oneshot/providers/__i...`
2. **Incomplete assertions**: `Error: asse` (likely "AssertionError")
3. **Lost exception context**: Original error type/message not recoverable

## Implementation Priorities

### Phase 1: Error Diagnosis
1. ✅ Identify truncation points in activity formatter
2. ✅ Map error message sources
3. Create debug output to capture full error information

### Phase 2: Unified Event Schema
1. Define complete JSON schema for streaming events
2. Implement event factory pattern
3. Create schema validation

### Phase 3: Provider Integration
1. Update each executor to emit streaming events
2. Implement JSONL output format
3. Add CLI flag support

### Phase 4: Testing & Validation
1. Test "capital of australia" across all executors
2. Verify complete error capture
3. Validate JSON schema compliance

## Next Steps

1. Review `activity_formatter.py` for truncation logic
2. Review `activity_interpreter.py` for event processing
3. Create detailed streaming event schema document
4. Implement per-event JSON emission in executors
