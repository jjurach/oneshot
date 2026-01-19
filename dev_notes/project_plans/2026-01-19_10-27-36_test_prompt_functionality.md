# Project Plan: Test Prompt Functionality

## 1. Overview
Test the prompt handling and execution functionality in the oneshot project. This involves running existing tests, demo scripts, and CLI commands to verify that prompts are processed correctly by various providers (Aider, Claude, Cline, Gemini, Direct).

## 2. Technical Context
* **Project:** oneshot (Worker-Auditor Autonomous Loop)
* **Components to Test:**
  - Unit tests for prompt handling
  - Provider executors (AiderExecutor, ClaudeExecutor, etc.)
  - Direct provider with Ollama
  - CLI prompt processing
* **Success Criteria:**
  - All existing tests pass
  - Demo scripts execute successfully
  - Basic oneshot CLI command works with test prompt

---

## 3. Implementation Steps

### Phase 1: Unit Test Execution
- [x] Run pytest to execute all unit tests
- [x] Verify test_executor.py tests pass (includes "test prompt" scenarios)
- [x] Check test coverage for prompt-related functionality
- [x] Document any test failures and their causes

### Phase 2: Demo Script Testing
- [x] Execute test_aider_demo.py to test AiderExecutor
- [x] Run demo-direct-executor.sh to test Direct provider with Ollama
- [x] Verify both scripts complete successfully
- [x] Capture and review output for correctness

### Phase 3: CLI Integration Testing
- [x] Test basic oneshot CLI command with simple prompt
- [x] Test with different providers (if available)
- [x] Verify session logging works correctly
- [x] Check error handling for invalid prompts

---

## 4. Success Criteria
- [ ] All pytest tests pass without errors
- [ ] Demo scripts execute and produce expected outputs
- [ ] Oneshot CLI accepts and processes test prompts correctly
- [ ] Session logs are created and contain proper prompt execution data
- [ ] No crashes or unhandled exceptions during testing

## 5. Testing Strategy
- **Environment:** Local development environment with available providers
- **Test Data:** Use existing test prompts from codebase ("What is the capital of Hungary?", "test prompt", etc.)
- **Verification:** Manual inspection of outputs and automated test results
- **Documentation:** Capture test results and any issues found

## 6. Risk Assessment
- **Medium:** External dependencies (Ollama, Claude CLI, etc.) may not be available
- **Low:** Unit tests should be isolated and not require external services
- **Medium:** Provider-specific tests may fail if executors aren't properly configured

## 7. Dependencies
- Python test environment set up
- External providers configured (optional for basic tests)
- Ollama running for direct provider tests (optional)