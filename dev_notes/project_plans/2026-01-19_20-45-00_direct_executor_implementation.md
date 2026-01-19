# Project Plan: Direct Executor Implementation

## Objective

Implement support for "direct" as a regular executor option that allows the `oneshot` CLI to directly communicate with local language models (specifically Ollama) via HTTP API, without requiring subprocess overhead. This provides a starting platform for lang-graph experimentation and validates concept with simple tasks like "2+2?" and "what is the capital of sweden?".

The implementation should allow:
```
oneshot --executor direct "what is the capital of sweden?"
```

Where the worker prompt is transmitted directly to the local Ollama model running on the system, establishing a minimal but functional executor that can serve the worker role.

## Implementation Steps

### Step 1: Audit Current Architecture
- **Task**: Review current executor provider system to understand how "claude", "cline", and "aider" executors are registered and used
- **Details**:
  - Examine `src/oneshot/providers/__init__.py` to understand ProviderConfig and create_provider()
  - Check `src/cli/oneshot_cli.py` to see where executor choices are defined (line 130: choices=['claude', 'cline', 'aider'])
  - Identify where executor defaults are applied in `src/oneshot/config.py`
- **Deliverable**: Document current executor registration pattern

### Step 2: Create DirectExecutor Class
- **Task**: Implement a new DirectExecutor class as a BaseExecutor subclass
- **Location**: `src/oneshot/providers/direct_executor.py` (NEW)
- **Details**:
  - Extend `BaseExecutor` from `src/oneshot/providers/base.py`
  - Implement `run_task()` method that:
    - Connects to local Ollama instance (default: http://localhost:11434)
    - Sends worker prompt as a chat completion API request
    - Returns ExecutionResult with success/output/error
  - Support configuration via environment variables:
    - `OLLAMA_ENDPOINT` (default: http://localhost:11434)
    - `OLLAMA_MODEL` (default: llama-pro or model from --worker-model)
  - Handle connection errors gracefully (Ollama not running)
  - Include basic retry logic for transient failures
- **Deliverable**: DirectExecutor class that can execute prompts against Ollama

### Step 3: Register DirectExecutor as Built-in Executor
- **Task**: Integrate DirectExecutor into the executor provider system
- **Details**:
  - Modify `src/oneshot/providers/__init__.py`:
    - Import DirectExecutor
    - Update ProviderConfig validation to accept "direct" as valid executor (line 49)
    - Update ExecutorProvider._call_direct_executor() method (similar to _call_aider_executor and _call_gemini_executor)
    - Add case for executor == "direct" in ExecutorProvider.generate() and generate_async()
  - Modify `src/cli/oneshot_cli.py`:
    - Add "direct" to executor choices (line 130)
    - Ensure --worker-endpoint and --worker-model options work with direct executor
    - Add appropriate validation/defaults for direct executor
  - Update `src/oneshot/config.py`:
    - Add direct executor as valid executor option
- **Deliverable**: DirectExecutor integrated into provider system

### Step 4: Add Unit Tests
- **Task**: Create comprehensive test suite for DirectExecutor
- **Location**: `tests/test_direct_executor.py` (NEW)
- **Details**:
  - Mock Ollama HTTP responses to avoid requiring running Ollama instance
  - Test successful execution with various prompts
  - Test error handling (connection failed, malformed response, etc.)
  - Test configuration via environment variables
  - Test timeout handling
  - Test simple mathematical queries ("2+2") and factual queries ("capital of Sweden")
  - Ensure tests pass without live Ollama (use mocks)
- **Deliverable**: Test suite with coverage for DirectExecutor functionality

### Step 5: Create Demo Scripts
- **Task**: Create demonstration scripts showing DirectExecutor usage
- **Location**: `demos/direct_executor_demo.py` (NEW)
- **Details**:
  - Demo 1: Simple mathematical query ("2+2?")
  - Demo 2: Factual query ("What is the capital of Sweden?")
  - Include instructions for running these demos with live Ollama
  - Document expected output
  - Include error handling examples (Ollama not running, etc.)
- **Deliverable**: Working demo scripts that can validate basic concept

### Step 6: Integration Test
- **Task**: Create integration test that validates end-to-end flow
- **Location**: `tests/test_direct_executor_integration.py` (NEW)
- **Details**:
  - Test the full oneshot flow using DirectExecutor
  - Include mocked Ollama responses for test scenarios
  - Validate that prompt flows through CLI → ProviderConfig → DirectExecutor → Response
  - Test both simple and complex prompts
- **Deliverable**: Integration test validating complete flow

### Step 7: Update Documentation
- **Task**: Update usage documentation with DirectExecutor information
- **Files to Update**:
  - `README.md`: Add section explaining DirectExecutor usage
    - Example: `oneshot --executor direct "2+2?"`
    - Explain Ollama setup requirements
    - Note current capabilities and limitations
  - `docs/direct-executor.md`: Expand with implementation details (if not already sufficient)
  - `docs/overview.md`: Update if needed to mention direct executor
- **Details**:
  - Explain how to run Ollama locally
  - Document configuration options
  - Note that this is a foundation for lang-graph experimentation
- **Deliverable**: Updated documentation with examples

### Step 8: Verification and Testing
- **Task**: Run full test suite and verify all functionality
- **Details**:
  - Run `pytest tests/` to ensure all tests pass
  - Run specific DirectExecutor tests: `pytest tests/test_direct_executor.py -v`
  - Run integration tests: `pytest tests/test_direct_executor_integration.py -v`
  - Run demo scripts to validate CLI functionality
  - Verify no regressions in existing executor tests
- **Deliverable**: All tests passing, demo scripts functional

## Success Criteria

1. ✅ CLI accepts `--executor direct` option
2. ✅ `oneshot --executor direct "what is the capital of sweden?"` executes successfully
3. ✅ Simple mathematical queries work (e.g., "2+2?")
4. ✅ DirectExecutor class properly implements BaseExecutor interface
5. ✅ Worker prompt is transmitted to Ollama via HTTP API
6. ✅ Response is properly formatted and returned
7. ✅ Unit tests cover DirectExecutor functionality (no live Ollama required)
8. ✅ Integration tests validate end-to-end flow
9. ✅ Demo scripts demonstrate basic usage patterns
10. ✅ All existing tests continue to pass (no regressions)
11. ✅ Documentation updated with examples and setup instructions
12. ✅ DirectExecutor can serve worker role with auditor using existing executor

## Testing Strategy

### Unit Tests
- Mock all HTTP calls to Ollama
- Test DirectExecutor class in isolation
- Cover success/error paths
- Test configuration via environment variables

### Integration Tests
- Use mocked API responses to simulate Ollama
- Validate complete oneshot flow
- Test CLI argument parsing
- Ensure proper error messages on failures

### Manual Testing (Optional)
- Install Ollama locally
- Run: `oneshot --executor direct "what is the capital of sweden?"`
- Run: `oneshot --executor direct "2+2?"`
- Verify responses are reasonable

### Demo Validation
- Demo scripts should run without errors
- Demo scripts should produce expected output format
- Demo scripts should handle Ollama not running gracefully

## Risk Assessment

### Low Risk Items
- Adding new executor class (follows existing pattern)
- Mock-based unit testing (no external dependencies required)
- CLI argument additions (backward compatible)

### Medium Risk Items
- HTTP connectivity assumptions (Ollama must be running for real use)
- API response parsing (Ollama API compatibility)
- Documentation accuracy (examples must be correct)

### Mitigation Strategies
- Use clear error messages when Ollama is not reachable
- Include comprehensive error handling for malformed responses
- Document setup requirements clearly
- Provide working demo scripts to validate setup

## Dependencies & Resources

### Required
- `requests` library (already in project dependencies for DirectProvider)
- `httpx` library (already in project dependencies for async DirectProvider)
- Ollama (for manual testing, not required for tests)

### Optional
- Local Ollama instance (for demonstration and manual validation)

## Notes

- This implementation builds on the existing Provider abstraction system already in place
- DirectExecutor follows the same pattern as AiderExecutor and GeminiCLIExecutor
- The focus is on creating a minimal but functional foundation for lang-graph experimentation
- No advanced features required at this stage (tools, complex prompting, etc.)
- Future enhancements can build on this foundation as experimentation progresses
