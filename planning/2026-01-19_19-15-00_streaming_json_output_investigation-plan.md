# Project Plan: Streaming JSON Output Format Investigation & Cross-Provider Implementation

## Objective

Investigate and implement unified streaming and JSON output format support across all supported AI providers (Claude, Cline, Aider, Gemini). The goal is to standardize how executors capture, stream, and interpret real-time activity data in structured JSON format, enabling:

1. Real-time streaming of executor activities with JSON-based event serialization
2. Support for `--output-format stream-json` semantics across all providers
3. Pseudo-terminal (PTY) allocation investigation for Cline and similar providers
4. Unified interpretation and formatting of streamed JSON data across all providers
5. Research and integration of Aider's streaming and logging capabilities

## Background & Context

### Current State
- **Activity Interpreter/Formatter**: Recently implemented system for categorizing and displaying executor activities (tool_calls, planning, errors, etc.)
- **Provider Executors**: Claude, Cline, Aider, and Gemini providers exist but have varying levels of streaming support
- **Aider History**: Stores conversation history in `.aider.chat.history.md` and `.aider.input.history` files
- **Cline**: Uses CLI-based executor with potential for `--output-format` flags
- **Streaming**: Each provider handles streaming differently; no unified streaming abstraction exists

### Key Findings from Research
- **Aider**: Supports `--stream`/`--no-stream` flags (enabled by default), stores history in `.aider.chat.history.md`, supports `--llm-history-file` for raw LLM message logging
- **Cline**: GitHub issue #6996 indicates desire for `--output-format json` support across commands; current CLI doesn't universally support JSON output
- **Claude**: Uses SSE (Server-Sent Events) and chunked responses; can be streamed natively
- **Gemini**: Supports streaming through the Google API

## Implementation Steps

### Phase 1: Research & Documentation (Steps 1-5)

**Step 1: Investigate Cline Streaming Architecture**
- Research Cline's existing `--output-format` implementation
- Investigate `--output-format stream-json` capabilities and limitations
- Document how Cline handles pseudo-terminal (PTY) allocation
- Examine Cline's current streaming implementation patterns
- Create findings document: `dev_notes/research/2026-01-19_cline_streaming_investigation.md`

**Step 2: Research Aider Streaming & Logging Capabilities**
- Investigate how Aider currently streams responses (default enabled with `--stream`)
- Research Aider's ability to output structured JSON (not just markdown history)
- Document Aider's `.aider.chat.history.md` format and structure
- Investigate accessing Aider's LLM history file (`--llm-history-file`) as JSON
- Test parsing Aider's output to extract structured activity data
- Create findings document: `dev_notes/research/2026-01-19_aider_streaming_investigation.md`

**Step 3: Research Claude Streaming Capabilities**
- Document existing Claude SSE/chunked streaming implementation
- Investigate converting Claude's streaming output to JSON Lines format (JSONL)
- Research how Claude's thinking tags and tool calls can be streamed as structured JSON
- Document current activity interpreter integration points
- Create findings document: `dev_notes/research/2026-01-19_claude_streaming_investigation.md`

**Step 4: Research Gemini Streaming & API Integration**
- Investigate Google's Gemini API streaming capabilities
- Document Gemini's structured output format (currently exists)
- Research how Gemini handles tool use and real-time activity streaming
- Explore converting Gemini streaming to unified JSON format
- Create findings document: `dev_notes/research/2026-01-19_gemini_streaming_investigation.md`

**Step 5: Define Unified Streaming JSON Schema**
- Create comprehensive JSON schema for streaming events that works across ALL providers
- Define event types: `activity_started`, `activity_progressed`, `activity_completed`, `error`, `tool_call`, `file_operation`, `planning`, etc.
- Design metadata structure for provider-specific information
- Create schema validation framework
- Document schema in: `dev_notes/research/2026-01-19_unified_streaming_json_schema.md`

### Phase 2: Provider-Specific Implementations (Steps 6-10)

**Step 6: Implement Cline Streaming JSON Support**
- Extend `ClineExecutor` with `--output-format stream-json` support
- Implement PTY allocation handling (research pseudo-terminal support)
- Add JSON event emission for each streaming chunk
- Create real-time JSON Lines output stream
- Implement buffering and parsing for streaming events
- Add error handling and malformed JSON recovery
- Create unit tests: `tests/test_cline_streaming.py`
- File: `src/oneshot/providers/cline_executor.py` (update existing)

