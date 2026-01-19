# Project Plan: Direct Executor CLI Support

## Objective

Enable the `--executor direct` flag for the oneshot CLI to support direct HTTP API calls to LLM providers (particularly Ollama). This allows users to run commands like:

```bash
oneshot --executor direct "what is the capital of sweden?"
```

The direct executor will function as a regular executor that can serve the worker role, with initial support for simple API calls and basic task completion. This provides a foundation for future LangGraph/lang-chain experimentation and tool integration.

---

## Implementation Steps

### Phase 1: Expand CLI Argument Support

1. **Update `src/cli/oneshot_cli.py`**
   - Add `--executor direct` as a valid choice (currently: `['claude', 'cline', 'aider']`)
   - This executor will route to the DirectProvider with sensible defaults
   - Ensure `--worker-model` flag works with direct executor (unlike cline)
   - Note: Direct executor is NOT the same as `--worker-provider direct` (which is for API endpoint configuration)

2. **Update `src/oneshot/config.py`**
   - Ensure default configuration supports "direct" as an executor choice
   - Add sensible defaults for direct executor (e.g., ollama endpoint, model)

### Phase 2: Create DirectExecutor Class

1. **Create `src/oneshot/providers/direct_executor.py`**
   - Extend `BaseExecutor` class from `base.py`
   - Implement `run_task(task: str) -> ExecutionResult` method
   - Use `DirectProvider` internally to make API calls to configured endpoint
   - Support ollama as the default provider with `http://localhost:11434/v1/chat/completions`
   - Implement proper error handling and output formatting

2. **Key Implementation Details**
   - Accept configuration for:
     - API endpoint URL (default: Ollama at localhost:11434)
     - Model name (default: llama-pro or configured model)
     - API key (optional for local models)
     - Timeout settings
   - Parse API responses and convert to ExecutionResult format
   - Clean up output (remove ANSI codes, format appropriately)
   - Extract any git-related metadata if applicable

### Phase 3: Integrate DirectExecutor into Executor Factory

1. **Update `src/oneshot/providers/__init__.py`**
   - Extend the executor factory/dispatcher to recognize "direct" executor type
   - Map "direct" executor to DirectExecutor class
   - Pass model name and configuration from CLI args

2. **Update `src/oneshot/oneshot.py`**
   - Ensure legacy API path supports "direct" executor choice
   - Route direct executor through proper execution path

### Phase 4: Testing

1. **Create `tests/test_direct_executor.py`**
   - Unit tests for DirectExecutor initialization
   - Mock tests for API calls (don't require live Ollama instance)
   - Test ExecutionResult generation
   - Test error handling (connection failures, timeouts, API errors)

2. **Create demo scripts in `dev_notes/`**
   - Simple mathematical task: `"2+2?"`
   - Knowledge task: `"what is the capital of sweden?"`
   - Output verification script

3. **Integration tests**
   - Test with live Ollama instance (if available)
   - Test CLI invocation: `oneshot --executor direct "2+2?"`
   - Verify output format and success/failure handling

### Phase 5: Documentation Updates

1. **Update `docs/direct-executor.md`**
   - Document the new CLI support: `--executor direct`
   - Add examples of command-line usage
   - Clarify difference between `--executor direct` and `--worker-provider direct`
   - Document how to configure the Ollama endpoint

2. **Update main README or usage documentation**
   - Add "direct" executor to list of supported executors
   - Include simple usage example

---

## Success Criteria

- [ ] `--executor direct` flag is recognized by CLI parser
- [ ] DirectExecutor class properly extends BaseExecutor
- [ ] Simple math task completes successfully: `oneshot --executor direct "2+2?"`
- [ ] Knowledge task completes successfully: `oneshot --executor direct "what is the capital of sweden?"`
- [ ] Output is properly formatted and wrapped in ExecutionResult
- [ ] All unit tests pass with no live service dependencies
- [ ] Integration tests pass with running Ollama instance
- [ ] Documentation is updated with usage examples
- [ ] CLI help text includes direct executor option

---

## Testing Strategy

### Unit Tests (Can run without Ollama)
```python
# Mock DirectProvider responses
# Test DirectExecutor initialization
# Test ExecutionResult generation
# Test error handling paths
```

### Integration Tests (Requires Ollama running)
```bash
# Start Ollama: ollama serve (or verify already running)
# Test CLI: oneshot --executor direct "2+2?"
# Verify output contains answer
# Test session logging
```

### Demo Scripts
```bash
# Run simple math test
python dev_notes/demo_direct_executor_math.py

# Run knowledge test
python dev_notes/demo_direct_executor_knowledge.py

# Run full CLI test
oneshot --executor direct "what is 5+3?"
```

---

## Risk Assessment

### Low Risk
- DirectProvider already exists and is functional
- BaseExecutor abstract class is stable
- CLI argument parsing is already extensible
- Integration with existing code follows established patterns

### Medium Risk
- Ollama endpoint may not be available/running during testing
  - **Mitigation:** Mock DirectProvider in unit tests, document Ollama requirement for integration tests
- DirectExecutor behavior may differ from other executors
  - **Mitigation:** Keep implementation simple initially, follow existing patterns from AiderExecutor

### Potential Issues
- Timeout or connectivity issues with Ollama
  - **Mitigation:** Implement robust error handling, clear error messages
- Output format inconsistencies between different models/endpoints
  - **Mitigation:** Standardize output parsing, normalize whitespace

---

## Architecture Notes

### Executor Hierarchy
```
BaseExecutor (abstract)
├── AiderExecutor
├── GeminiExecutor
└── DirectExecutor (NEW)
    └── Uses DirectProvider internally
```

### CLI Flow for `--executor direct`
```
CLI Parser
  ├── Parse --executor direct
  ├── Parse --worker-model (required for direct)
  └── Executor Factory
      └── Create DirectExecutor
          └── Create DirectProvider
              └── Call Ollama API
```

### Distinction: `--executor direct` vs `--worker-provider direct`
- **`--executor direct`**: New feature - direct executor type, subprocess-like role
- **`--worker-provider direct`**: Existing feature - provider configuration for APIs

Both may eventually work together but serve different purposes.

---

## Future Considerations

- Tool integration for function calling (LangGraph Phase 1)
- Context augmentation and RAG (LangGraph Phase 2)
- State machine and multi-step reasoning (LangGraph Phase 3)
- Support for streaming responses (if Ollama supports it)
- Rate limiting and response caching

---

## Dependencies

- Existing `DirectProvider` in `src/oneshot/providers/__init__.py`
- BaseExecutor class in `src/oneshot/providers/base.py`
- Running Ollama instance (for integration tests): llama-pro model
- Python unittest or pytest framework

---

## Files to be Created/Modified

### New Files
- `src/oneshot/providers/direct_executor.py` - DirectExecutor implementation
- `tests/test_direct_executor.py` - Unit tests
- `dev_notes/demo_direct_executor_math.py` - Math demo script
- `dev_notes/demo_direct_executor_knowledge.py` - Knowledge demo script

### Modified Files
- `src/cli/oneshot_cli.py` - Update executor choices and argument parsing
- `src/oneshot/config.py` - Add direct executor defaults if needed
- `src/oneshot/providers/__init__.py` - Add DirectExecutor to factory
- `src/oneshot/oneshot.py` - Ensure legacy API path supports direct
- `docs/direct-executor.md` - Update documentation
