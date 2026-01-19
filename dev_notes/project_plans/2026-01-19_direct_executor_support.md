# Project Plan: Add Direct Executor Support to Oneshot CLI

## Objective

Implement support for a "direct" executor mode in the oneshot CLI that allows workers to communicate directly with Ollama, enabling the CLI to handle queries like:
```
oneshot --executor direct "what is the capital of sweden?"
```

This provides a foundation for worker role execution and future lang-graph experimentation.

## Implementation Steps

1. **Investigation & Architecture Design**
   - Examine existing executor patterns in the codebase
   - Review current Ollama integration and worker prompt handling
   - Understand how the worker prompt is currently transmitted
   - Design the direct executor module interface to match existing patterns

2. **Direct Executor Implementation**
   - Create a new direct executor module (`src/executors/direct.py` or equivalent)
   - Implement Ollama communication logic that:
     - Receives worker prompts
     - Transmits them to the running Ollama instance
     - Handles response streaming/collection
     - Returns results in the expected format
   - Ensure the executor integrates with the existing executor registration/routing system

3. **CLI Integration**
   - Add `--executor direct` option support to argument parser
   - Route `direct` executor selection to the new direct executor module
   - Ensure backward compatibility with existing executor options
   - Test that the command `oneshot --executor direct "question"` functions correctly

4. **Testing**
   - Create unit tests for direct executor module:
     - Test Ollama connection and communication
     - Test prompt transmission
     - Test response handling
     - Test error cases (Ollama unavailable, malformed responses, etc.)
   - Create demo/integration scripts:
     - Simple arithmetic: `oneshot --executor direct "2+2?"`
     - Geographic question: `oneshot --executor direct "what is the capital of sweden?"`
   - Run full pytest suite to ensure no regressions
   - Verify all existing tests still pass

5. **Documentation Updates**
   - Update CLI usage documentation with `--executor direct` option
   - Add examples of direct executor usage
   - Document prerequisites (Ollama must be running)
   - Document any configuration needed
   - Update any relevant README or getting-started guides

6. **Validation & Cleanup**
   - Verify the command works end-to-end with the running Ollama instance
   - Ensure pytest suite passes completely
   - Clean up any temporary files or test artifacts
   - Confirm all code follows existing patterns and conventions

## Success Criteria

- [ ] `oneshot --executor direct "2+2?"` returns correct result
- [ ] `oneshot --executor direct "what is the capital of sweden?"` returns correct result
- [ ] All new unit tests pass
- [ ] All existing tests still pass (full pytest suite)
- [ ] CLI help/usage documentation includes direct executor
- [ ] No regressions in existing functionality
- [ ] Code follows existing style and patterns

## Testing Strategy

1. **Unit Tests**: Direct executor module tests covering:
   - Ollama connectivity
   - Prompt transmission
   - Response parsing
   - Error handling

2. **Integration Tests**: Demo scripts validating:
   - Simple queries with direct executor
   - Proper result formatting
   - Ollama availability checks

3. **Regression Tests**: Full pytest run ensuring:
   - Existing executors still work
   - No breaking changes to CLI interface

## Risk Assessment

**Low Risk Factors:**
- Feature is additive (new executor mode, doesn't modify existing functionality)
- Ollama is already running and available
- Clear requirements from prompt

**Potential Risks & Mitigation:**
- **Ollama connection failures**: Implement proper error handling and clear error messages if Ollama is unavailable
- **Integration point uncertainty**: May need to investigate existing code patterns first (Step 1) to ensure proper integration
- **Response format compatibility**: Must ensure direct executor responses match expected format for rest of pipeline

