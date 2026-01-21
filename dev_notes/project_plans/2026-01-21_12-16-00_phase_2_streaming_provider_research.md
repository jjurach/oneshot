# Project Plan: Phase 2 - Provider Research & Unified Schema Definition

**Status:** DRAFT - AWAITING APPROVAL
**Date:** 2026-01-21
**Related Project Plan:** `dev_notes/project_plans/2026-01-19_19-15-00_streaming_json_output_investigation.md`

## Objective

Complete Phase 2 of the Streaming JSON Output Investigation by conducting detailed research into each provider's streaming capabilities and defining a unified JSON schema for real-time activity streaming. This phase focuses on understanding the current state of streaming across all providers (Cline, Aider, Claude, Gemini) and creating a comprehensive specification that enables Phase 3 implementation.

## Context

Phase 1 established that:
- ✅ Two event formats exist (legacy "Say/Ask" and current "Message" formats)
- ✅ NDJSON format is correct for streaming
- ✅ No unified schema currently exists
- ✅ Need for provider identification and timestamp standardization identified

Phase 2 will research each provider's capabilities and create the foundation for unified streaming implementation.

## Implementation Steps

### Step 1: Cline Streaming Architecture Investigation
**Objective:** Document Cline's current streaming capabilities and identify paths to JSON streaming support.

**Research Tasks:**
- Investigate Cline's existing `--output-format` implementation
- Test `--output-format stream-json` capabilities and document limitations
- Document how Cline handles pseudo-terminal (PTY) allocation
- Examine Cline's current streaming implementation patterns
- Test various Cline commands with different output formats
- Document any existing JSON output capabilities

**Deliverables:**
- `dev_notes/research/2026-01-21_cline_streaming_investigation.md`
- Test results and command examples
- PTY allocation behavior documentation
- Recommendations for JSON streaming implementation

### Step 2: Aider Streaming & Logging Capabilities Research
**Objective:** Document Aider's streaming and logging mechanisms for conversion to unified JSON format.

**Research Tasks:**
- Investigate Aider's `--stream`/`--no-stream` flags (enabled by default)
- Research Aider's ability to output structured JSON beyond markdown history
- Document `.aider.chat.history.md` format and real-time update patterns
- Investigate `--llm-history-file` for raw LLM message logging as JSON
- Test parsing Aider's output to extract structured activity data during execution
- Document file I/O patterns and potential race conditions

**Deliverables:**
- `dev_notes/research/2026-01-21_aider_streaming_investigation.md`
- File monitoring strategies and implementation approaches
- JSON conversion patterns from markdown history
- Performance considerations for real-time parsing

### Step 3: Claude Streaming Capabilities Research
**Objective:** Document Claude's existing streaming implementation and identify JSON conversion requirements.

**Research Tasks:**
- Document existing Claude SSE (Server-Sent Events) and chunked streaming
- Investigate converting Claude's streaming output to JSON Lines format
- Research how Claude's thinking tags and tool calls can be streamed as structured JSON
- Document current activity interpreter integration points
- Test streaming behavior with different prompt types
- Identify any gaps in current streaming implementation

**Deliverables:**
- `dev_notes/research/2026-01-21_claude_streaming_investigation.md`
- SSE to JSONL conversion strategies
- Event type mapping from Claude's format to unified schema
- Backward compatibility considerations

### Step 4: Gemini Streaming & API Integration Research
**Objective:** Document Gemini's streaming capabilities and integration points.

**Research Tasks:**
- Investigate Google Gemini API streaming capabilities
- Document Gemini's current structured output format
- Research how Gemini handles tool use and real-time activity streaming
- Test streaming behavior with different model configurations
- Explore converting Gemini streaming to unified JSON format
- Document API rate limits and streaming constraints

**Deliverables:**
- `dev_notes/research/2026-01-21_gemini_streaming_investigation.md`
- API streaming patterns and limitations
- Tool use streaming conversion strategies
- Error handling and recovery mechanisms

### Step 5: Unified Streaming JSON Schema Definition
**Objective:** Create comprehensive JSON schema that accommodates all provider capabilities.

**Design Tasks:**
- Define event types covering all providers: `activity_started`, `activity_progressed`, `activity_completed`, `error`, `tool_call`, `file_operation`, `planning`, `thinking`, `user_input`, `assistant_output`, etc.
- Design metadata structure for provider-specific information
- Include standardized timestamp format (ISO 8601)
- Add sequence numbers for event ordering
- Define payload structure for different event types
- Create schema validation framework
- Document extensibility for future providers

**Deliverables:**
- `dev_notes/research/2026-01-21_unified_streaming_json_schema.md`
- JSON schema definition with examples
- Validation framework design
- Migration path from existing formats

### Step 6: Cross-Provider Analysis & Recommendations
**Objective:** Synthesize research findings and create Phase 3 implementation roadmap.

