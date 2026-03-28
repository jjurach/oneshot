# Project Plan: Direct Executor Implementation

## Objective

Enable the `oneshot` CLI to support a `direct` executor mode that can serve as a worker role, allowing execution of simple queries like `oneshot --executor direct "what is the capital of sweden?"`. The direct executor will forward worker prompts to Ollama (currently running `llama-pro:latest`) and provide a foundation for future lang-graph experimentation.

---

## Implementation Steps

### Phase 1: Executor Architecture & Integration
1. **Review existing executor architecture** in the codebase
   - Locate executor interface/base class definitions
   - Understand current executor implementations (if any)
   - Identify how executors are instantiated and invoked

2. **Design the Direct Executor**
   - Create a new executor class that implements the existing executor interface
   - Configure it to forward prompts to Ollama via HTTP/API calls
   - Ensure compatibility with the worker role pattern

3. **Integrate Direct Executor into CLI**
   - Add CLI argument parsing for `--executor direct`
   - Update the main CLI handler to instantiate and use the direct executor
   - Ensure backward compatibility with existing executor modes (if any)

### Phase 2: Core Functionality Implementation
4. **Implement Ollama Communication**
   - Create an Ollama client module for HTTP communication
   - Handle Ollama model inference requests (using `llama-pro:latest`)
   - Parse and return Ollama responses
   - Add error handling for connection failures and API issues

5. **Implement Direct Executor Logic**
   - Create the executor class with required methods
   - Integrate Ollama client into the executor
   - Implement prompt transmission and response handling
   - Test basic execution flow (e.g., "2+2?", "what is the capital of sweden?")

### Phase 3: Testing & Validation
6. **Create Unit Tests**
   - Write pytest tests for the Ollama client module
   - Write pytest tests for the direct executor
   - Test executor instantiation and CLI argument parsing
   - Test prompt transmission and response handling
   - Test error scenarios (connection failures, invalid models, etc.)

7. **Create Demo Scripts**
   - Create standalone demo scripts showing direct executor usage
   - Include simple examples: arithmetic, factual questions, etc.
   - Document how to run demos with provided ollama instance

8. **Run Full Test Suite**
   - Execute all new pytest tests
   - Run global pytest to ensure no regressions
   - Verify all tests pass

### Phase 4: Documentation & Cleanup
9. **Update Usage Documentation**
   - Update CLI help text to include `--executor direct` option
   - Add documentation on direct executor behavior and capabilities
   - Document Ollama dependency and setup requirements
   - Add usage examples to main README or docs

10. **Final Verification**
    - Verify demo scripts execute without errors
    - Verify CLI help text is clear and accurate
    - Test end-to-end workflow: `oneshot --executor direct "2+2?"`

---

## Success Criteria

- ✅ CLI accepts `--executor direct` argument without errors
- ✅ `oneshot --executor direct "what is the capital of sweden?"` executes and returns response from Ollama
- ✅ `oneshot --executor direct "2+2?"` executes and returns response from Ollama
- ✅ All new pytest tests pass
- ✅ Global pytest suite passes (no regressions)
- ✅ Demo scripts execute successfully
- ✅ Usage documentation is updated with direct executor examples
- ✅ Error handling works for connection failures to Ollama

---

## Testing Strategy

1. **Unit Tests (pytest)**
   - Ollama client tests: mock HTTP calls, test request/response handling
   - Direct executor tests: test prompt forwarding, response parsing
   - CLI argument parsing tests: verify `--executor direct` is recognized

2. **Integration Tests**
   - End-to-end tests with actual Ollama instance running
   - Test simple queries: "2+2?", "what is the capital of sweden?"
   - Verify response quality and format

3. **Demo Scripts**
   - Executable Python scripts demonstrating direct executor usage
   - Include examples with various prompt types
   - Document expected output

4. **Regression Testing**
   - Run global pytest suite to ensure existing functionality is not broken
   - Verify any existing executors still work

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Ollama connection issues | Medium | High | Implement robust error handling, connection retry logic, clear error messages |
| Ollama model not responding correctly | Medium | Medium | Test with known working prompts, validate response parsing |
| CLI argument parsing conflicts | Low | Medium | Review existing CLI structure, test with existing commands |
| Performance degradation | Low | Low | Monitor response times, optimize API calls if needed |
| Missing Ollama dependency | High | High | Clear documentation on Ollama setup, explicit error if Ollama unavailable |

---

## Notes

- Ollama is currently running: `llama-pro:latest` with 8192 context window
- This direct executor serves as a foundation for future lang-graph experimentation
- Current implementation focuses on basic prompt forwarding; advanced features (tooling, streaming, etc.) can be added later
- Assumes Ollama is running on standard localhost:11434 (or configurable endpoint)