**Step 7: Implement Aider Streaming JSON Support**
- Extend `AiderExecutor` with JSON streaming capabilities
- Implement real-time monitoring of `.aider.chat.history.md` file changes
- Create streaming event parser that converts Aider's markdown output to JSON events
- Implement `--llm-history-file` monitoring for raw LLM message tracking
- Add support for extracting streaming chunks as JSON during execution
- Create JSON Lines output for Aider's streaming responses
- Add error handling for file I/O and parsing edge cases
- Create unit tests: `tests/test_aider_streaming.py`
- File: `src/oneshot/providers/aider_executor.py` (update existing)

**Step 8: Implement Claude Streaming JSON Support**
- Extend `ClaudeExecutor` with explicit JSON streaming support
- Convert existing SSE/chunked streaming to JSON Lines format
- Implement streaming event emitter that converts thinking tags, tool calls, and responses to JSON
- Add support for `stream-json` output format flag
- Ensure backward compatibility with existing streaming
- Create unit tests: `tests/test_claude_streaming.py`
- File: `src/oneshot/providers/claude_executor.py` (update existing)

**Step 9: Implement Gemini Streaming JSON Support**
- Extend `GeminiExecutor` with unified JSON streaming support
- Convert Gemini's native streaming to unified schema
- Implement tool use and function call streaming as JSON events
- Add support for `stream-json` output format flag
- Create unit tests: `tests/test_gemini_streaming.py`
- File: `src/oneshot/providers/gemini_executor.py` (update existing)

**Step 10: Create Unified Streaming Interface**
- Create `StreamingOutput` abstract base class in `base.py`
- Define streaming event interface with fields: `type`, `timestamp`, `provider`, `payload`
- Implement `JSONLStreamingOutput` concrete class for JSON Lines format
- Add streaming output to `ExecutionResult` dataclass
- Create adapter layer that works with all executors
- Implement streaming event factory pattern
- File: `src/oneshot/providers/base.py` (update)

### Phase 3: Interpretation & Processing (Steps 11-13)

**Step 11: Enhance Activity Interpreter for Streaming JSON**
- Extend `ActivityInterpreter` to process streaming JSON events
- Add methods: `interpret_json_event()`, `parse_streaming_chunk()`, `handle_partial_json()`
- Implement incremental interpretation for streaming data
- Add buffering for out-of-order or partial events
- Create comprehensive unit tests for streaming scenarios
- File: `src/oneshot/providers/activity_interpreter.py` (update)

**Step 12: Implement Streaming Activity Formatter**
- Create `StreamingActivityFormatter` class for real-time formatting
- Support both compact and detailed streaming formats
- Implement ANSI coloring for terminal output
- Add support for progress indicators and real-time updates
- Create methods: `format_streaming_start()`, `format_streaming_update()`, `format_streaming_end()`
- File: `src/oneshot/providers/activity_formatter.py` (update/new)

**Step 13: Create JSON Event Dispatcher System**
- Implement centralized dispatcher for streaming JSON events
- Add event routing based on type and provider
- Create subscriber/observer pattern for event handlers
- Integrate with existing `AsyncEventEmitter` system
- Add event filtering and transformation pipeline
- Enable real-time event forwarding to CLI, Web UI, and logging systems
- File: `src/oneshot/events.py` (new streaming event types)

### Phase 4: Integration & Testing (Steps 14-16)

**Step 14: Integrate Streaming with Executor Pipeline**
- Update `ExecutorProvider.run_executor()` to handle streaming outputs
- Add streaming event emission hooks during execution
- Implement real-time progress tracking
- Create streaming output aggregation system
- Update `oneshot.py` to support streaming mode
- File: `src/oneshot/providers/__init__.py` (update)

**Step 15: Create Comprehensive Streaming Tests**
- Unit tests for each provider's streaming implementation (6 test files)
- Integration tests for streaming event interpretation and formatting
- End-to-end tests for all providers with real tasks
- Edge case tests: empty streams, malformed JSON, network interruptions
- Performance tests: streaming throughput and latency
- Files: `tests/test_*_streaming.py` (6 files)

