# Project Plan: Implement Adaptive Timeout with Activity Monitoring

## Objective
Address "cline call timed out" errors by implementing adaptive timeout thresholds and activity monitoring for long-running agent tasks. Allow agents to run for up to 10 minutes or 1 hour while monitoring for activity indicators.

## Implementation Steps

### 1. Analyze Current Timeout Implementation
- Review `call_executor` function in `src/oneshot/oneshot.py`
- Document current hardcoded 120-second timeout for both claude and cline executors
- Understand subprocess execution patterns and output capture

### 2. Design Adaptive Timeout System
- Implement configurable timeout parameters:
  - Initial timeout: 5 minutes (300 seconds)
  - Activity extension: up to 1 hour (3600 seconds) if streaming detected
  - Activity check interval: 30 seconds
- Add activity monitoring for "[streaming]" patterns in output
- Create new timeout configuration options

### 3. Modify call_executor Function
- Replace hardcoded timeout with adaptive timeout logic
- Implement streaming output monitoring
- Add timeout configuration parameters
- Maintain backward compatibility with existing behavior

### 4. Add Command Line Configuration
- Add new CLI arguments for timeout configuration:
  - `--initial-timeout`: Initial timeout before activity check (default: 300s)
  - `--max-timeout`: Maximum allowed timeout with activity (default: 3600s)
  - `--activity-interval`: How often to check for activity (default: 30s)
- Update argument parsing in main()

### 5. Update Tests
- Modify existing timeout tests in `tests/test_oneshot.py`
- Add new tests for adaptive timeout behavior
- Test activity monitoring scenarios

### 6. Update Documentation
- Update README.md with new timeout options
- Document behavior changes for long-running tasks

## Success Criteria
- Agents can run for up to 1 hour when showing activity every 30 seconds
- Initial 5-minute timeout prevents indefinite hangs
- Backward compatibility maintained for existing usage
- Clear error messages when timeouts occur
- Activity monitoring works for both claude and cline executors

## Testing Strategy
- Unit tests for timeout logic and activity detection
- Integration tests with mocked long-running processes
- Manual testing with actual claude/cline commands
- Test edge cases: no activity, intermittent activity, continuous activity

## Risk Assessment
- **Low**: Breaking existing functionality - will maintain backward compatibility
- **Medium**: Complex subprocess monitoring - requires careful implementation of streaming detection
- **Low**: Performance impact - monitoring adds minimal overhead
- **Low**: Cross-platform compatibility - uses standard subprocess features

This plan addresses the core timeout issue while implementing the requested activity monitoring. The adaptive approach balances preventing indefinite hangs with allowing legitimate long-running tasks.