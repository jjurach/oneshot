# Project Plan: Streaming JSON Output Format and Multi-Provider Investigation

## Objective

Investigate and implement `--output-format stream-json` capability across Cline and other supported providers (Claude, Aider), including pseudo-terminal (PTY) allocation optimization, to enable real-time JSON-formatted streaming of executor activity and conversation history. This includes researching Aider's local filesystem logging and establishing a unified streaming and interpretation framework.

## Current State Analysis

### What Already Exists

1. **Activity System** (`activity_interpreter.py`, `activity_formatter.py`)
   - Extracts meaningful activity patterns from executor output
   - Filters sensitive metadata (tokens, costs, usage)
   - Formats activities for display

2. **Provider Executors**
   - Claude executor: Uses subprocess with PTY streaming
   - Cline executor: VSCode extension integration (CLI invocation)
   - Aider executor: CLI-based with `.aider.chat.history.md` storage
   - Gemini executor: Direct CLI invocation

3. **Executor Infrastructure** (`providers/__init__.py`)
   - `call_executor()` and `call_executor_async()` functions
   - PTY allocation (enabled by default)
   - Streaming output capture
   - Event emission system

4. **Aider Chat History**
   - **Primary**: `.aider.chat.history.md` (conversation log)
   - **LLM History**: `.aider.llm.history` (LLM conversation via environment variable `AIDER_LLM_HISTORY_FILE`)
   - **Input History**: `.aider.input.history` (user input history)
   - All stored in current working directory by default
   - Configuration via environment variables and YAML config

### What's Missing

1. **Stream JSON Output Format**
   - No `--output-format stream-json` implementation for any executor
   - No unified JSON output schema for streaming activity
   - No per-executor JSON streaming capability

2. **Cline Streaming Investigation**
   - Need to understand Cline's `--output-format` options
   - Need to determine if PTY affects JSON output quality
   - Need to test streaming JSON parsing robustness

3. **PTY Allocation Optimization**
   - Current: PTY enabled by default, no configuration options
   - Missing: Conditional PTY based on output format requested
   - Missing: Performance impact analysis (PTY vs pipe)

4. **Aider Streaming Capability**
   - Aider currently runs with `--no-stream` flag
   - Conversation stored in `.md` file, not streamed real-time
   - Need to: Enable streaming, parse output in real-time, extract activities

5. **Cross-Provider Streaming Framework**
   - No unified interface for streaming JSON across providers
   - Each provider has different output formats and streaming capabilities
   - Missing adapter pattern for normalizing outputs

## Implementation Steps

### Phase 1: Research & Investigation (Non-Breaking)

#### Step 1.1: Investigate Cline Stream JSON Output Format
- **Goal**: Understand Cline's `--output-format stream-json` capability
- **Tasks**:
  - Research Cline documentation and help text: `cline --help`
  - Test `cline` with `--output-format stream-json` flag
  - Analyze JSON output schema (structure, fields, nesting)
  - Determine if streaming is continuous or chunked
  - Identify any dependencies on model or configuration
  - Document schema with examples
  - Test interaction with PTY allocation (does JSON remain valid with PTY?)
  - Test without PTY (pipe output) - is JSON cleaner?
- **Files to Create**:
  - `dev_notes/research/cline_stream_json_analysis.md` - findings and schema documentation
  - Test script: `scripts/test_cline_stream_json.sh`

#### Step 1.2: Investigate Cline PTY Allocation Impact
- **Goal**: Determine optimal PTY configuration for JSON output
- **Tasks**:
  - Compare output with PTY enabled vs disabled
  - Measure ANSI escape codes in PTY output
  - Test JSON parsing robustness on both modes
  - Measure performance impact (latency, CPU, memory)
  - Document recommendations
- **Files to Create**:
  - `dev_notes/research/pty_allocation_impact_analysis.md`
  - Test script: `scripts/test_pty_configurations.sh`