**Step 16: Update CLI and Web UI for Streaming**
- Enhance CLI to display real-time streaming events
- Update Web UI to handle WebSocket streaming of JSON events
- Add CLI flag: `--stream-json` for JSON output format
- Add CLI flag: `--stream-format` to select streaming verbosity (compact/detailed)
- Create streaming progress display in TUI
- File: `src/cli/oneshot_cli.py` (update), `src/oneshot/web_ui.py` (update)

### Phase 5: Documentation & Validation (Steps 17-18)

**Step 17: Create Comprehensive Streaming Documentation**
- Document unified JSON schema with examples
- Create implementation guide for each provider
- Document CLI streaming flags and options
- Create troubleshooting guide for streaming issues
- Add streaming examples and use cases
- Files: `docs/streaming-guide.md`, `docs/streaming-schema.md`

**Step 18: Final Testing & Validation**
- Run full test suite (pytest) - all tests must pass
- Validate streaming behavior across all providers with real-world tasks
- Performance validation: streaming latency, throughput, resource usage
- Document any limitations or edge cases discovered
- Create validation report: `dev_notes/validation/2026-01-19_streaming_implementation_validation.md`
- Commit all changes to git

## Success Criteria

1. **Complete Research Phase**
   - ✅ All 5 research documents completed with detailed findings
   - ✅ Unified JSON schema defined and documented
   - ✅ PTY allocation understanding for Cline documented

2. **Provider Implementations**
   - ✅ All 4 providers (Claude, Cline, Aider, Gemini) support streaming JSON
   - ✅ Each provider has `--output-format stream-json` equivalent
   - ✅ Unified streaming interface in `BaseExecutor`
   - ✅ JSON Lines format output working correctly

3. **Activity Interpretation**
   - ✅ Streaming JSON events correctly interpreted by ActivityInterpreter
   - ✅ Real-time formatting works with streaming data
   - ✅ Event dispatcher routes events correctly

4. **Integration**
   - ✅ CLI supports `--stream-json` flag
   - ✅ Web UI displays real-time streaming events
   - ✅ All executors emit streaming events properly

5. **Testing**
   - ✅ All unit tests pass (6 provider-specific test files)
   - ✅ Integration tests validate end-to-end streaming
   - ✅ 100% test pass rate before final commit
   - ✅ No regressions in existing functionality

6. **Documentation**
   - ✅ Comprehensive streaming implementation guide
   - ✅ JSON schema documentation with examples
   - ✅ Troubleshooting and best practices guide

## Testing Strategy

### Unit Testing
- **Provider-Specific Tests** (6 files): Test each executor's streaming implementation independently
  - `tests/test_claude_streaming.py`: Claude SSE/chunked streaming to JSON conversion
  - `tests/test_cline_streaming.py`: Cline CLI JSON output parsing
  - `tests/test_aider_streaming.py`: Aider markdown output to JSON conversion
  - `tests/test_gemini_streaming.py`: Gemini API streaming parsing
  - `tests/test_activity_interpreter_streaming.py`: JSON event interpretation
  - `tests/test_streaming_formatter.py`: Real-time event formatting

- **Core Functionality Tests**:
  - Streaming event serialization/deserialization
  - Partial JSON handling and buffering
  - Error recovery and malformed data handling
  - Event type routing and filtering

### Integration Testing
- End-to-end provider execution with streaming enabled
- Event emission and reception across system
- CLI display of streamed events
- Web UI WebSocket streaming validation
- Activity interpretation + formatting pipeline

### Edge Cases
- Empty streams
- Incomplete JSON in stream
- Out-of-order events
- Rapid event bursts (high throughput)
- Network interruption recovery (for remote providers)
- Provider-specific error handling

### Performance Testing
- Streaming throughput (events/second)
- Event latency (from generation to display)
- Memory usage during long-running streams
- CPU utilization during active streaming

## Risk Assessment

### High Priority Risks
1. **PTY Allocation Unknown**: Cline's pseudo-terminal allocation behavior not yet understood
   - **Mitigation**: Research in Phase 1 (Step 1), consult Cline documentation/GitHub

2. **Aider Output Variability**: Aider's markdown output format may change across versions
   - **Mitigation**: Version-lock Aider during testing, implement flexible parsing with fallbacks