**Analysis Tasks:**
- Compare streaming capabilities across all providers
- Identify common patterns and provider-specific requirements
- Prioritize implementation order based on complexity and dependencies
- Define integration points with existing codebase
- Document potential challenges and mitigation strategies
- Create detailed Phase 3 project plan outline

**Deliverables:**
- `dev_notes/research/2026-01-21_cross_provider_streaming_analysis.md`
- Phase 3 implementation roadmap
- Risk assessment and mitigation plan
- Success criteria for Phase 3 completion

## Timeline

- **Step 1 (Cline Research)**: 4 hours - Document current capabilities and PTY behavior
- **Step 2 (Aider Research)**: 4 hours - File monitoring and markdown parsing strategies
- **Step 3 (Claude Research)**: 3 hours - SSE conversion and event mapping
- **Step 4 (Gemini Research)**: 3 hours - API streaming patterns and limitations
- **Step 5 (Schema Design)**: 6 hours - Unified schema definition and validation
- **Step 6 (Analysis & Planning)**: 4 hours - Cross-provider synthesis and roadmap

**Total Estimated Time:** 24 hours (3 working days)

## Success Criteria

### Research Quality
- ✅ All 4 provider research documents completed with detailed findings
- ✅ Hands-on testing of streaming capabilities for each provider
- ✅ Clear documentation of current limitations and capabilities
- ✅ Identification of implementation paths for each provider

### Schema Design
- ✅ Unified JSON schema accommodates all provider capabilities
- ✅ Schema includes proper metadata (timestamps, sequence numbers, provider ID)
- ✅ Event types cover all identified activity patterns
- ✅ Schema is extensible for future providers
- ✅ Validation framework designed and documented

### Implementation Readiness
- ✅ Phase 3 implementation roadmap created
- ✅ Clear prioritization of provider implementations
- ✅ Risk assessment completed with mitigation strategies
- ✅ Integration points identified and documented

## Testing Strategy

### Research Validation
- **Provider Testing**: Each research step includes hands-on testing of provider capabilities
- **Command Testing**: Document working commands and output formats for each provider
- **Error Scenarios**: Test edge cases like network failures, malformed responses, PTY issues

### Schema Validation
- **Example Generation**: Create realistic JSON examples for each event type
- **Cross-Validation**: Ensure schema works with output from all researched providers
- **Backward Compatibility**: Verify schema can represent existing activity formats

## Risk Assessment

### High Priority Risks
1. **PTY Allocation Complexity**: Cline's pseudo-terminal behavior may be complex
   - **Mitigation**: Extensive testing and documentation in Step 1

2. **Aider File I/O Race Conditions**: Real-time monitoring of history files
   - **Mitigation**: Research file locking and atomic write patterns

3. **API Rate Limiting**: Gemini/Claude streaming may hit rate limits during testing
   - **Mitigation**: Implement delays and monitor API usage

### Medium Priority Risks
1. **Provider API Changes**: Streaming capabilities may change between versions
   - **Mitigation**: Document version dependencies and update mechanisms

2. **Complex Event Mapping**: Some provider events may not map cleanly to unified schema
   - **Mitigation**: Design extensible schema with provider-specific fields

## Dependencies

### Tools Required
- Access to all 4 providers (Cline, Aider, Claude API, Gemini API)
- Development environment with all providers configured
- File monitoring tools for Aider research
- JSON schema validation tools

### Knowledge Prerequisites
- Understanding of existing Oneshot codebase and provider architecture
- Familiarity with each provider's API and CLI interfaces
- Experience with streaming protocols (SSE, WebSockets, etc.)

## Deliverables Summary

### Research Documents (5 files)
- `dev_notes/research/2026-01-21_cline_streaming_investigation.md`
- `dev_notes/research/2026-01-21_aider_streaming_investigation.md`
- `dev_notes/research/2026-01-21_claude_streaming_investigation.md`
- `dev_notes/research/2026-01-21_gemini_streaming_investigation.md`
- `dev_notes/research/2026-01-21_unified_streaming_json_schema.md`

### Analysis Documents (1 file)
- `dev_notes/research/2026-01-21_cross_provider_streaming_analysis.md`

### Integration Artifacts
- Phase 3 project plan outline
- Schema validation framework design
- Implementation priority matrix

---

## Implementation Notes

1. **Research-First Approach**: Each provider investigation must include hands-on testing
2. **Documentation Standards**: Use consistent format across all research documents
3. **Schema Extensibility**: Design schema to accommodate future providers and event types
4. **Testing Integration**: Include test commands and expected outputs in research docs
5. **Version Dependencies**: Document provider versions and potential compatibility issues

## Next Steps (After Approval)

1. Begin Step 1: Cline streaming investigation
2. Document findings and test results
3. Progress through each research step sequentially
4. Complete schema design in Step 5
5. Create Phase 3 implementation roadmap in Step 6
6. Prepare for developer review and Phase 3 approval

---

*Generated: 2026-01-21 12:16 UTC*
*Phase: Research & Planning*
*Status: AWAITING APPROVAL*