#### Step 1.3: Investigate Aider Streaming Capability
- **Goal**: Understand Aider's streaming options and real-time output capability
- **Tasks**:
  - Research Aider streaming options (remove `--no-stream` flag)
  - Test Aider with `--stream` enabled
  - Analyze Aider's real-time output format during execution
  - Document `.aider.chat.history.md` file format and update frequency
  - Research `AIDER_LLM_HISTORY_FILE` functionality
  - Test if history files are updated in real-time during execution
  - Determine optimal polling/monitoring strategy for history files
  - Document all findings with examples
- **Files to Create**:
  - `dev_notes/research/aider_streaming_analysis.md` - formats, capabilities, limitations
  - Test script: `scripts/test_aider_streaming.sh`

#### Step 1.4: Research Aider History File Monitoring
- **Goal**: Establish strategy for reading Aider's conversation history
- **Tasks**:
  - Document location: `$CWD/.aider.chat.history.md` (default)
  - Document format: Markdown with timestamp and speaker markers
  - Implement file watcher/poller to detect updates
  - Test real-time reading during active Aider session
  - Determine read strategy: polling interval, file position tracking, or inotify
  - Test concurrent access (Aider writing while monitoring)
  - Document recommended monitoring approach
  - Create proof-of-concept monitor script
- **Files to Create**:
  - `dev_notes/research/aider_history_monitoring_poc.md`
  - `scripts/monitor_aider_history.py` - proof-of-concept file monitor
  - Test data: `test_data/aider_history_example.md`

#### Step 1.5: Investigate Claude and Gemini Streaming
- **Goal**: Understand streaming capabilities for Claude and Gemini executors
- **Tasks**:
  - Document current Claude streaming implementation
  - Research Claude's `--output-format` options (if available)
  - Test Gemini executor streaming capability
  - Document what JSON output schema would be appropriate for each
  - Identify any provider-specific limitations
- **Files to Create**:
  - `dev_notes/research/provider_streaming_comparison.md`

#### Step 1.6: Design Unified Stream JSON Schema
- **Goal**: Create specification for JSON streaming output across all providers
- **Tasks**:
  - Analyze existing activity system JSON structure
  - Define unified schema covering:
    - Streaming events (start, chunk, tool_call, file_operation, error, complete)
    - Timestamp and sequence information
    - Provider/executor identification
    - Activity details and metadata
    - Error information with context
  - Design for extensibility (new provider, new activity types)
  - Create TypeScript/Pydantic validation models
  - Create JSON schema document with examples
  - Validate against existing activity system
- **Files to Create**:
  - `dev_notes/research/unified_stream_json_schema.md`
  - `api/stream-json-schema.json` (JSON Schema definition)
  - Test schema validations

### Phase 2: Implementation (With Approval)

#### Step 2.1: Implement Stream JSON Output for Cline
- **Goal**: Add `--output-format stream-json` support to Cline executor
- **Tasks**:
  - Create `CloneStreamJsonAdapter` class to wrap Cline execution
  - Modify `providers/__init__.py` to detect `output_format=stream-json` parameter
  - Implement PTY configuration based on output format (disable PTY for JSON)
  - Add JSON streaming output handler
  - Transform Cline JSON output to unified schema
  - Add real-time event emission
  - Implement error handling for malformed JSON
  - Add comprehensive logging
- **Files to Modify**:
  - `src/oneshot/providers/__init__.py` - add stream JSON handling
  - `src/oneshot/oneshot.py` - add output_format parameter to call_executor
- **Files to Create**:
  - `src/oneshot/providers/stream_json_adapter.py` - unified JSON output handler
  - `src/oneshot/providers/cline_stream_json.py` - Cline-specific implementation

#### Step 2.2: Implement Stream JSON Output for Aider
- **Goal**: Add real-time streaming JSON support to Aider executor
- **Tasks**:
  - Create `AiderStreamJsonAdapter` class
  - Modify AiderExecutor to run Aider with `--stream` enabled (configurable)
  - Implement `.aider.chat.history.md` file monitoring during execution
  - Implement real-time history file parsing and event emission
  - Transform Aider output to unified JSON schema
  - Handle concurrent file writes during parsing
  - Implement cleanup of history files (optional, configurable)
  - Add retry logic for file access
- **Files to Modify**:
  - `src/oneshot/providers/aider_executor.py` - add streaming support
  - `src/oneshot/providers/__init__.py` - add Aider stream JSON handling
