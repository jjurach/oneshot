# Change: Enhanced Claude Execution Arguments

**Related Project Plan:** 2026-01-19_09-52-57_enhanced_claude_execution_arguments.md

**Overview:** Added `--output-format stream-json` and `--verbose` arguments to claude command execution to provide more detailed output for activity monitoring and hung agent detection.

**Files Modified:**
- `src/oneshot/oneshot.py`: Updated claude command construction in both `call_executor` and `call_executor_adaptive` functions to include new arguments

**Impact Assessment:**
- Claude commands now include additional arguments for better output formatting and verbosity
- Both normal execution and adaptive timeout paths have been updated consistently
- The changes are backward compatible and only add functionality
- No impact on existing cline executor functionality