3. **Streaming Event Ordering**: Events from concurrent operations may arrive out of order
   - **Mitigation**: Add sequence numbers/timestamps, implement buffering logic

4. **Performance Impact**: Real-time JSON event emission may add latency
   - **Mitigation**: Performance testing in Phase 4, implement async event emission

### Medium Priority Risks
1. **Schema Compatibility**: Unified schema may not fit all provider capabilities
   - **Mitigation**: Make schema extensible with provider-specific fields

2. **Backward Compatibility**: Changes to ExecutionResult may break existing code
   - **Mitigation**: Make streaming output optional, add deprecation timeline if needed

3. **File I/O Race Conditions**: Monitoring Aider's `.aider.chat.history.md` file
   - **Mitigation**: Implement proper file locking, retry logic, and error handling

### Low Priority Risks
1. **Breaking Changes**: Updates to base executor interface
   - **Mitigation**: Comprehensive test suite catches regressions

2. **Documentation Drift**: Schema changes not reflected in docs
   - **Mitigation**: Implement docs validation in CI/CD

## Timeline Considerations

- **Phase 1 (Research)**: Foundational work, must complete before implementation
- **Phase 2-3 (Implementation)**: Can be parallelized across providers after schema definition
- **Phase 4-5 (Integration & Testing)**: Sequential, builds on previous phases
- **Estimated Complexity**: 18 implementation steps with multiple test files and documentation

## Key Dependencies

1. Existing `ActivityInterpreter` and `ActivityFormatter` classes
2. Existing executor provider implementations (Claude, Cline, Aider, Gemini)
3. Event system (`AsyncEventEmitter`) in `src/oneshot/events.py`
4. CLI framework in `src/cli/oneshot_cli.py`
5. Web UI framework in `src/oneshot/web_ui.py`

## Deliverables

### Research Documents (5)
- `dev_notes/research/2026-01-19_cline_streaming_investigation.md`
- `dev_notes/research/2026-01-19_aider_streaming_investigation.md`
- `dev_notes/research/2026-01-19_claude_streaming_investigation.md`
- `dev_notes/research/2026-01-19_gemini_streaming_investigation.md`
- `dev_notes/research/2026-01-19_unified_streaming_json_schema.md`

### Code Implementation Files
- Updated: `src/oneshot/providers/cline_executor.py` (streaming support)
- Updated: `src/oneshot/providers/aider_executor.py` (streaming support)
- Updated: `src/oneshot/providers/claude_executor.py` (JSON streaming)
- Updated: `src/oneshot/providers/gemini_executor.py` (JSON streaming)
- Updated: `src/oneshot/providers/base.py` (streaming interface)
- Updated: `src/oneshot/providers/activity_interpreter.py` (streaming JSON parsing)
- Updated: `src/oneshot/providers/activity_formatter.py` (streaming output)
- New: `src/oneshot/providers/streaming_dispatcher.py` (event routing)
- Updated: `src/oneshot/events.py` (streaming event types)
- Updated: `src/cli/oneshot_cli.py` (streaming flags)
- Updated: `src/oneshot/web_ui.py` (WebSocket streaming)

### Test Files (6)
- `tests/test_claude_streaming.py`
- `tests/test_cline_streaming.py`
- `tests/test_aider_streaming.py`
- `tests/test_gemini_streaming.py`
- `tests/test_activity_interpreter_streaming.py`
- `tests/test_streaming_formatter.py`

### Documentation Files
- `docs/streaming-guide.md` (implementation guide)
- `docs/streaming-schema.md` (JSON schema reference)
- `dev_notes/validation/2026-01-19_streaming_implementation_validation.md`

---

## Notes for Implementation

1. **Research Phase is Critical**: Do not skip Steps 1-5. Understanding each provider's capabilities is essential for Phase 2.

2. **Schema First**: Complete Step 5 before implementing provider-specific code. The unified schema is the foundation.

3. **Incremental Testing**: Each provider implementation (Steps 6-9) should be tested independently before integration.

4. **Backward Compatibility**: Streaming should be optional. Existing code should continue to work without changes.

5. **Documentation as Code**: Keep schema and implementation docs synchronized as code changes.

6. **Version Control**: Commit after each major phase (after Steps 5, 10, 13, 16, 18) with detailed commit messages.
