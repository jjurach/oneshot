# Project Plan: Unified Executor Streaming Implementation

## Objective
Implement real-time streaming output from both Claude and Cline CLI executors to enable:
1. Real-time visibility of executor progress during subprocess execution
2. Structured JSON output parsing for better data extraction
3. Enhanced activity monitoring through multiple detection mechanisms
4. Improved user experience with immediate feedback vs. buffered output

## Problem Statement
Both Claude and Cline executors currently suffer from the same fundamental limitation: `subprocess.run()` with `capture_output=True` buffers all output until the subprocess completes. This prevents:
- Real-time progress visibility during long-running tasks
- Immediate feedback for iterative work
- Effective activity monitoring based on output
- Optimal user experience with streaming-capable CLI tools

### Root Cause: POSIX Pipe Buffering
1. **POSIX pipes are fully buffered**: When stdout/stderr is redirected through a pipe, subprocesses buffer output in large blocks
2. **Terminal streams are line-buffered**: When output goes to a TTY, it's typically line-buffered
3. **CLI tools detect TTY**: Many CLI tools (including Claude and Cline) use `isatty()` to detect terminals and adjust buffering accordingly

## Solution Overview

### Multi-Pronged Approach
1. **PTY Allocation**: Force CLI tools to detect a TTY and use line-buffering
2. **JSON Streaming**: Use `--output-format json` (Cline) and `--output-format stream-json` (Claude) for structured output
3. **File-Based Activity Monitoring**: Monitor task files in `$HOME/.cline/data/tasks/$task_id` as a fallback activity indicator
4. **Unbuffered I/O**: Set `bufsize=0` and use `stdout=PIPE, stderr=PIPE` for real-time reading

## Implementation Steps

### Phase 1: Research and Analysis (Completed)
- [x] Analyze buffering behavior in POSIX pipes vs TTY
- [x] Research PTY allocation solutions using `pty` module
- [x] Analyze Cline's `--output-format json` functionality
- [x] Map out Cline's task directory structure at `$HOME/.cline/data/tasks/$task_id`
- [x] Document current oneshot subprocess handling patterns
- [x] Review Claude CLI `--output-format stream-json` behavior

### Phase 2: Core PTY-Based Streaming Implementation
#### Step 2.1: PTY Infrastructure
- [ ] Create `call_executor_pty()` function in `src/oneshot/oneshot.py`
- [ ] Implement master/slave PTY setup using `pty.openpty()`
- [ ] Add line-by-line or fixed-buffer reading from master PTY (1024 byte buffers)
- [ ] Handle subprocess exit code and completion
- [ ] Add proper exception handling for PTY errors (OSError, IOError)
- [ ] Implement platform detection (warn or skip on Windows)
- [ ] Add try/finally blocks for cleanup to avoid zombie processes
- [ ] Handle SIGHUP and signal cleanup when master PTY closes

#### Step 2.2: Integrate PTY with Existing Executors
- [ ] Modify `call_executor()` in `src/oneshot/oneshot.py:331-449` to use PTY approach
- [ ] Update `call_executor_adaptive()` to leverage PTY infrastructure
- [ ] Ensure `call_executor_async()` can handle streaming output
- [ ] Add fallback to `capture_output=True` if PTY allocation fails
- [ ] Add environment variable `ONESHOT_DISABLE_STREAMING=1` for fallback control

#### Step 2.3: JSON Streaming Output
- [ ] Add `--output-format json` flag to Cline command construction
- [ ] Verify Claude CLI already uses `--output-format stream-json`
- [ ] Implement streaming JSON parser for real-time object extraction
- [ ] Handle partial JSON messages during streaming (buffer incomplete objects)
- [ ] Integrate with existing lenient JSON parsing logic
- [ ] Gracefully degrade when JSON output is malformed
- [ ] Collect complete output while displaying line-by-line for later JSON extraction

### Phase 3: File-Based Activity Monitoring (Cline-Specific)
- [ ] Create `get_cline_task_dir(task_id)` function to locate task directory
- [ ] Implement `monitor_task_files(task_dir, callback)` for file change detection
- [ ] Use `os.stat()` or `pathlib.Path.stat()` to check modification times
- [ ] Add polling mechanism with configurable interval (default: 5 seconds)
- [ ] Implement fallback to process monitoring if file monitoring fails
- [ ] Add error handling for permission issues accessing task directories
- [ ] Create abstraction layer to switch between file and process monitoring methods

