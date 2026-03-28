# Project Plan: Direct Executor CLI Integration

## Objective

Implement CLI support for the "direct" executor mode to enable oneshot to accept commands like:
```
oneshot --executor direct "what is the capital of sweden?"
```

The direct executor will serve as a foundation for LangGraph experimentation and will support local models via Ollama (currently running llama-pro:latest on GPU).

## Implementation Steps

### Phase 1: CLI Integration

1. **Analyze current executor support in CLI**
   - Review `src/oneshot/oneshot.py` argument parser
   - Review `src/oneshot/cli.py` for entry point configuration
   - Document current executor registration pattern (cline, gemini, aider, etc.)

2. **Create DirectExecutor wrapper class**
   - Create `src/oneshot/providers/direct_executor.py` as a new executor implementation
   - Implement BaseExecutor interface consistent with existing executors
   - Support configuration via CLI flags for:
     - `--endpoint`: API endpoint (default: `http://localhost:11434/v1/chat/completions` for Ollama)
     - `--model`: Model name (default: `llama-pro`)
     - `--timeout`: Request timeout in seconds (default: 30)
   - Leverage existing DirectProvider from `src/oneshot/providers/base.py` or create new if needed

3. **Update CLI argument parser**
   - Add `--executor direct` as valid executor choice
   - Add optional flags: `--endpoint`, `--model`, `--timeout`
   - Add validation to ensure Ollama endpoint is reachable before execution
   - Add help text documenting direct executor usage

4. **Register executor in provider registry**
   - Update executor discovery/registration mechanism to include direct executor
   - Ensure executor is properly imported and registered on startup

5. **Implement run logic**
   - Create execution flow that:
     - Accepts task description as positional argument
     - Sends prompt to configured LLM endpoint
     - Handles streaming or buffered response based on model capability
     - Formats output consistently with other executors
     - Returns success/failure status

### Phase 2: Testing

1. **Create unit tests** in `tests/test_direct_executor.py`
   - Test DirectExecutor initialization with various configs
   - Test endpoint validation (success, connection refused, timeout)
   - Test prompt formatting and API call generation
   - Test response parsing from Ollama/OpenAI-compatible endpoints
   - Test error handling (invalid config, network errors, malformed responses)
   - Mock HTTP calls to avoid requiring running Ollama during tests

2. **Create demo/integration test script**
   - Create `demo_direct_executor.py` in project root
   - Demonstrate basic usage: `oneshot --executor direct "what is 2+2?"`
   - Demonstrate with custom endpoint/model flags
   - Include examples for capital of Sweden, 2+2, etc.
   - Check if Ollama is running and provide helpful error message if not
   - Can be run manually to test against live Ollama instance

3. **Run existing pytest suite**
   - Ensure all existing tests still pass with new executor added
   - Verify no regressions in CLI or provider infrastructure

### Phase 3: Documentation Updates

1. **Update README.md**
   - Add section explaining "direct" executor mode
   - Include usage examples for oneshot CLI with `--executor direct`
   - Explain Ollama setup requirements (ollama run llama-pro)
   - Document CLI flags: `--endpoint`, `--model`, `--timeout`

2. **Update `docs/direct-executor.md`** (already exists, may need updates)
   - Add CLI integration section
   - Document new executor registration mechanism
   - Update implementation roadmap

3. **Add usage documentation**
   - Create section in docs explaining how to use direct executor for LangGraph experimentation
   - Provide quick-start guide for Ollama users

## Success Criteria

1. ✅ CLI accepts `oneshot --executor direct "prompt"` and executes against Ollama
2. ✅ Response from llama-pro model is properly formatted and returned
3. ✅ Simple queries like "what is 2+2?" return correct outputs
4. ✅ Custom endpoint/model/timeout flags are respected
5. ✅ Helpful error messages when Ollama is not available
6. ✅ All unit tests pass with 100% success rate
7. ✅ Demo script demonstrates working integration
8. ✅ Documentation is updated and clear
9. ✅ No regressions in existing executor functionality

## Testing Strategy

### Unit Testing
- Mock HTTP requests to avoid Ollama dependency
- Test all configuration combinations
- Test error conditions (network timeouts, invalid responses, etc.)
- Test response parsing for various output formats
- Verify executor interface compliance

### Integration Testing
- Demo script with optional live Ollama connection
- Test against running Ollama instance if available
- Verify CLI argument parsing and routing
- Test executor registration in provider system

### Manual Testing
- Run `oneshot --executor direct "2+2?"`
- Run `oneshot --executor direct "what is the capital of sweden?"`
- Run with custom endpoint: `oneshot --executor direct --endpoint http://localhost:8000/v1/chat/completions "prompt"`
- Verify helpful error when Ollama is not running

## Risk Assessment

### Low Risk
- ✅ Adding new executor doesn't require modifying existing executors
- ✅ Using standard OpenAI-compatible API format
- ✅ Ollama is already running and stable
- ✅ Follows established executor pattern from existing implementations

### Medium Risk
- ⚠️ Network timeout configuration needs sensible defaults
- ⚠️ Error handling for various failure modes (connection refused, malformed responses)
- ⚠️ Streaming output handling consistency

### Mitigation
- Use conservative timeout defaults (30 seconds)
- Implement comprehensive error handling with user-friendly messages
- Test response parsing thoroughly before deployment
- Provide clear documentation on configuration options

## Related Documentation
- `docs/direct-executor.md` - Architecture and integration roadmap
- `AGENTS.md` - Project workflow and documentation standards
- `pyproject.toml` - Entry point configuration
- `src/oneshot/oneshot.py` - CLI main entry point
- `src/oneshot/providers/` - Existing executor implementations
