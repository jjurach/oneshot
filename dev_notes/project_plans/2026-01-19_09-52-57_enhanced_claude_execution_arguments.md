# Project Plan: Enhanced Claude Execution Arguments

**Objective:** Add `--output-format stream-json` and `--verbose` arguments to claude command execution to provide more detailed output for activity monitoring and hung agent detection.

**Implementation Steps:**

1. **Update claude command construction in `call_executor` function** - Add the new arguments to the command array
2. **Update claude command construction in `call_executor_adaptive` function** - Ensure consistency in both timeout handling paths
3. **Test the changes** - Verify the commands execute properly with the new arguments

**Success Criteria:**
- Claude commands include `--output-format stream-json` and `--verbose` arguments
- Both normal execution and adaptive timeout paths are updated
- Commands execute successfully with the new arguments

**Testing Strategy:**
- Manual testing with a simple prompt to verify the arguments are passed correctly
- Verify output format provides streaming JSON information for activity monitoring

**Risk Assessment:**
- Low risk - only adding arguments to existing command construction
- The arguments should be backward compatible if the claude tool supports them
- If arguments aren't supported, the claude tool will likely report an error

This is a straightforward change that modifies two locations in the codebase where claude commands are constructed.