### Phase 4: Timeout and Activity Detection
- [ ] Modify timeout logic to work with streaming output
- [ ] Ensure `subprocess.TimeoutExpired` exceptions are handled correctly
- [ ] Implement activity detection based on streaming output timestamps
- [ ] Integrate file-based activity monitoring for Cline
- [ ] Add deadlock prevention (PTY avoids pipe deadlock naturally)
- [ ] Test timeout behavior with long-running streaming tasks

### Phase 5: Memory and Performance Optimization
- [ ] Optimize memory usage during streaming operations (avoid unbounded buffering)
- [ ] Test with very large streaming outputs to prevent memory issues
- [ ] Implement connection pooling for file monitoring if needed
- [ ] Balance memory usage with user experience for large outputs
- [ ] Test CPU overhead of streaming vs buffered execution

### Phase 6: Testing and Validation
#### Unit Tests
- [ ] Mock PTY behavior for testability
- [ ] Test JSON output parsing with various message formats
- [ ] Test timeout handling during streaming
- [ ] Test partial JSON line buffering and completion
- [ ] Validate file-based activity detection logic (Cline)
- [ ] Test platform detection for Windows fallback

#### Integration Tests
- [ ] Test complete oneshot workflow with Claude streaming
- [ ] Test complete oneshot workflow with Cline streaming
- [ ] Test with simple prompts to verify real-time output
- [ ] Verify stream-json output is streamed (not buffered)
- [ ] Test with `--verbose` flag to see debug logs
- [ ] Verify activity monitoring during long-running tasks
- [ ] Test timeout behavior with streaming (clean process termination)
- [ ] Test error handling when CLI doesn't support streaming flags
- [ ] Test file monitoring with actual Cline tasks (requires Cline installation)
- [ ] Verify fallback behavior when task directories are inaccessible
- [ ] Ensure existing tests pass with new streaming implementation

#### Performance Experiments
- [ ] **Experiment 1: Buffer Size Impact**
  - Test bufsize=0, 1024, 4096, 8192, and default
  - Measure output latency from process start to first output received
  - Compare memory usage across different buffer sizes
  - Identify optimal buffer size for streaming performance

- [ ] **Experiment 2: Activity Detection Accuracy**
  - Run long-running tasks with both monitoring methods
  - Compare false positive/negative rates between file and process monitoring
  - Test with different task types (coding, file operations, API calls)
  - Measure detection latency for each method

- [ ] **Experiment 3: Resource Usage Comparison**
  - Monitor CPU usage during streaming vs buffered execution
  - Measure memory consumption over time for long-running tasks
  - Test impact on system responsiveness during execution
  - Compare overhead of PTY vs pipe-based execution

- [ ] **Experiment 4: JSON Parsing Performance**
  - Benchmark JSON parsing speed for complete vs partial messages
  - Test memory usage with large JSON objects during streaming
  - Validate parsing accuracy with malformed or incomplete JSON
  - Test graceful degradation with non-JSON output mixed in

- [ ] **Experiment 5: PTY vs Line-Buffered Reading**
  - Compare PTY allocation vs `bufsize=1` + `universal_newlines=True`
  - Measure latency differences for line-terminated output
  - Test with non-line-terminated JSON streaming
  - Determine best approach for each executor type

#### Regression Tests
- [ ] Ensure existing Claude executor functionality unchanged
- [ ] Ensure existing Cline executor functionality unchanged
- [ ] Verify non-streaming executors still work correctly
- [ ] Test error handling for malformed JSON streams
- [ ] Verify no performance regression vs current implementation
- [ ] Run `pytest tests/test_oneshot.py -v` and ensure all pass

#### Manual Testing
- [ ] Run oneshot with long-running Claude task, observe real-time output
- [ ] Run oneshot with long-running Cline task, observe real-time output
- [ ] Verify session logs contain complete output
- [ ] Monitor for any performance regression
- [ ] Test on multiple platforms (Linux, macOS)
- [ ] Verify no new warnings or errors in debug logs

### Phase 7: Documentation and Deployment
- [ ] Document the PTY streaming implementation approach
- [ ] Add comments explaining PTY setup and limitations
- [ ] Update function documentation with new streaming parameters
- [ ] Add configuration options for enabling/disabling streaming features
- [ ] Document Windows platform limitations (no PTY support)
- [ ] Create migration guide for users upgrading to streaming version
- [ ] Update README with new streaming capabilities
- [ ] Update `docs/direct-executor.md` with streaming behavior
- [ ] Update `CLAUDE.md` or `AGENTS.md` if streaming becomes configurable
- [ ] Remove or archive old `call_executor_adaptive()` if no longer needed
- [ ] Consider adding `--no-streaming` CLI flag for testing

