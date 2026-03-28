# Project Plan: Comprehensive Prompt Functionality Testing

## 1. Overview
Test all aspects of prompt handling and execution in the oneshot project, including unit tests, demo scripts, CLI integration, and provider-specific functionality to ensure prompts are processed correctly across different execution paths.

---

## 2. Technical Context
* **Project:** oneshot (Worker-Auditor Autonomous Loop)
* **Components to Test:**
  - Unit tests for prompt handling (test_executor.py, test_providers.py)
  - Provider executors (AiderExecutor, ClaudeExecutor, ClineExecutor, GeminiExecutor)
  - Direct provider with Ollama endpoints
  - CLI prompt processing and session management
  - Configuration file integration with prompts
* **Success Criteria:**
  - All unit tests pass (pytest)
  - Demo scripts execute successfully with correct outputs
  - CLI accepts and processes prompts without errors
  - Session logs properly capture prompt execution data
  - No crashes or unhandled exceptions during testing
  - Provider switching works correctly with prompts

---

## 3. Implementation Steps

### Phase 1: Environment Setup and Prerequisites
- [ ] Verify Python environment and dependencies are installed
- [ ] Check availability of external providers (Ollama, Claude CLI, Cline, etc.)
- [ ] Ensure test environment is properly configured
- [ ] Install development dependencies if needed

### Phase 2: Unit Test Execution
- [ ] Run complete pytest suite focusing on prompt-related tests
- [ ] Execute test_executor.py with prompt scenarios
- [ ] Verify test_providers.py covers all provider types
- [ ] Check test coverage for prompt processing components
- [ ] Document any test failures and their root causes

### Phase 3: Demo Script Validation
- [ ] Execute test_aider_demo.py to test AiderExecutor with sample prompts
- [ ] Run test_aider_executor_interface.py to verify interface compliance
- [ ] Execute demo-direct-executor.sh for direct provider testing
- [ ] Validate outputs match expected results
- [ ] Capture and analyze execution results

### Phase 4: CLI Integration Testing
- [ ] Test basic oneshot CLI with various prompt types
- [ ] Verify session logging captures prompt execution correctly
- [ ] Test error handling for malformed prompts
- [ ] Check configuration file integration with prompts
- [ ] Test different provider configurations

### Phase 5: Provider-Specific Testing
- [ ] Test executor providers (Claude, Cline) with prompts
- [ ] Test direct providers with Ollama endpoints
- [ ] Validate prompt processing across different models
- [ ] Test mixed provider configurations (worker + auditor)
- [ ] Verify prompt handling edge cases

### Phase 6: Regression Testing
- [ ] Run existing test suite to ensure no regressions
- [ ] Verify session management with prompts
- [ ] Test edge cases in prompt handling
- [ ] Performance testing with various prompt sizes

---

## 4. Success Criteria
- [ ] All unit tests pass (pytest)
- [ ] Demo scripts execute successfully with correct outputs
- [ ] CLI accepts and processes prompts without errors
- [ ] Session logs properly capture prompt execution data
- [ ] No crashes or unhandled exceptions during testing
- [ ] Provider switching works correctly with prompts
- [ ] Configuration files integrate properly with prompt handling

## 5. Testing Strategy
- **Environment:** Local development environment with available providers
- **Test Data:** Use existing test prompts from codebase ("What is the capital of Hungary?", "test prompt", etc.)
- **Verification:** Manual inspection of outputs and automated test results
- **Documentation:** Capture test results and any issues found
- **Isolation:** Use mocking for external dependencies where possible

## 6. Risk Assessment
- **High:** External provider dependencies may not be available in test environment
- **Medium:** Network connectivity issues for direct provider tests
- **Low:** Unit tests should be self-contained and reliable
- **Medium:** Demo scripts may require specific LLM configurations

## 7. Dependencies
- Python 3.8+ test environment set up
- External providers configured (optional for basic tests)
- Ollama running for direct provider tests (optional)
- pytest and related testing tools
- Development dependencies installed

---

## 8. Timeline
- Phase 1: 15 minutes (environment check)
- Phase 2: 30 minutes (unit tests)
- Phase 3: 45 minutes (demo scripts)
- Phase 4: 30 minutes (CLI testing)
- Phase 5: 45 minutes (provider testing)
- Phase 6: 30 minutes (regression testing)
- **Total estimated time:** 3.5 hours