# Project Plan: Comprehensive Prompt Functionality Testing

## Objective
Execute comprehensive end-to-end testing of the oneshot prompt functionality using "test prompt" as the primary test case. This plan addresses the recently identified session format bug and builds on previous successful prompt testing work to ensure robust functionality across all available providers.

## Implementation Steps

### Phase 1: Environment and Bug Assessment
- [ ] Verify Python environment and dependencies are current
- [ ] Check external provider availability (Ollama, Claude CLI, etc.)
- [ ] Review and document the session format bug impact on testing
- [ ] Confirm oneshot installation and configuration

### Phase 2: Session Format Bug Mitigation
- [ ] Implement testing workaround for session format inconsistency
- [ ] Test with `--keep-log` flag to avoid format conflicts
- [ ] Verify session handling works correctly with markdown format
- [ ] Document any additional session-related issues discovered

### Phase 3: Provider-Specific Testing
- [ ] Test AiderExecutor with "test prompt" (primary focus)
- [ ] Test Direct provider with Ollama (if available)
- [ ] Test Claude/Cline providers (if configured)
- [ ] Validate Gemini provider execution (if available)
- [ ] Document provider-specific results and any failures

### Phase 4: Demo Script Validation
- [ ] Execute `test_aider_demo.py` with "test prompt"
- [ ] Execute `demo-direct-executor.sh` with "test prompt"
- [ ] Verify both scripts complete successfully without session errors
- [ ] Capture and validate execution outputs and metadata

### Phase 5: CLI Integration Testing
- [ ] Test oneshot CLI with basic "test prompt" command
- [ ] Test with different providers using provider flags
- [ ] Verify session logging captures execution data correctly
- [ ] Test error handling scenarios without session format issues

### Phase 6: Streaming and Advanced Features
- [ ] Test complete workflow from input to response with streaming
- [ ] Verify metadata and logging functionality
- [ ] Test timeout and error recovery mechanisms
- [ ] Validate async execution capabilities

### Phase 7: Regression and Unit Test Validation
- [ ] Run full test suite to ensure no regressions
- [ ] Address any remaining test failures unrelated to prompt functionality
- [ ] Verify provider abstraction works correctly across all tests
- [ ] Document test results and coverage

## Success Criteria
- [ ] All demo scripts execute successfully with "test prompt" input
- [ ] CLI processes prompts correctly across available providers
- [ ] Session format bug does not impact testing workflow
- [ ] At least one provider executes prompts successfully
- [ ] Session logs contain proper execution metadata
- [ ] No unhandled crashes during comprehensive testing
- [ ] Streaming functionality works for available providers
- [ ] Full test suite passes (or failures are unrelated to prompt functionality)

## Testing Strategy
- **Primary Test Input:** Literal "test prompt" string
- **Environment:** Local development environment with available providers
- **Verification:** Manual inspection of outputs, logs, and error handling
- **Fallback:** If external providers unavailable, test with mock/simulated responses
- **Bug Mitigation:** Use session workarounds to avoid format conflicts during testing

## Risk Assessment
- **Medium:** Session format bug may cause intermittent failures in testing
- **Medium:** External dependencies (Ollama, Claude CLI) may not be available
- **Low:** Core prompt processing should work based on previous successful tests
- **Low:** Provider abstraction should isolate individual provider issues
- **Low:** Workarounds exist for known session format issues

## Dependencies
- Python 3.8+ with oneshot installed
- At least one provider available (AiderExecutor, Direct with Ollama, or Claude CLI)
- Test environment properly configured
- Recent codebase with async refactor and session logging improvements