- **Files to Create**:
  - `src/oneshot/providers/aider_stream_json.py` - Aider-specific implementation
  - `src/oneshot/providers/history_file_monitor.py` - file watching utility

#### Step 2.3: Implement Stream JSON Output for Claude
- **Goal**: Add `--output-format stream-json` support to Claude executor
- **Tasks**:
  - Create `ClaudeStreamJsonAdapter` class
  - Modify Claude execution to detect and respond to output format
  - Optimize PTY usage (disable for JSON output)
  - Implement real-time event emission
  - Transform Claude output to unified JSON schema
  - Add JSON parsing validation
  - Add performance metrics collection
- **Files to Modify**:
  - `src/oneshot/providers/__init__.py`
  - Claude executor wrapper
- **Files to Create**:
  - `src/oneshot/providers/claude_stream_json.py`

#### Step 2.4: Create Stream JSON Configuration and Options
- **Goal**: Allow users to enable stream JSON output
- **Tasks**:
  - Add `--output-format` CLI parameter to main oneshot command
  - Support options: `text` (default), `json`, `stream-json`
  - Add environment variable support: `ONESHOT_OUTPUT_FORMAT`
  - Add configuration file support in `.oneshort.yaml`
  - Create validation for valid output format options
  - Update help documentation
- **Files to Modify**:
  - `src/oneshot/oneshot.py` - add output_format parameter
  - `src/oneshot/cli.py` or main entry point
  - Configuration parsing module

#### Step 2.5: Optimize PTY Allocation
- **Goal**: Make PTY allocation conditional and configurable
- **Tasks**:
  - Create `PTYConfig` dataclass with allocation strategy
  - Modify `call_executor()` to accept PTY configuration
  - Implement logic: disable PTY when output_format != 'text'
  - Add `--pty` CLI flag to allow override
  - Add `--no-pty` flag to disable PTY
  - Add metrics collection (execution time, memory) for PTY vs no-PTY
  - Document performance implications
- **Files to Modify**:
  - `src/oneshot/oneshot.py` - call_executor functions
  - `src/oneshot/providers/__init__.py`

#### Step 2.6: Implement Unified Stream JSON Adapter
- **Goal**: Create abstraction layer for provider-agnostic JSON streaming
- **Tasks**:
  - Create `StreamJsonProvider` base class
  - Implement standardized event emission interface
  - Create event router/dispatcher for different activity types
  - Add JSON validation against schema
  - Implement streaming output writer (stdout, file, webhook)
  - Add buffering and batching options
  - Create error recovery mechanism
- **Files to Create**:
  - `src/oneshot/providers/stream_json_adapter.py` - core abstraction
  - `src/oneshot/stream_json_output.py` - JSON output handlers

#### Step 2.7: Add Stream JSON Support to CLI and Web UI
- **Goal**: Integrate stream JSON output into CLI and Web interfaces
- **Tasks**:
  - Modify CLI output handler to parse and display stream JSON
  - Update Web UI to stream JSON events via WebSocket
  - Create formatted output for stream JSON in terminal
  - Add filtering options (by activity type, severity)
  - Create progress indicator for streaming
  - Add real-time stats dashboard option
  - Test with actual provider streams
- **Files to Modify**:
  - `src/oneshot/cli.py` - add JSON output formatting
  - `src/oneshot/web_ui.py` - add WebSocket streaming
  - `src/oneshot/tui.py` - add activity stream display

### Phase 3: Testing & Documentation

#### Step 3.1: Unit Tests for Stream JSON Adapters
- **Goal**: Comprehensive testing of each adapter
- **Tasks**:
  - Create test fixtures for each provider's JSON format
  - Test schema validation for all activity types
  - Test error handling (malformed JSON, missing fields, timeouts)
  - Test concurrent file access (Aider history)
  - Test event emission and ordering
  - Test filtering and transformation logic
- **Files to Create**:
  - `tests/test_cline_stream_json.py`
  - `tests/test_aider_stream_json.py`
  - `tests/test_claude_stream_json.py`
  - `tests/test_stream_json_adapter.py`
  - `tests/fixtures/stream_json_examples/` - test data

