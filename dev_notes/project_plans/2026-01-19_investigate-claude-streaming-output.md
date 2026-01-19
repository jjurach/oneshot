# Project Plan: Enable Real-Time Streaming Output from Claude CLI

## Objective
Investigate and implement real-time streaming output from the Claude CLI subprocess when invoked with `--output-format stream-json`. Currently, the oneshot system captures output only after the entire process completes (using `capture_output=True`), preventing users from seeing iterative progress reports until completion.

## Problem Statement
The current `call_executor()` function in `src/oneshot/oneshot.py:331-449` uses `subprocess.run()` with `capture_output=True`, which buffers all output until the subprocess finishes. This prevents real-time visibility of Claude's progress when using the `--output-format stream-json` flag.

## Root Cause Analysis (from Research)

### Buffering Behavior in POSIX Pipes
1. **POSIX Pipes are Fully Buffered**: When stdout/stderr is redirected through a pipe (as with `capture_output=True`), the subprocess buffers output in blocks of arbitrary size
2. **Terminal Streams are Line-Buffered**: When output goes to a TTY, it's typically line-buffered
3. **Detection with `isatty()`**: Many CLI tools (including Claude) check if stdout is a terminal using `isatty()` and adjust buffering accordingly

### Three Potential Solutions

#### Solution A: Line-Buffering Configuration
- Set `bufsize=1` + `universal_newlines=True` in `subprocess.Popen()`
- **Limitation**: Only works for line-terminated output; doesn't work reliably for JSON streaming
- **Limitation**: Line buffering is often disabled for non-terminal streams anyway
- **Limitation**: Requires manual line-by-line reading instead of `capture_output`

#### Solution B: Environment Variable Approach
- Set `PYTHONUNBUFFERED=1` in subprocess environment
- Use `-u` flag (unbuffered mode)
- **Limitation**: Only affects Python subprocesses, not the Claude CLI itself
- **Limitation**: Claude CLI may still buffer unless it detects a TTY

#### Solution C: Pseudo-Terminal (PTY) Allocation
- Allocate a PTY using Python's `pty` module or third-party `ptyprocess` library
- Forces the subprocess to believe it's running in an interactive terminal
- The subprocess will use line-buffering (or no buffering) when it detects a TTY
- **Advantage**: Works with any CLI tool, not just Python
- **Advantage**: Preserves program behavior for interactive elements
- **Trade-off**: More complex to implement; requires proper signal handling; PTY handling varies across platforms

## Recommended Approach: Hybrid Solution

### Phase 1: Quick Win - Line-Buffered Reading (Easy, Partial Solution)
Implement line-buffered reading as a first step:
- Use `subprocess.Popen()` with `bufsize=1`, `universal_newlines=True`
- Read from stdout line-by-line using `iter(process.stdout.readline, '')`
- Print/log each line as it arrives
- **Result**: Achieves real-time output for line-terminated JSON but not true streaming

### Phase 2: Proper Solution - PTY Allocation (Complete Solution)
Implement PTY allocation for true streaming:
- Use `pty.openpty()` (built-in, no dependencies) or `ptyprocess` (more robust)
- Spawn Claude CLI subprocess connected to slave PTY
- Read from master PTY file descriptor as data arrives
- Implement proper error handling and cleanup (PTY-specific exception handling)
- Handle platform differences (Windows lacks PTY support)

## Implementation Steps

### Step 1: Research & Validation
- [ ] Verify Claude CLI respects `isatty()` and streams output when stdout is a TTY
- [ ] Test current behavior: run `claude` with `capture_output=True` vs PTY allocation
- [ ] Verify JSON streaming works end-to-end with PTY allocation
- [ ] Check compatibility with streaming JSON format

### Step 2: Add PTY-Based Executor Function
- [ ] Create `call_executor_pty()` function in `oneshot.py`
- [ ] Implement master/slave PTY setup
- [ ] Add line-by-line or fixed-buffer reading from master
- [ ] Handle subprocess exit code and completion
- [ ] Proper exception handling for PTY errors (OSError, IOError)
- [ ] Add platform detection (warn or skip on Windows)

### Step 3: Integrate with Existing Code
- [ ] Modify `call_executor()` to use PTY approach instead of `capture_output=True`
- [ ] Update logging to show streaming output in real-time
- [ ] Ensure all captured output is still available for JSON extraction
- [ ] Handle both sync and async versions (or keep async as fallback)

### Step 4: Output Buffering Strategy
- [ ] Decide on read buffer size (1024 bytes as suggested in prompt, or line-based)
- [ ] Implement real-time output display/logging
- [ ] Buffer complete JSON objects for parsing
- [ ] Handle partial JSON lines gracefully

### Step 5: Testing
- [ ] Unit tests for PTY functionality
- [ ] Integration tests with actual Claude CLI
- [ ] Verify stream-json output is captured correctly
- [ ] Test timeout behavior with streaming output
- [ ] Verify no deadlock with large outputs
- [ ] Test error scenarios (process crashes, PTY allocation failure)

### Step 6: Documentation & Cleanup
- [ ] Document the streaming implementation
- [ ] Add comments explaining PTY setup and limitations
- [ ] Update CLAUDE.md or docs with new behavior
- [ ] Remove or archive old `call_executor_adaptive()` if no longer needed

