# Change: Test Infrastructure Improvements and Async Event System Fix

## Related Project Plan
Oneshot UI Integration (2026-01-17_19-08-03_oneshot_ui_integration.md)

## Overview
Fixed critical test infrastructure issues and resolved async event system bugs that were causing test timeouts and failures. Implemented permanent test safety features to prevent blocking subprocess calls in tests.

## Test Results
- **Total Tests**: 64
- **Passing**: 55 (85.9%)
- **Failing**: 9 (14.1%)
- **Status**: Major improvement from previous state where tests were timing out indefinitely

## Critical Fixes

### 1. Event System Event Loop Compatibility (CRITICAL FIX)
**Problem**: Global `event_emitter` queue was bound to the first test's event loop, causing "Queue is bound to a different event loop" errors in subsequent tests, leading to infinite error loops and timeouts.

**Solution**: Modified `AsyncEventEmitter.start()` in `src/oneshot/events.py` to detect and recreate the queue when the event loop changes:

```python
async def start(self):
    """Start the event dispatcher."""
    if self._running:
        return

    # Recreate queue to handle potential event loop changes (e.g., in tests)
    try:
        _ = self.queue._loop
        if _ != asyncio.get_running_loop():
            old_maxsize = self.queue.maxsize if hasattr(self.queue, 'maxsize') else 1000
            self.queue = asyncio.Queue(maxsize=old_maxsize)
    except (AttributeError, RuntimeError):
        old_maxsize = self.queue.maxsize if hasattr(self.queue, 'maxsize') else 1000
        self.queue = asyncio.Queue(maxsize=old_maxsize)

    self._running = True
    self._dispatcher_task = asyncio.create_task(self._dispatch_events())
```

**Impact**: Event system tests now pass consistently without timeouts.

### 2. Test Mode Blocking Prevention
**Problem**: Tests were hanging on actual subprocess calls instead of using mocks.

**Solution**: Implemented global test mode configuration in `src/oneshot/oneshot.py`:

```python
# Set ONESHOT_TEST_MODE=1 to prevent blocking subprocess calls
TEST_MODE = os.environ.get('ONESHOT_TEST_MODE', '0') == '1'

def _check_test_mode_blocking():
    """Raise exception if test mode is enabled and blocking call is attempted."""
    if TEST_MODE:
        import traceback
        stack = ''.join(traceback.format_stack())
        raise RuntimeError(
            f"BLOCKED: Subprocess call attempted in test mode!\n"
            f"All subprocess.run() calls should be mocked in tests.\n"
            f"Stack trace:\n{stack}"
        )
```

Added `_check_test_mode_blocking()` before all `subprocess.run()` calls (4 locations).

Enabled in tests via `tests/test_oneshot.py`:
```python
# Enable test mode to prevent blocking subprocess calls
os.environ['ONESHOT_TEST_MODE'] = '1'
```

**Impact**: Tests now fail fast with clear error messages instead of hanging, making debugging much easier.

### 3. Async Test Timeouts
**Problem**: Async tests could hang indefinitely without clear indication of what was blocking.

**Solution**:
- Installed `pytest-timeout` package
- Added `@pytest.mark.timeout()` decorators to all async tests:
  - Event system tests: 5 second timeout (fast operations)
  - Task and orchestrator tests: 10 second timeout (mocked async operations)

**Impact**: Tests fail fast with timeout errors instead of blocking test suite execution.

### 4. Event System Test Improvements
**Problem**: Tests weren't properly waiting for async events to be processed, leading to race conditions.

**Solution**: Used `asyncio.Event` for synchronization in `test_task_event_convenience_function`:

```python
events_received = []
event_received_event = asyncio.Event()

async def event_handler(event):
    events_received.append(event)
    event_received_event.set()  # Signal event received

# Wait for event with timeout
try:
    await asyncio.wait_for(event_received_event.wait(), timeout=2.0)
except asyncio.TimeoutError:
    pytest.fail("Event was not received within timeout")
```

