# Change: Executor Test Failures Identified

## Related Project Plan
dev_notes/project_plans/2026-01-19_10-27-36_test_prompt_functionality.md

## Overview
During execution of the prompt functionality testing plan, several test failures were identified in test_executor.py. The tests are failing because the implementation has been updated to use PTY (pseudo-terminal) execution for real-time streaming, but the tests were written expecting the old synchronous subprocess.run behavior.

## Files Modified
- tests/test_executor.py (examined for test failures)

## Impact Assessment

### Test Failures Identified:
1. **test_call_claude_executor**: Expected mocked "Mock output" but received actual claude CLI error: "Error: Input must be provided either through stdin or as a prompt argument when using --print"

2. **test_call_cline_executor**: Test timed out because it's actually executing the cline command via PTY instead of using the mock

3. **test_call_executor_timeout, test_call_executor_exception, test_call_executor_adaptive_timeout**: These tests fail because the mocking strategy doesn't work with the new PTY-based execution

### Root Cause:
The codebase has been updated to use `call_executor_pty()` for streaming output, but the unit tests still expect the old `subprocess.run()` behavior that was being mocked.

### Recommendations:
- Update tests to properly mock PTY functionality or test actual execution behavior
- Consider adding integration tests that actually run providers if available
- The PTY implementation appears to be working (it's executing real commands), just the tests need updating

### Next Steps:
Continue with demo script testing to verify actual functionality works end-to-end, then address test updates separately.