#### Step 3.2: Integration Tests
- **Goal**: Test full end-to-end streaming workflow
- **Tasks**:
  - Test stream JSON with actual providers (mock if unavailable)
  - Test CLI with `--output-format stream-json`
  - Test Web UI streaming
  - Test cross-provider consistency
  - Test error scenarios (executor crash, file corruption)
  - Test performance under load
- **Files to Create**:
  - `tests/test_stream_json_integration.py`
  - `tests/test_stream_json_cli.py`

#### Step 3.3: Manual Testing & Documentation
- **Goal**: Verify real-world functionality
- **Tasks**:
  - Test each provider manually with stream JSON output
  - Create usage examples and documentation
  - Document JSON output examples for each provider
  - Create troubleshooting guide
  - Document performance characteristics
  - Create migration guide from old output format
- **Files to Create**:
  - `docs/stream_json_usage.md`
  - `docs/stream_json_schema_reference.md`
  - `examples/stream_json_output_examples.md`
  - `docs/provider_specific_streaming_notes.md`

#### Step 3.4: Update Project Documentation
- **Goal**: Document all new features and capabilities
- **Tasks**:
  - Update README with stream JSON examples
  - Add stream JSON configuration to configuration guide
  - Update architecture documentation
  - Create troubleshooting section
  - Document provider differences and limitations
- **Files to Modify**:
  - `README.md`
  - `docs/architecture.md`
  - `docs/configuration.md`

## Success Criteria

1. ✅ **Research Complete**: All Phase 1 investigation documents completed and reviewed
   - Cline stream JSON capabilities documented
   - Aider streaming options researched
   - PTY impact analyzed
   - Unified schema designed

2. ✅ **Cline Stream JSON**: `cline` executor supports `--output-format stream-json`
   - Output validated against unified schema
   - Real-time event emission working
   - JSON remains valid with/without PTY

3. ✅ **Aider Stream JSON**: Aider history files monitored and streamed as JSON
   - `.aider.chat.history.md` monitored in real-time
   - History parsed and transformed to unified schema
   - Events emitted as activities occur

4. ✅ **Claude Stream JSON**: Claude executor supports `--output-format stream-json`
   - Output follows unified schema
   - Real-time streaming functional

5. ✅ **PTY Optimization**: PTY allocation configurable based on output format
   - JSON output uses pipe (no PTY) by default
   - `--pty` flag can override behavior
   - Performance improvements measurable

6. ✅ **Unified Schema**: All providers output consistent JSON structure
   - Schema validated with examples from each provider
   - Extensible for future providers
   - Documented with JSON Schema

7. ✅ **CLI & Web UI**: Stream JSON output integrated
   - CLI displays formatted stream JSON output
   - Web UI streams JSON via WebSocket
   - Filtering and stats available

8. ✅ **Tests Passing**: All unit and integration tests pass
   - 90%+ coverage of new code
   - Real-world examples tested
   - Error scenarios handled

9. ✅ **Documentation Complete**: Usage and troubleshooting guides available
   - Examples for each provider
   - Configuration documentation
   - Troubleshooting guide

## Testing Strategy

### Unit Testing
- Test each adapter in isolation with mock provider output
- Test schema validation against unified schema
- Test JSON parsing and error handling
- Test file monitoring (Aider history)
- Run with `pytest` for all new modules

### Integration Testing
- Test full flow from CLI to output
- Test with multiple providers sequentially
- Test error recovery
- Test performance with large outputs
- Validate output against JSON schema

### Manual Testing
- Execute commands with each provider
- Verify stream JSON output in real-time
- Test Web UI display
- Test CLI formatting
- Observe performance characteristics

### Regression Testing
- Ensure existing text output format unchanged
- Verify backward compatibility
- Test with existing scripts and tools
- Validate no breaking changes to APIs

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Cline doesn't support stream-json format | Medium | High | Alternative: implement custom JSON wrapper around text output |
| Aider file locking during write | Medium | Medium | Use file locking library, retry logic, fallback to polling |
| PTY affects JSON validity | Low | High | Comprehensive testing, document findings |
| Schema incompatible with future providers | Low | Medium | Design schema for extensibility, create provider-specific fields |
| Performance degradation from monitoring | Medium | Medium | Use efficient file monitoring (inotify), batch events |
| Breaking changes to API | Low | High | Maintain backward compatibility, use feature flags |
| Concurrent file access issues | Low | Medium | Implement proper synchronization, error recovery |