## Critical Considerations

### Deadlock Prevention
- PTY approach avoids the pipe deadlock issue because PTYs use a different buffering strategy
- No need for threading/select() monitoring when using PTY
- Must still handle subprocess.TimeoutExpired exceptions

### Cross-Platform Compatibility
- PTY is Unix/Linux only (not available on Windows)
- Need fallback or skip for Windows environments
- Add platform detection to warn users on Windows

### Signal Handling
- PTY processes may need special signal handling (SIGHUP when master closes)
- Must properly close master PTY descriptor to avoid zombie processes
- Use try/finally to ensure cleanup

### Output Capture for JSON Extraction
- While streaming output to terminal/logs, must also capture for JSON extraction
- Need to collect complete output while displaying it line-by-line
- Balance between memory (for large outputs) and user experience

## Success Criteria

1. **Real-time Progress**: User sees iterative Claude progress reports while subprocess runs (not waiting until completion)
2. **JSON Extraction Works**: Can still extract complete JSON objects from captured output for auditor processing
3. **No Breaking Changes**: Existing functionality preserved; streaming is transparent enhancement
4. **Timeout Still Works**: Activity monitoring and timeouts function correctly with streaming
5. **Clean Implementation**: Code follows existing patterns; well-integrated with current architecture
6. **Documentation**: Implementation is documented for future maintainers

## Testing Strategy

### Unit Tests
- Mock PTY behavior for testability
- Test output parsing with various JSON formats
- Test timeout handling during streaming

### Integration Tests
- Real Claude CLI invocation with simple prompt
- Verify stream-json output is streamed (not buffered)
- Verify output is captured correctly
- Test with `--verbose` flag to see debug logs

### Manual Testing
- Run oneshot with long-running Claude task
- Observe real-time progress output on terminal
- Verify session logs contain complete output
- Monitor for any performance regression

## Risk Assessment

### Low Risk
- Line-buffered approach (Phase 1) as fallback
- Existing `capture_output=True` approach still works
- No changes to API or external interfaces

### Medium Risk
- PTY-specific behavior differences across Unix variants
- Potential signal handling issues
- Memory usage with very large streaming outputs

### Mitigation Strategies
- Start with Phase 1 (line-buffered reading) as proven intermediate solution
- Add comprehensive error handling for PTY failures
- Add fallback to non-streaming approach if PTY fails
- Test on multiple platforms (Linux, macOS) before release
- Add environment variable for disabling streaming (e.g., `ONESHOT_DISABLE_STREAMING=1`)

## Dependencies & Resources

### Python Standard Library (No New Dependencies)
- `pty` module: Built-in for PTY allocation
- `os` module: Already imported; used for file descriptor operations
- `select` module: Optional for cross-platform async reading (if needed)

### Optional Enhancement
- `ptyprocess` package: More robust, handles edge cases
- Installation: `pip install ptyprocess`
- Benefit: Works on more platforms; better Windows fallback behavior

## Files to Modify

1. **`src/oneshot/oneshot.py`**
   - Add `call_executor_pty()` function
   - Modify `call_executor()` to use PTY approach
   - Update `call_executor_adaptive()` if needed
   - Update `call_executor_async()` for async version

2. **`src/oneshot/providers/__init__.py`** (Optional)
   - Update ExecutorProvider if needed to support streaming config

3. **Documentation** (Optional)
   - `docs/direct-executor.md`: Update streaming behavior docs
   - `CLAUDE.md`: Mention streaming output improvement

## Related Files (Read-Only)
- `docs/overview.md`: Understand project architecture
- `src/oneshot/task.py`: Understand OneshotTask for async handling
- `tests/test_oneshot.py`: Understand test patterns

## Success Indicators

After implementation, verify:
1. Running `oneshot 'long task'` shows progress in real-time
2. Session logs contain complete JSON output
3. Auditor receives all expected data from worker
4. No performance regression vs current implementation
5. Tests pass: `pytest tests/test_oneshot.py -v`
6. No new warnings or errors in debug logs

## Notes & Observations

### From Research
- Python's `capture_output=True` is equivalent to `stdout=PIPE, stderr=PIPE`
- POSIX pipes default to full buffering (not line buffering) in subprocess context
- The suggested PTY approach in `prompt-04.md` is the correct solution for this problem
- `pty.openpty()` returns (master, slave) file descriptors (not file objects)
- Master must be read before slave can be used by subprocess

### Current Implementation Notes
- `call_executor()` at line 331 currently uses `subprocess.run()` with `capture_output=True`
- Claude CLI invoked with `['claude', '-p', '--output-format', 'stream-json', '--verbose']`
- Prompt passed via `input=prompt` parameter
- Output buffered until process completes; all available at once
- Model optionally specified with `--model` flag
- `call_executor_adaptive()` exists but also uses pipes
- Async version in `call_executor_async()` delegates to sync version for claude executor

## Post-Implementation TODOs

1. Commit changes with clear message about streaming implementation
2. Update AGENTS.md if streaming becomes configurable
3. Consider adding `--no-streaming` flag if needed
4. Monitor for edge cases in production use
5. Consider performance metrics for streaming overhead