### Phase 8: Post-Implementation
- [ ] Commit changes with clear message about streaming implementation
- [ ] Monitor for edge cases in production use
- [ ] Consider performance metrics collection for streaming overhead
- [ ] Add Slack notification upon commit (if MCP support available)

## Success Criteria

### Primary Goals
1. **Real-time Progress**: Users see iterative executor progress reports while subprocess runs (not after completion)
2. **Streaming Latency**: Real-time streaming achieved with <100ms latency for output processing
3. **JSON Extraction Works**: Can still extract complete JSON objects from captured output for auditor processing
4. **Activity Monitoring**: File-based activity monitoring detects Cline task progress with >95% accuracy
5. **No Breaking Changes**: Existing functionality preserved; streaming is transparent enhancement
6. **Timeout Still Works**: Activity monitoring and timeouts function correctly with streaming
7. **No Regression**: No regression in existing functionality for non-streaming executors or buffered execution

### Secondary Goals
8. **Clean Implementation**: Code follows existing patterns; well-integrated with current architecture
9. **Performance**: Performance benchmarks show measurable improvements in responsiveness
10. **All Tests Pass**: All existing tests pass with new streaming implementation
11. **Documentation**: Implementation is documented for future maintainers
12. **Cross-Platform**: Graceful fallback on Windows (no PTY support)

## Testing Strategy Summary

### Three-Tiered Testing Approach
1. **Unit Tests**: Mock PTY behavior, test JSON parsing, test file monitoring logic
2. **Integration Tests**: Real CLI invocations, end-to-end workflow tests, timeout handling
3. **Performance Experiments**: Quantitative measurements of latency, memory, CPU, accuracy

### Test Coverage Goals
- PTY allocation and cleanup: 100%
- JSON parsing (complete and partial): 100%
- File-based activity monitoring: 100%
- Timeout handling with streaming: 100%
- Platform detection and fallback: 100%
- Error handling (PTY failures, malformed JSON): 100%

## Risk Assessment

### High Risk
- **JSON streaming breakage**: JSON streaming could break existing parsing logic if CLI output format changes
  - *Mitigation*: Implement graceful degradation and fallback to line-based parsing
- **PTY platform compatibility**: PTY behavior differs across Unix variants; no Windows support
  - *Mitigation*: Add comprehensive platform detection and fallback to buffered execution

### Medium Risk
- **File-based monitoring**: Cline may change task storage location/format in future versions
  - *Mitigation*: Implement fallback to process monitoring; version detection
- **Signal handling issues**: PTY processes require special signal handling
  - *Mitigation*: Use try/finally blocks; proper SIGHUP handling
- **Memory usage with large outputs**: Very large streaming outputs could cause memory issues
  - *Mitigation*: Implement bounded buffers; test with large outputs

### Low Risk
- **Performance overhead**: Streaming may add minor CPU/memory overhead
  - *Mitigation*: Performance improvements are additive; can be disabled with feature flags
- **Line-buffered fallback**: Line-buffered reading (Phase 1) as proven intermediate solution
  - *Mitigation*: Existing `capture_output=True` approach still works

### Mitigation Strategies
- Implement feature flags to enable/disable streaming (fallback to current behavior)
- Add environment variable `ONESHOT_DISABLE_STREAMING=1` for emergency rollback
- Start testing with line-buffered reading before full PTY implementation
- Add comprehensive error handling for PTY failures
- Test on multiple platforms (Linux, macOS) before release
- Consider optional `ptyprocess` package for more robust PTY handling

## Dependencies & Resources

### Python Standard Library (No New Dependencies Required)
- `pty` module: Built-in for PTY allocation
- `os` module: Already imported; used for file descriptor operations
- `select` module: Optional for cross-platform async reading (if needed)
- `subprocess` module: Already used; will be modified for PTY integration

### Optional Enhancement
- `ptyprocess` package: More robust PTY handling; better edge case support
  - Installation: `pip install ptyprocess`
  - Benefit: Works on more platforms; better Windows fallback behavior
  - *Decision*: Evaluate during implementation; start with built-in `pty` module

## Critical Implementation Details

### Deadlock Prevention
- PTY approach naturally avoids pipe deadlock because PTYs use different buffering strategy
- No need for threading/select() monitoring with PTY (simplified implementation)
- Must still handle `subprocess.TimeoutExpired` exceptions for timeout support

