# Project Plan: Complete Prompt Functionality Testing

## Objective
Execute comprehensive testing of prompt functionality across all providers and execution modes to ensure the oneshot system correctly processes and responds to prompts, resolving current test failures and completing all testing phases.

## Implementation Steps

### Phase 1: Address Test Failures
- [ ] Fix executor test failures in `tests/test_executor.py` (PTY mocking issues)
- [ ] Update tests to work with new streaming PTY execution
- [ ] Ensure all 168 tests pass without new failures

### Phase 2: Complete Unit Test Verification
- [ ] Run pytest on all prompt-related tests (`test_executor.py`, `test_providers.py`)
- [ ] Verify all provider tests pass (26/26 expected)
- [ ] Confirm no regressions in provider system

### Phase 3: Provider-Specific Testing
- [ ] **AiderExecutor**: Run `test_aider_demo.py` with "test prompt"
- [ ] **Direct Provider**: Execute `demo-direct-executor.sh` with "test prompt"
- [ ] **Claude/Cline**: Test via CLI with executor providers (if available)

### Phase 4: CLI Integration Testing
- [ ] Test basic oneshot CLI command with "test prompt"
- [ ] Verify session logging captures prompt execution data
- [ ] Test error handling with invalid prompts

### Phase 5: End-to-End Validation
- [ ] Execute system with the literal prompt "test prompt"
- [ ] Test with more complex prompts from `dev_notes/prompts/`
- [ ] Verify output formatting and metadata inclusion

## Success Criteria
- [ ] All 168 pytest tests pass without failures
- [ ] Demo scripts execute successfully and produce expected outputs
- [ ] CLI accepts and processes "test prompt" correctly
- [ ] Session logs contain proper prompt execution metadata
- [ ] No crashes or unhandled exceptions during testing
- [ ] PTY streaming functionality works correctly

## Testing Strategy
- **Environment**: Local development with available providers (Ollama for Direct provider)
- **Test Data**: Use "test prompt" as primary test case, plus existing prompt files
- **Verification**: Manual inspection of outputs and automated test results
- **Documentation**: Record test results and any issues found

## Risk Assessment
- **Medium**: External dependencies (Ollama, Claude CLI) may not be available
- **Low**: Unit tests should be isolated and not require external services
- **High**: PTY streaming test failures need resolution before completion

## Dependencies
- Python test environment set up
- Ollama running for direct provider tests (optional)
- External providers configured (optional for basic tests)