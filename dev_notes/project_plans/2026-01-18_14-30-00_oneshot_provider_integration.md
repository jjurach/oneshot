# Project Plan: Oneshot Autonomous Executor Providers Integration

## Objective
Design and implement a robust CLI-first integration strategy for three high-performance Autonomous Executor Providers: Aider, Roo Code, and Gemini CLI. Create a flexible, secure, and type-safe implementation that allows oneshot to delegate tasks to these agents in a fully headless, non-interactive manner.

## Implementation Steps
1. Establish Base Executor Class
   - Create `oneshot/providers/base.py` with `BaseExecutor` abstract base class
   - Define common interface methods:
     * `run_task(task: str) -> ExecutionResult`
     * Error handling and logging mechanisms
     * Type hinting and docstrings

2. AiderExecutor Implementation
   - Create `oneshot/providers/aider_executor.py`
   - Implement command line configuration:
     * Use `--message "{task}"`
     * Add `--yes-test --no-stream` flags
   - Capture git commit hash from Aider output
   - Implement cleanup for `.aider.chat.history.md`
   - Sanitize environment variables for API keys

3. GeminiCLIExecutor Implementation
   - Create `oneshot/providers/gemini_executor.py`
   - Implement `--prompt "{task}" --yolo` command
   - Design log filtering for "Action" and "Observation" steps
   - Ensure uninterrupted terminal operations

4. Shared Utilities
   - Implement `_run_command` utility in base or utils module
     * STDOUT/STDERR merging
     * ANSI color code stripping
   - Secure API key environment mapping

5. Error Handling and Logging
   - Develop comprehensive error handling for each provider
   - Create detailed logging mechanism
   - Ensure clean text output for Auditor review

## Success Criteria
- All three providers (Aider, Roo Code, Gemini CLI) can be instantiated and run tasks
- Providers inherit from `BaseExecutor`
- Git commit hash captured for Aider
- Minimal log pollution
- Secure handling of API keys
- Consistent error handling across providers

## Testing Strategy
1. Unit Tests
   - Test each provider's `run_task` method
   - Verify error handling
   - Check git commit hash extraction
   - Validate log filtering

2. Integration Tests
   - Run sample tasks through each provider
   - Verify Auditor can process execution results
   - Test different task scenarios

3. Security Tests
   - Validate API key handling
   - Check for potential environment variable leaks

## Risk Assessment
- Potential Risks:
  * Inconsistent output formats from different providers
  * API key security vulnerabilities
  * Unexpected task execution behaviors

- Mitigation Strategies:
  * Robust input validation
  * Comprehensive error handling
  * Strict type checking
  * Secure environment variable management

- Fallback Mechanisms:
  * Graceful degradation if a provider fails
  * Detailed error reporting
  * Ability to skip or retry tasks