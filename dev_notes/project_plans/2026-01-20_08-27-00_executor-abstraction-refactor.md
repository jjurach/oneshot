# Project Plan: Executor Abstraction Refactor

## Objective

Implement a robust executor abstraction layer that consolidates all agent execution logic (cline, claude, gemini, aider, direct) into a unified, extensible architecture. Each executor will encapsulate command selection, activity parsing, and output formatting specific to its agent type, ensuring clean separation of concerns and reducing code duplication.

---

## Implementation Steps

### Phase 1: Base Executor Architecture (Steps 1-5)

- [ ] **Step 1: Design and document base Executor class contract**
  - Review existing `base.py` structure and current executor implementations
  - Define abstract methods: `select_command()`, `parse_activity()`, `format_output()`
  - Document the execution lifecycle and streaming activity model
  - Ensure design supports all five executor types (cline, claude, gemini, aider, direct)

- [ ] **Step 2: Analyze and extract cline executor logic**
  - Extract command selection logic from existing cline integration
  - Identify cline-specific activity parsing patterns from streaming JSON
  - Identify cline-specific output formatting requirements
  - Document behavioral differences from other executors

- [ ] **Step 3: Implement ClineExecutor class**
  - Inherit from base Executor
  - Implement `select_command()` method for cline CLI invocation
  - Implement `parse_activity()` method for cline streaming activity interpretation
  - Implement `format_output()` method to summarize activity to stdout and audit details
  - Isolate all cline-specific logic within this class

- [ ] **Step 4: Analyze and extract claude executor logic**
  - Review Claude Code (claude) execution patterns
  - Extract command selection logic
  - Identify activity parsing patterns (if different from cline)
  - Document output formatting requirements

- [ ] **Step 5: Implement ClaudeExecutor class**
  - Inherit from base Executor
  - Implement executor-specific methods
  - Isolate all Claude-specific logic
  - Ensure compatibility with existing claude executor references

### Phase 2: Additional Executor Implementations (Steps 6-13)

- [ ] **Step 6: Analyze and extract gemini executor logic**
  - Review existing gemini_executor.py implementation
  - Extract command selection, activity parsing, and output formatting
  - Document gemini-specific behaviors

- [ ] **Step 7: Refactor GeminiExecutor (if needed)**
  - Update to match unified base Executor contract if not already compliant
  - Verify command selection method signature
  - Verify activity parsing method signature
  - Verify output formatting method signature

- [ ] **Step 8: Analyze and extract aider executor logic**
  - Review existing aider_executor.py implementation
  - Extract command selection, activity parsing, and output formatting
  - Document aider-specific behaviors and requirements

- [ ] **Step 9: Refactor AiderExecutor (if needed)**
  - Update to match unified base Executor contract
  - Implement required methods with aider-specific logic
  - Test compatibility with existing aider integration

- [ ] **Step 10: Analyze and extract direct executor logic**
  - Review existing direct_executor.py implementation
  - Extract command selection, activity parsing, and output formatting
  - Document direct (OpenAI) execution specifics

- [ ] **Step 11: Refactor DirectExecutor (if needed)**
  - Update to match unified base Executor contract
  - Implement required methods with direct-specific logic
  - Verify API interaction patterns are preserved

- [ ] **Step 12: Create executor factory/registry**
  - Implement factory method or registry to instantiate correct executor by type
  - Add validation to ensure requested executor type is available
  - Document how to register new executor types

- [ ] **Step 13: Update main oneshot module imports and references**
  - Update `__init__.py` to export executor classes and factory
  - Remove any duplicate executor logic from other modules
  - Update existing code to use unified executor interface

### Phase 3: Testing & Validation (Steps 14-21)

- [ ] **Step 14: Create base executor test module**
  - Location: `tests/test_executor_framework.py`
  - Test base class interface and abstract method enforcement
  - Test executor instantiation and configuration
  - Create mock executor for testing base functionality

- [ ] **Step 15: Create streaming activity parser tests**
  - Test activity parsing for each executor type
  - Validate correct extraction of command results and status
  - Test edge cases: malformed activity, empty streams, timeout scenarios
  - Create test fixtures with real activity samples for each executor

- [ ] **Step 16: Create command construction tests**
  - Test command generation for each executor type
  - Validate proper argument escaping and quoting
  - Test with various input configurations
  - Verify commands match expected format for each agent type

- [ ] **Step 17: Create output formatting tests**
  - Test stdout summary generation for each executor type
  - Test audit detail extraction and formatting
  - Validate JSON parsing where applicable
  - Test with streaming activity samples

- [ ] **Step 18: Create cross-executor integration tests**
  - Test executor factory/registry
  - Test switching between executors
  - Test that all executors can handle the same input types
  - Validate consistent output structure across executors

