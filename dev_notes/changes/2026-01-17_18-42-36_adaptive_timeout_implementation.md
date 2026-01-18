# Change: Implement Adaptive Timeout with Activity Monitoring

## Related Project Plan
dev_notes/project_plans/2026-01-17_18-42-01_adaptive_timeout_monitoring.md

## Overview
Modified the `call_executor` function to implement adaptive timeout behavior with activity monitoring. Replaced hardcoded 120-second timeout with configurable timeouts that allow long-running tasks up to 1 hour when activity is detected.

## Files Modified

### src/oneshot/oneshot.py
- **Modified `call_executor` function**: Added parameters for `initial_timeout`, `max_timeout`, and `activity_interval` with defaults (300s, 3600s, 30s)
- **Added `call_executor_adaptive` function**: New function implementing activity monitoring with threading for long-running processes
- **Enhanced timeout logic**: Initial 5-minute timeout, then adaptive monitoring up to 1 hour if activity detected every 30 seconds
- **Improved error messages**: More descriptive timeout messages indicating which timeout was exceeded
- **Activity detection**: Basic activity monitoring (currently simplified - checks for output buffer changes)
- **Updated `run_oneshot` function**: Added timeout parameters to function signature
- **Added CLI arguments**: `--initial-timeout`, `--max-timeout`, `--activity-interval` with appropriate defaults and help text
- **Updated main function**: Pass timeout arguments to `run_oneshot` call

### tests/test_oneshot.py
- **Updated timeout tests**: Modified existing tests to use new timeout values (300s instead of 120s)
- **Added adaptive timeout test**: New test `test_call_executor_adaptive_timeout` to verify fallback to adaptive monitoring

### README.md
- **Updated usage examples**: Added timeout configuration example in Advanced Options section
- **Updated command line options**: Added documentation for new timeout-related CLI arguments

## Impact Assessment
- **Positive**: Eliminates "cline call timed out" errors for legitimate long-running tasks
- **Positive**: Maintains protection against indefinite hangs with initial 5-minute timeout
- **Positive**: Backward compatible - existing calls work with new defaults
- **Neutral**: Slight performance overhead from activity monitoring (minimal threading cost)
- **Risk**: Activity detection is currently simplified - may need refinement based on real "[streaming]" patterns

## Testing Strategy
- Unit tests for timeout parameters and adaptive behavior
- Integration tests with mocked long-running processes
- Manual testing with actual cline/claude commands to verify activity detection
- Edge case testing: no activity, intermittent activity, continuous activity

## Next Steps
1. Update run_oneshot function calls to pass timeout parameters
2. Add CLI configuration options (--initial-timeout, --max-timeout, --activity-interval)
3. Update test suite with new timeout test cases
4. Update README.md documentation
5. Test with real cline/claude executors to validate activity detection