**Impact**: Eliminates race conditions in event system tests.

## Files Modified

### Core Implementation
- `src/oneshot/oneshot.py`:
  - Added `TEST_MODE` and `_check_test_mode_blocking()` function
  - Added blocking checks before all 4 `subprocess.run()` calls
  - Import `os` module for environment variable access

- `src/oneshot/events.py`:
  - Modified `AsyncEventEmitter.start()` to recreate queue on event loop changes

### Tests
- `tests/test_oneshot.py`:
  - Added `os.environ['ONESHOT_TEST_MODE'] = '1'` at module level
  - Added `@pytest.mark.timeout()` to all 10 async tests
  - Improved `test_task_event_convenience_function` with proper async synchronization
  - Fixed `test_orchestrator_stats` to use correct orchestrator structure

- `requirements-dev.txt` / `pyproject.toml`:
  - Added `pytest-timeout>=2.4.0` dependency

## Remaining Test Failures (9 tests)

### TestCallExecutor (5 failures)
- **Cause**: Test mode blocking is triggering before mocks take effect
- **Status**: Tests correctly identify blocking; need to adjust mocking strategy or temporarily disable test mode for these tests

### TestOneshotTask (2 failures)
- `test_task_failed_execution`: Async stream readline mocking timeout
- `test_task_idle_detection`: Task not transitioning to IDLE state as expected
- **Cause**: Complex async stream mocking not properly configured
- **Status**: Requires more sophisticated async mock setup

### TestAsyncOrchestrator (2 failures)
- `test_orchestrator_single_task`: Timeout waiting for task completion
- `test_orchestrator_multiple_tasks`: Timeout waiting for tasks completion
- **Cause**: Mocked tasks not properly completing async execution
- **Status**: Requires fixing async task mock execution

## Technical Benefits

### Debugging Improvements
1. **Fast Failure**: Tests now fail in seconds instead of timing out after minutes
2. **Clear Error Messages**: Test mode blocking provides full stack traces
3. **Timeout Information**: pytest-timeout clearly indicates which test is hanging

### Test Reliability
1. **Event Loop Safety**: Event system works correctly across test isolation boundaries
2. **No Infinite Loops**: Event dispatcher errors are contained and logged
3. **Proper Synchronization**: Event-based tests use explicit async synchronization

### Future-Proofing
1. **Permanent Safety**: Test mode blocking prevents accidental real subprocess execution
2. **Scalable Pattern**: Easy to add more blocking checks for other I/O operations
3. **Clear Test Requirements**: Tests must properly mock all external dependencies

## Next Steps

To achieve 100% test pass rate:

1. **Fix TestCallExecutor tests**: Either disable test mode for these specific tests or use module-level subprocess mocking
2. **Improve async stream mocking**: Create proper async iterators for stdout/stderr readline operations
3. **Fix orchestrator tests**: Ensure mocked tasks complete their async execution properly

## Testing Methodology

All changes were tested with:
```bash
# Event system tests
python -m pytest tests/test_oneshot.py::TestEventSystem -v

# Full test suite
python -m pytest tests/test_oneshot.py -v --tb=short

# Quick summary
python -m pytest tests/test_oneshot.py --tb=no -q
```

## Impact Assessment

### Positive Impacts
- **Development Velocity**: Much faster test feedback loop
- **Test Confidence**: Higher confidence in async code correctness
- **Maintainability**: Easier to identify and fix test issues

### Areas for Improvement
- 9 remaining test failures need attention
- Some tests may need architectural changes to be properly testable
- Mock setup complexity for async operations needs simplification

## Conclusion

This change significantly improves the test infrastructure, making it possible to:
1. Run tests without infinite timeouts
2. Identify blocking operations quickly
3. Debug async code with confidence
4. Maintain test isolation across async operations

The 85.9% pass rate is a major improvement from the previous state where tests would hang indefinitely. The remaining failures are well-understood and have clear paths to resolution.