- [ ] **Step 19: Create comprehensive test suite covering all executors**
  - Run all tests from Step 15-18 against all five executor types
  - Document test matrix showing coverage
  - Ensure no executor-specific bugs slip through

- [ ] **Step 20: Create demo script for single executor**
  - Location: `demo_executor_single.py`
  - Build a simple script that demonstrates one executor in action
  - Include a checklist of actions being performed
  - Show real-time streaming output
  - Show final audit output

- [ ] **Step 21: Extend demo script for all executors**
  - Location: `demo_executor_all.py`
  - Modify script to execute demonstration across all executor types
  - Show executor type selection/switching
  - Compare output formats across executors
  - Document any differences in behavior

### Phase 4: Regression Testing & Documentation (Steps 22-24)

- [ ] **Step 22: Run full test suite for all executors**
  - Execute pytest across all executor tests
  - Run existing tests that may depend on executors
  - Ensure no regressions in existing functionality
  - Fix any test failures immediately

- [ ] **Step 23: Integration testing with main oneshot workflow**
  - Test executor usage within full oneshot execution pipeline
  - Verify activity logging captures data correctly for all executors
  - Test error handling and recovery mechanisms
  - Validate that main application still functions correctly

- [ ] **Step 24: Document executor patterns and interfaces**
  - Location: `docs/executor_implementation_guide.md`
  - Create developer guide for implementing new executors
  - Document command selection patterns
  - Document activity parsing patterns
  - Document output formatting patterns
  - Include examples for each executor type

---

## Success Criteria

1. **Base Executor class** properly defines abstract interface with clear documentation
2. **All five executor types** (cline, claude, gemini, aider, direct) inherit from base and implement required methods
3. **All cline-specific logic** is isolated within ClineExecutor class
4. **All executor-specific logic** is isolated within respective executor classes
5. **Command selection** works correctly for all executor types with proper argument handling
6. **Activity parsing** correctly extracts results and status from each executor's streaming output
7. **Output formatting** produces correct stdout summaries and audit details for each executor
8. **Comprehensive test coverage** with 100% pass rate across all executor tests
9. **Demo script** successfully executes a simple task using each executor type independently
10. **Cross-executor demo** shows all executors working and comparable results
11. **No regressions** in existing oneshot functionality
12. **Documentation** is clear and comprehensive for implementing new executors

---

## Testing Strategy

### Unit Tests (Per Executor)
- **Command Construction Tests**: Verify correct command format for each executor type
- **Activity Parser Tests**: Test parsing against real activity samples from each executor
- **Output Formatter Tests**: Validate stdout and audit output for each executor type

### Integration Tests
- **Executor Factory Tests**: Ensure correct executor instantiation by type
- **Cross-Executor Tests**: Verify consistent behavior across different executors
- **Workflow Tests**: Test executor usage within full oneshot pipeline

### End-to-End Tests
- **Demo Script Tests**: Execute demo against each executor type
- **Regression Tests**: Run existing test suite to ensure no breakage
- **Real Usage Tests**: Execute actual tasks with different executors (if feasible)

### Test Coverage Goals
- Minimum 85% code coverage for each executor class
- 100% coverage of critical paths (command selection, activity parsing, output formatting)
- All edge cases documented and tested

---

## Risk Assessment

### High Risk Areas
1. **Breaking existing integration**: Changes to executor interface could break existing code
   - **Mitigation**: Maintain backwards compatibility during refactor; use adapter pattern if needed

2. **Activity parsing regression**: Incorrect parsing could lose audit data
   - **Mitigation**: Preserve exact parsing logic; test against real activity samples extensively

3. **Command format changes**: Incorrect command generation could fail to invoke executors
   - **Mitigation**: Test command construction thoroughly; validate against actual executor requirements

### Medium Risk Areas
4. **Cross-executor compatibility**: Different executors may have incompatible patterns
   - **Mitigation**: Design base class to accommodate all patterns; use flexibility in abstract methods

5. **Streaming output variations**: Each executor may emit different streaming formats
   - **Mitigation**: Create executor-specific parsers; document all format variations

### Low Risk Areas
6. **Documentation drift**: Documentation may become outdated as code evolves
   - **Mitigation**: Update docs during implementation; enforce documentation checks

7. **Performance impact**: Abstraction layer could add overhead
   - **Mitigation**: Keep abstraction minimal; benchmark critical paths if necessary

---

## Notes

- **Code Quality**: Follow existing code patterns, conventions, and typing from current executor implementations
- **Backwards Compatibility**: Preserve existing public APIs where possible; use deprecation warnings if changes are necessary
- **Documentation**: Each executor should have clear docstrings explaining its unique command selection, activity parsing, and output formatting
- **Testability**: Design executors to be easily testable with mock activity streams and command verification
- **Extensibility**: New executor types should be easy to add by inheriting from base Executor and implementing the three key methods

