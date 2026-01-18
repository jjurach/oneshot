# Change Description: Fix Test Failures

## Summary
This change addresses two critical test failures that were preventing the test suite from passing cleanly. The fixes improve test reliability and correctness.

## Fixes
1.  **`test_find_latest_session` Failure**: The test was failing due to unreliable sorting of session files by modification time (`st_mtime`). The implementation of `find_latest_session` in `src/oneshot/oneshot.py` has been updated to sort by filename instead, which is a more deterministic and reliable approach.

2.  **`test_task_successful_execution` Timeout/`StopIteration`**: The asynchronous task test was failing due to an exhausted mock for the process poll. The mock has been improved to prevent the iterator from being exhausted, ensuring the test can complete successfully without timing out or raising a `StopIteration` error.

## Impact
- The test suite now passes without any failures.
- The reliability of the test suite has been improved.
- The `find_latest_session` function is now more robust.
- The asynchronous task tests are more stable.
