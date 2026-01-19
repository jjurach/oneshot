# Change: Reworker Prompt Feature Implementation

## Related Project Plan

dev_notes/project_plans/2026-01-19_reworker_prompt_feature.md

## Overview

Successfully implemented the three-stage prompt system for the oneshot execution framework. This introduces a `get_reworker_prompt()` function and modifies the worker loop to use reworker prompts on subsequent iterations after auditor feedback, enabling iterative refinement of AI worker outputs.

## Files Modified

### src/oneshot/oneshot.py (Primary changes)

1. **Added `get_reworker_prompt()` function** (lines ~645-675):
   - Creates reworker prompt with customizable header (default: "oneshot reworker")
   - Includes guidance to focus only on original prompt and auditor feedback
   - Warns against wandering in random directions
   - Includes instruction to re-run tests and output expected JSON format

2. **Added `REWORKER_PROMPT` constant** (line ~678):
   - Backward compatibility constant following existing pattern

3. **Modified worker prompt construction logic** (lines ~1200-1220):
   - Added `last_auditor_feedback` tracking variable
   - Implemented iteration-aware prompt selection:
     - First iteration: uses `get_worker_prompt()`
     - Subsequent iterations: uses `get_reworker_prompt()` + original prompt + auditor feedback

4. **Updated REITERATE handling** (lines ~1440-1450):
   - Stores auditor feedback in `last_auditor_feedback` when REITERATE verdict received
   - Ensures feedback is available for reworker prompts in next iteration

5. **Added `truncate_worker_output_for_auditor()` function** (lines ~850-890):
   - Truncates worker output for auditor prompts to final 2KB or complete JSON if present
   - Handles UTF-8 character boundaries properly
   - Returns complete JSON objects if they contain completion indicators

6. **Updated auditor prompt construction** (lines ~1360-1375):
   - Uses `truncate_worker_output_for_auditor()` to limit auditor input
   - Maintains proper prompt structure: header + prompt content + original task + truncated worker output

7. **Updated function signatures**:
   - `run_oneshot()`: Added `reworker_prompt_header` parameter
   - `run_oneshot_legacy()`: Added `reworker_prompt_header` parameter

8. **Updated CLI argument parser** (lines ~1580-1590):
   - Added `--reworker-prompt-header` argument with default "oneshot reworker"
   - Updated main function to pass reworker_prompt_header to legacy wrapper

### Test Results

- **242 tests passed**, 2 skipped, 3 failed
- Failed tests are pre-existing issues unrelated to reworker prompt implementation:
  - PTY streaming multiline output issues (2 tests)
  - Mock import issue in one test
- All reworker prompt functionality tests pass

## Impact Assessment

### Positive Impact
- ✅ **Enhanced iterative refinement**: Workers now receive focused reworker prompts on subsequent iterations
- ✅ **Improved feedback loop**: Auditor feedback is properly injected into reworker prompts
- ✅ **Output truncation**: Auditor prompts are limited to relevant content (2KB or complete JSON)
- ✅ **Backward compatibility**: All existing APIs maintain compatibility
- ✅ **Custom headers**: Support for custom prompt headers via CLI and API
- ✅ **Focused guidance**: Reworker prompts emphasize staying on-task and re-running tests

### Neutral Impact
- No breaking changes to existing functionality
- Minimal performance impact (additional string operations)
- Memory usage slightly increased due to auditor feedback storage

### Risk Assessment
- **Low risk**: Implementation follows existing patterns and conventions
- **Tested thoroughly**: 242/247 tests pass, failures are unrelated
- **Backward compatible**: All existing function signatures preserved

## Technical Details

### Prompt Structure
- **Worker (Initial)**: `[header] + [worker_prompt] + [original_task]`
- **Auditor**: `[header] + [auditor_prompt] + [original_task] + [truncated_worker_output]`
- **Reworker (Subsequent)**: `[header] + [reworker_prompt] + [original_task] + [auditor_feedback]`

### Key Features
1. **Iteration tracking**: Automatically detects first vs subsequent iterations
2. **Feedback storage**: Persists auditor feedback between iterations
3. **Smart truncation**: Preserves complete JSON responses in auditor prompts
4. **UTF-8 safe**: Proper character boundary handling in truncation
5. **CLI integration**: Full command-line support for custom headers

### Success Criteria Met
- ✅ `get_reworker_prompt()` function exists and returns properly formatted prompt
- ✅ Worker receives `get_worker_prompt()` on initial iteration, `get_reworker_prompt()` on subsequent iterations
- ✅ Auditor feedback is correctly injected into reworker prompts
- ✅ Auditor receives properly formatted prompts with truncated worker output
- ✅ All three prompt types have clearly demarcated sections with customizable headers
- ✅ Backward compatibility maintained
- ✅ CLI arguments added for header customization

## Notes

The implementation successfully addresses all requirements from prompt-09.md and the detailed project plan. The reworker prompt system enables more effective iterative refinement by ensuring workers focus on specific feedback while avoiding tangential exploration. The output truncation prevents auditor prompt bloat while preserving critical completion information.