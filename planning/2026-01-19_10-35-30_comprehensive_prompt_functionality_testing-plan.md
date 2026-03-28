# Project Plan: Comprehensive Prompt Functionality Testing

## Objective
Execute end-to-end testing of prompt processing across all providers and execution paths in the oneshot system to ensure robust functionality. This plan consolidates existing incomplete testing plans and addresses current test failures.

## Implementation Steps

### Phase 1: Environment and Dependency Verification
- [ ] Verify Python environment and all dependencies are properly installed
- [ ] Check external provider availability (Ollama, Claude CLI, Cline, etc.)
- [ ] Confirm oneshot package is installed in development mode
- [ ] Validate configuration files and environment variables

### Phase 2: Test Suite Analysis and Fixes
- [ ] Analyze the failing `test_call_claude_executor` test in detail
- [ ] Fix the input parameter issue causing the test failure
- [ ] Run full test suite to establish baseline
- [ ] Document any remaining test failures and assess impact

### Phase 3: AiderExecutor Testing
- [ ] Execute `test_aider_demo.py` with "test prompt" input
- [ ] Verify successful execution and output validation
- [ ] Test with different prompt variations
- [ ] Validate metadata and session logging

### Phase 4: Direct Provider Testing
- [ ] Test Direct provider with Ollama (if available)
- [ ] Test with OpenAI-compatible endpoints (if configured)
- [ ] Verify API key handling and authentication
- [ ] Test Gemini provider execution (if available)

### Phase 5: CLI Integration Testing
- [ ] Test basic oneshot CLI with "test prompt"
- [ ] Test with different provider configurations
- [ ] Verify command-line argument parsing
- [ ] Test error scenarios and help messages

### Phase 6: Session Management Testing
- [ ] Verify session logging captures prompt execution data
- [ ] Test session resume functionality
- [ ] Validate session format consistency
- [ ] Test session cleanup and management

### Phase 7: Provider Switching Testing
- [ ] Test switching between executor and direct providers
- [ ] Verify mixed provider configurations (worker + auditor)
- [ ] Test provider-specific prompt handling
- [ ] Validate provider abstraction layer

### Phase 8: Streaming and Advanced Features
- [ ] Test complete workflow from input to response with streaming
- [ ] Verify metadata and logging functionality
- [ ] Test timeout and error recovery mechanisms
- [ ] Validate async execution capabilities

### Phase 9: Error Handling and Edge Cases
- [ ] Test with malformed prompts
- [ ] Test network failure scenarios
- [ ] Test provider unavailability
- [ ] Test concurrent execution limits

### Phase 10: Regression and Final Validation
- [ ] Run full test suite to ensure no regressions
- [ ] Verify all prompt-related functionality works
- [ ] Document comprehensive test results
- [ ] Update project documentation if needed

## Success Criteria
- [ ] All demo scripts execute successfully with "test prompt"
- [ ] CLI processes prompts without errors across available providers
- [ ] Session logs contain proper execution metadata
- [ ] No unhandled crashes during comprehensive testing
- [ ] Failing tests resolved or documented as unrelated to prompt functionality
- [ ] Provider switching works correctly
- [ ] Streaming functionality verified for available providers
- [ ] Full test suite passes (or failures unrelated to prompt functionality)

## Testing Strategy
- **Primary Test Input:** "test prompt" string
- **Environment:** Local development environment
- **Verification:** Manual inspection, automated tests, and log analysis
- **Fallback:** Skip unavailable external providers and document limitations
- **Documentation:** Capture all test results and issues

## Risk Assessment
- **Medium:** External provider dependencies may not be available (Ollama, Claude CLI)
- **Medium:** Network connectivity issues for direct provider tests
- **Low:** Core prompt processing should work based on existing architecture
- **Low:** Provider abstraction isolates individual provider issues
- **Low:** Session format issues can be worked around with --keep-log flag

## Dependencies
- Python 3.8+ with oneshot installed
- At least one provider available (AiderExecutor, Direct with API, or CLI executors)
- Test environment properly configured
- Recent codebase with async refactor and session improvements