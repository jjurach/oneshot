# Project Plan: Optimize Cline Streaming and Activity Monitoring

## Objective
Enhance the oneshot tool's integration with the cline executor by:
1. Implementing `--output-format json` for structured output parsing
2. Modifying buffering characteristics to enable real-time streaming instead of buffered capture
3. Developing alternative activity monitoring by reading task files from `$HOME/.cline/data/tasks/$task_id` instead of process output
4. Creating a comprehensive testing framework to measure and optimize streaming performance

## Implementation Steps

### Phase 1: Research and Analysis (Completed)
- [x] Analyze cline's `--output-format json` functionality and message structure
- [x] Map out the `$HOME/.cline/data/tasks/$task_id` directory structure and file contents
- [x] Document how task progress is stored and updated during execution
- [x] Review current oneshot subprocess handling patterns

### Phase 2: Core Implementation
- [ ] Update `call_executor` function in `src/oneshot/oneshot.py` to accept output format parameter
- [ ] Add `--output-format json` flag to cline command construction
- [ ] Implement streaming subprocess execution with pipes instead of `capture_output=True`
- [ ] Create function to detect and read cline task directories
- [ ] Monitor task file modification times as activity indicator
- [ ] Develop streaming output parser for JSON messages
- [ ] Handle partial JSON messages during streaming
- [ ] Integrate with existing lenient JSON parsing logic
- [ ] Set `bufsize=0` for unbuffered I/O in subprocess calls
- [ ] Use `stdout=PIPE, stderr=PIPE` with real-time reading
- [ ] Implement non-blocking reads with timeouts

### Phase 3: Performance Optimization
- [ ] Modify timeout logic to work with streaming output
- [ ] Add graceful degradation when JSON output is malformed
- [ ] Optimize memory usage during streaming operations
- [ ] Implement connection pooling for file monitoring if needed

### Phase 4: Testing and Validation
- [ ] Develop experiments to compare streaming vs buffered execution
- [ ] Measure latency improvements and resource usage
- [ ] Test activity detection accuracy across different task types
- [ ] Create unit tests for JSON output parsing
- [ ] Validate file-based activity detection logic
- [ ] Add integration tests for complete oneshot workflow with cline streaming
- [ ] Verify activity monitoring during long-running tasks
- [ ] Compare buffered vs streaming performance metrics
- [ ] Ensure all existing tests pass with new streaming implementation

### Phase 5: Documentation and Deployment
- [ ] Update function documentation with new streaming parameters
- [ ] Add configuration options for enabling/disabling streaming features
- [ ] Create migration guide for users upgrading to streaming version
- [ ] Update README with new cline integration capabilities

## Detailed Checklist Items

### Streaming Implementation Checklist
- [ ] Modify `call_executor()` to accept `output_format` parameter (default: None)
- [ ] Add logic to append `--output-format json` when output_format="json"
- [ ] Replace `capture_output=True` with `stdout=subprocess.PIPE, stderr=subprocess.PIPE`
- [ ] Implement real-time line reading using `select()` or threading for non-blocking I/O
- [ ] Add JSON parsing for each line of output as it arrives
- [ ] Handle incomplete JSON lines by buffering until complete objects
- [ ] Set `text=True, bufsize=0` for unbuffered text mode
- [ ] Add timeout handling that works with streaming (terminate process after timeout)

### File-Based Activity Monitoring Checklist
- [ ] Create `get_cline_task_dir(task_id)` function to locate task directory
- [ ] Implement `monitor_task_files(task_dir, callback)` for file change detection
- [ ] Use `os.stat()` or `pathlib.Path.stat()` to check modification times
- [ ] Add polling mechanism with configurable interval (default: 5 seconds)
- [ ] Implement fallback to process monitoring if file monitoring fails
- [ ] Add error handling for permission issues accessing task directories
- [ ] Create abstraction layer to switch between file and process monitoring

### Performance Experiment Checklist
- [ ] **Experiment 1**: Buffer Size Impact
  - Test bufsize=0, 4096, 8192, and default
  - Measure output latency from process start to first output received
  - Compare memory usage across different buffer sizes
- [ ] **Experiment 2**: Activity Detection Accuracy
  - Run long-running tasks with both monitoring methods
  - Compare false positive/negative rates between file and process monitoring
  - Test with different task types (coding, file operations, API calls)
- [ ] **Experiment 3**: Resource Usage Comparison
  - Monitor CPU usage during streaming vs buffered execution
  - Measure memory consumption over time for long-running tasks
  - Test impact on system responsiveness during execution
- [ ] **Experiment 4**: JSON Parsing Performance
  - Benchmark JSON parsing speed for complete vs partial messages
  - Test memory usage with large JSON objects during streaming
  - Validate parsing accuracy with malformed or incomplete JSON

### Integration Testing Checklist
- [ ] Test with simple cline tasks to verify JSON output format works
- [ ] Verify streaming doesn't break existing non-JSON output handling
- [ ] Test timeout behavior with streaming (should terminate process cleanly)
- [ ] Validate error handling when cline doesn't support --output-format json
- [ ] Test file monitoring with actual cline tasks (requires cline installation)
- [ ] Verify fallback behavior when task directories are inaccessible

## Success Criteria
- Cline executor accepts and properly formats output as JSON
- Real-time streaming achieved with <100ms latency for output processing
- File-based activity monitoring detects task progress with >95% accuracy
- No regression in existing functionality for non-streaming executors
- Performance benchmarks show measurable improvements in responsiveness
- All existing tests pass with new streaming implementation

## Testing Strategy

### Unit Tests
- Test JSON output parsing with various message formats
- Validate file-based activity detection logic
- Mock streaming subprocess calls for controlled testing

### Integration Tests
- Test complete oneshot workflow with cline streaming
- Verify activity monitoring during long-running tasks
- Compare buffered vs streaming performance metrics

### Performance Experiments
- Experiment 1: Measure output latency with different buffer sizes (0, 4096, default)
- Experiment 2: Compare process output vs file monitoring accuracy
- Experiment 3: Test streaming impact on memory usage and CPU overhead
- Experiment 4: Benchmark JSON parsing performance with partial messages

### Regression Tests
- Ensure existing claude executor functionality unchanged
- Verify timeout behavior with streaming output
- Test error handling for malformed JSON streams

## Risk Assessment
- **High Risk**: JSON streaming could break existing parsing logic if cline output format changes
- **Medium Risk**: File-based monitoring may not work if cline changes task storage location/format
- **Low Risk**: Performance improvements are additive and can be disabled if issues arise
- **Mitigation**: Implement feature flags to enable/disable streaming, with fallback to current behavior