### Cross-Platform Compatibility
- PTY is Unix/Linux only (not available on Windows)
- Need fallback to buffered execution for Windows environments
- Add platform detection to warn users on Windows
- Consider `ptyprocess` library for better cross-platform support

### Signal Handling
- PTY processes may need special signal handling (SIGHUP when master closes)
- Must properly close master PTY descriptor to avoid zombie processes
- Use try/finally to ensure cleanup even on exceptions

### Output Capture Strategy
- While streaming output to terminal/logs, must also capture for JSON extraction
- Need to collect complete output while displaying it line-by-line
- Balance between memory (for large outputs) and user experience
- Implement bounded buffers to prevent unbounded memory growth

## Files to Modify

### Primary Changes
1. **`src/oneshot/oneshot.py`** (Lines 331-449)
   - Add `call_executor_pty()` function
   - Modify `call_executor()` to use PTY approach instead of `capture_output=True`
   - Update `call_executor_adaptive()` if needed
   - Update `call_executor_async()` for async version
   - Add JSON streaming parser
   - Add file-based activity monitoring functions for Cline

### Optional Changes
2. **`src/oneshot/providers/__init__.py`**
   - Update ExecutorProvider if needed to support streaming configuration

### Documentation Updates
3. **`docs/direct-executor.md`**: Update streaming behavior documentation
4. **`CLAUDE.md`**: Mention streaming output improvement
5. **`AGENTS.md`**: Document streaming configuration if it becomes configurable

### Testing
6. **`tests/test_oneshot.py`**: Add comprehensive tests for streaming functionality

## Related Files (Read-Only Reference)
- `docs/overview.md`: Project architecture understanding
- `src/oneshot/task.py`: OneshotTask for async handling patterns
- `tests/test_oneshot.py`: Existing test patterns

## Success Indicators (Post-Implementation Checklist)

After implementation, verify:
1. ✓ Running `oneshot 'long task'` with Claude shows progress in real-time
2. ✓ Running `oneshot 'long task'` with Cline shows progress in real-time
3. ✓ Session logs contain complete JSON output
4. ✓ Auditor receives all expected data from worker
5. ✓ No performance regression vs current implementation
6. ✓ Tests pass: `pytest tests/test_oneshot.py -v`
7. ✓ No new warnings or errors in debug logs
8. ✓ File-based activity monitoring works for Cline tasks
9. ✓ Timeout behavior still works correctly with streaming
10. ✓ Graceful fallback on Windows (or clear warning)

## Notes & Observations

### Unified Understanding
- Both Claude and Cline executors suffer from the same root cause (POSIX pipe buffering)
- PTY allocation is the comprehensive solution for both executors
- JSON structured output provides better data extraction than text parsing
- File-based monitoring offers a unique advantage for Cline (task directory visibility)

### Implementation Priorities
1. **Highest Priority**: PTY-based streaming (solves core problem for both executors)
2. **High Priority**: JSON parsing for structured output
3. **Medium Priority**: File-based activity monitoring for Cline
4. **Lower Priority**: Performance optimization and tuning

### Current Implementation Context
- `call_executor()` at line 331 currently uses `subprocess.run()` with `capture_output=True`
- Claude CLI invoked with `['claude', '-p', '--output-format', 'stream-json', '--verbose']`
- Cline executor should add `--output-format json` flag
- Prompt passed via `input=prompt` parameter
- Output currently buffered until process completes
- Model optionally specified with `--model` flag
- `call_executor_adaptive()` exists but also uses pipes
- Async version in `call_executor_async()` delegates to sync version

### Key Technical Insights
- `capture_output=True` is equivalent to `stdout=PIPE, stderr=PIPE`
- POSIX pipes default to full buffering (not line buffering) in subprocess context
- PTY allocation forces CLI tools to believe they're in an interactive terminal
- `pty.openpty()` returns (master, slave) file descriptors (not file objects)
- Master must be read before slave can be used by subprocess
- Line-buffered reading (`bufsize=1`) is partial solution but insufficient for true streaming

## Post-Implementation TODOs

1. Commit changes with clear message about streaming implementation
2. Notify via Slack (if MCP support available)
3. Update `AGENTS.md` if streaming becomes configurable
4. Consider adding `--no-streaming` flag if needed for debugging
5. Monitor for edge cases in production use
6. Consider performance metrics collection for streaming overhead
7. Evaluate need for `ptyprocess` library based on edge cases discovered
8. Document any platform-specific behavior discovered during testing
9. Consider backporting streaming to other executors if successful
