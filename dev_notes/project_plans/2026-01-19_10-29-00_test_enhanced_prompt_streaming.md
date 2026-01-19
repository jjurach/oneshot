# Project Plan: Test Enhanced Prompt Streaming Functionality

## 1. Overview
Test the enhanced prompt functionality in the Oneshot system following major updates to the execution infrastructure. This includes testing the new PTY-based streaming capabilities, adaptive timeouts, and updated provider integrations.

## 2. Technical Context
* **Project:** oneshot (Worker-Auditor Autonomous Loop)
* **Recent Changes:** PTY streaming infrastructure, enhanced adaptive timeouts, updated output formats
* **Key Components to Test:**
  - PTY-based real-time streaming execution (`call_executor_pty`)
  - Streaming JSON parsing (`parse_streaming_json`)
  - Enhanced adaptive timeout with activity monitoring
  - Updated command formats (`--output-format json/stream-json`)
  - Provider executors (AiderExecutor, ClaudeExecutor, ClineExecutor, Direct)
* **Success Criteria:**
  - All existing tests pass with new streaming infrastructure
  - PTY streaming works correctly on supported platforms
  - Adaptive timeouts handle long-running prompts appropriately
  - All providers execute prompts correctly with new formats
  - CLI interface works with streaming features

---

## 3. Implementation Steps

### Phase 1: Unit Test Validation
- [ ] Run complete pytest suite to verify baseline functionality
- [ ] Verify existing prompt-related tests pass with streaming changes
- [ ] Check for any regressions in provider interfaces
- [ ] Document any test failures and their root causes

### Phase 2: PTY Streaming Feature Testing
- [ ] Test PTY allocation and execution on Linux platform
- [ ] Verify real-time output streaming works correctly
- [ ] Test streaming JSON parsing with partial/incomplete messages
- [ ] Validate fallback to buffered execution when PTY unavailable
- [ ] Test timeout handling in PTY streaming mode

### Phase 3: Provider Integration Testing
- [ ] Test AiderExecutor with new streaming infrastructure
- [ ] Test ClaudeExecutor with `--output-format stream-json`
- [ ] Test ClineExecutor with `--output-format json`
- [ ] Test DirectExecutor with Ollama integration
- [ ] Verify all providers handle prompts correctly

### Phase 4: Adaptive Timeout Validation
- [ ] Test enhanced adaptive timeout with PTY streaming
- [ ] Test fallback to buffered execution when PTY fails
- [ ] Verify activity monitoring works correctly
- [ ] Test timeout extension for long-running prompts
- [ ] Validate error handling in timeout scenarios

### Phase 5: CLI Integration Testing
- [ ] Test basic oneshot CLI command with streaming
- [ ] Test with different providers and models
- [ ] Verify session logging captures streaming output
- [ ] Test error handling and user feedback
- [ ] Validate verbose output and debugging information

### Phase 6: Cross-Platform Compatibility
- [ ] Verify PTY streaming disabled appropriately on non-Unix platforms
- [ ] Test buffered execution fallback works correctly
- [ ] Ensure environment variable controls work (`ONESHOT_DISABLE_STREAMING`)

---

## 4. Success Criteria
- [ ] All pytest tests pass (162+ tests) without streaming-related failures
- [ ] PTY streaming executes successfully on Linux with real-time output
- [ ] All provider executors (Aider, Claude, Cline, Direct) work with new formats
- [ ] Adaptive timeout extends appropriately for active processes
- [ ] CLI interface accepts and processes prompts with streaming feedback
- [ ] Session logs contain proper metadata and execution results
- [ ] Graceful fallback when streaming features unavailable
- [ ] No crashes or unhandled exceptions during testing

## 5. Testing Strategy
- **Environment:** Local development with Linux platform for PTY testing
- **Test Data:** Use existing prompts ("What is the capital of Hungary?", "test prompt")
- **Verification:** Automated tests + manual inspection of streaming output
- **Documentation:** Capture test results, performance metrics, and any issues
- **Platforms:** Linux primary, verify fallback behavior on other platforms

## 6. Risk Assessment
- **Medium:** PTY allocation may fail in some environments (containers, restricted systems)
- **Low:** Streaming features are designed with fallbacks to buffered execution
- **Medium:** External provider availability (Ollama, Claude CLI, etc.)
- **Low:** Unit tests should work independently of external services

## 7. Dependencies
- Python test environment with pytest
- Linux platform for PTY testing (or verify fallback behavior)
- External providers configured (optional for core functionality tests)
- Ollama running for DirectExecutor tests (optional)

## 8. Timeline Estimate
- Phase 1: 15 minutes (unit test execution)
- Phase 2-4: 45 minutes (streaming and provider testing)
- Phase 5: 20 minutes (CLI integration)
- Phase 6: 10 minutes (cross-platform validation)
- **Total:** ~1.5 hours

## 9. Rollback Plan
- If streaming features cause issues, disable via `ONESHOT_DISABLE_STREAMING=1`
- Revert to previous commit if necessary
- Maintain backward compatibility with existing buffered execution