## Architecture Notes

### Data Flow - Stream JSON
```
Provider (Cline/Aider/Claude) execution
    ↓
[Provider-specific streaming capture]
    ↓
[Parse/interpret provider output]
    ↓
[Transform to unified JSON schema]
    ↓
[Emit EXECUTOR_STREAM_JSON events]
    ↓
[CLI/Web UI format and display]
    ↓
[User sees real-time JSON activity stream]
```

### Unified Stream JSON Event Schema
```json
{
  "type": "executor_stream",
  "version": "1.0",
  "timestamp": "2026-01-19T10:48:49Z",
  "executor": "cline|aider|claude|gemini",
  "task_id": "task-123",
  "event": {
    "id": "evt-456",
    "sequence": 42,
    "activity_type": "tool_call|file_operation|reasoning|error|start|complete",
    "description": "Human-readable activity description",
    "details": {
      "tool_name": "optional tool name",
      "file_path": "optional file path",
      "status": "in_progress|success|failed",
      "error": "optional error message"
    },
    "duration_ms": 1234
  },
  "metadata": {
    "provider_version": "1.2.3",
    "model": "claude-3-sonnet",
    "custom_field": "provider-specific data"
  }
}
```

### Provider-Specific Implementation Details

#### Cline
- Flag: `--output-format stream-json`
- Output: Continuous JSON stream (one JSON object per line)
- PTY: Disable for JSON (use pipes)
- Integration: Parse stream, emit events, validate schema

#### Aider
- Streaming: Remove `--no-stream` flag
- History: Monitor `.aider.chat.history.md` file
- Strategy: File watching + real-time parsing
- Format: Convert markdown history to JSON events
- Cleanup: Remove history files after processing (optional)

#### Claude
- Detection: Check for `--output-format` support
- Fallback: Custom JSON wrapping of text output if needed
- PTY: Optimize based on output format
- Schema: Map to unified format

## Implementation Priority

1. Phase 1 Research (all steps) - Establish foundation
2. Phase 2.1 - Cline Stream JSON (most critical)
3. Phase 2.4 - CLI Configuration (enables user access)
4. Phase 2.2 - Aider Stream JSON (leverages research)
5. Phase 2.3 - Claude Stream JSON (consistency)
6. Phase 2.5 - PTY Optimization (performance)
7. Phase 2.6 - Unified Adapter (abstraction)
8. Phase 2.7 - CLI/Web Integration (user-facing)
9. Phase 3 - Testing & Documentation

## Dependencies

### External
- Cline CLI: `cline --help` documentation
- Aider: File monitoring library (watchdog or inotify)
- pydantic or json-schema-validator
- pytest for testing

### Internal
- Existing `ActivityInterpreter` and `ActivityFormatter`
- Event system infrastructure
- Existing executor implementations

### Documentation Dependencies
- JSON Schema specification
- Provider CLI documentation (Cline, Aider, Claude)
- Existing architecture documentation

## Notes

- **Aider History Storage**: Research confirms `.aider.chat.history.md` is the primary conversation log. Real-time monitoring required to capture streaming activity.
- **JSON Parsing**: Use NDJSON (newline-delimited JSON) format for streaming to handle line-by-line parsing.
- **Performance**: PTY allocation has measurable impact; investigate optimal configuration per output format.
- **Extensibility**: Design schema to accommodate future providers (Gpt-4o, Anthropic via API, etc.).
- **Error Recovery**: Implement graceful degradation if provider doesn't support requested output format.

## Reference Materials

- [Aider Documentation - Chat History](https://aider.chat/docs/faq.html)
- [Aider Configuration Options](https://aider.chat/docs/config/options.html)
- [Aider GitHub Issues - Local History](https://github.com/Aider-AI/aider/issues/2684)
- Claude Code Feature Request: [Project-Local Conversation History Storage](https://github.com/anthropics/claude-code/issues/9306)
