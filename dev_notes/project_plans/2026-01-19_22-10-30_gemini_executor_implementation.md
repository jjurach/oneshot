# Project Plan: Introduce `--executor gemini` Feature for Oneshot Task Execution

## Objective

Implement a new `--executor gemini` command-line option for the Gemini CLI that enables execution of oneshot tasks using the Gemini backend. This feature should allow users to pipe input into the gemini command with the executor option to run tasks with Gemini's execution capabilities, similar to the existing streaming-json functionality demonstrated in the request.

## Implementation Steps

### Step 1: Analyze Existing Codebase
- Identify the current CLI argument parsing structure
- Locate existing `--output-format stream-json` and `--approval-mode yolo` implementation
- Understand how oneshot tasks are currently structured
- Map out where executor logic should be integrated

### Step 2: Design Executor Interface
- Define the `--executor gemini` option specification
- Determine how executor options interact with existing flags (`--output-format`, `--approval-mode`)
- Specify what happens when `--executor gemini` is used with various output formats
- Document expected behavior and error cases

### Step 3: Implement Core Executor Logic
- Create executor abstraction/interface if it doesn't exist
- Implement Gemini executor backend
- Integrate with existing CLI argument parsing
- Handle executor selection and initialization
- Ensure compatibility with streaming JSON output format

### Step 4: Create Demo Script
- Create a demo script (e.g., `demo_gemini_executor.py` or similar) that:
  - Shows how to use `--executor gemini` with various inputs
  - Demonstrates integration with `--output-format stream-json`
  - Shows integration with `--approval-mode yolo`
  - Provides clear usage examples for users
  - Includes comments explaining what each example does

### Step 5: Write Comprehensive Unit Tests
- Create test file `test_gemini_executor.py` (or add to existing test suite) with tests for:
  - Executor initialization and configuration
  - CLI argument parsing with `--executor gemini`
  - Executor with various output format combinations
  - Executor with different approval modes
  - Error handling (invalid executor names, missing dependencies, etc.)
  - Integration tests showing end-to-end oneshot execution
  - Streaming JSON output validation from Gemini executor

### Step 6: Validate Global Test Suite
- Run the global pytest suite to ensure no regressions
- Verify all new tests pass
- Ensure code follows existing patterns and conventions

### Step 7: Documentation and Cleanup
- Update CLI help text to document the new `--executor gemini` option
- Add usage examples to relevant documentation files
- Clean up any temporary files created during development

### Step 8: Commit Work
- Create a git commit with all changes
- Reference the project plan in the commit message

## Success Criteria

1. ✓ `--executor gemini` flag is recognized by the CLI
2. ✓ Users can execute oneshot tasks with `--executor gemini`
3. ✓ Feature works seamlessly with `--output-format stream-json`
4. ✓ Feature works with `--approval-mode yolo` and other approval modes
5. ✓ Demo script successfully demonstrates the feature
6. ✓ All new unit tests pass (minimum 80% code coverage for new executor code)
7. ✓ All existing tests continue to pass (no regressions)
8. ✓ Code follows existing conventions, patterns, and styling

## Testing Strategy

### Unit Tests
- Test executor initialization
- Test CLI argument parsing
- Test output format compatibility
- Test error handling and edge cases
- Mock Gemini API calls to avoid dependency on external services

### Integration Tests
- Test end-to-end oneshot execution with `--executor gemini`
- Test streaming JSON output validation
- Test with multiple approval modes

### Demo Script Validation
- Execute demo script and verify it completes without errors
- Verify output format matches expected stream-json structure
- Verify example use cases work as intended

### Regression Testing
- Run global pytest suite
- Verify no breaking changes to existing CLI functionality

## Risk Assessment

### Low Risk Areas
- New CLI flag addition (isolated from existing code)
- Demo script creation (independent utility)
- Unit tests (don't affect production code)

### Medium Risk Areas
- Integration with existing CLI argument parsing (could break existing functionality if not careful)
- Interaction with output formats (must preserve compatibility)

### Mitigation Strategies
- Thoroughly test CLI argument parsing with existing flags
- Test all combinations of new flag with existing flags
- Run full regression test suite before committing
- Follow existing code patterns to maintain consistency
- Use clear naming conventions to distinguish new code

## Notes

- The existing Gemini CLI appears to already support the core streaming-json output format with tool execution
- This feature builds on proven functionality demonstrated in the request
- Implementation should leverage existing patterns in the codebase
- Demo script should serve as both documentation and usage example
