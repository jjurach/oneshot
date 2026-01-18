# Change: Implement Lenient JSON Validation for Worker Responses

## Related Project Plan
dev_notes/project_plans/2026-01-17_18-48-01_lenient_json_validation.md

## Overview
Implemented lenient JSON validation to accept malformed JSON containing completion indicators ("success", "DONE", "status") to support cheaper worker models that may not produce perfectly formatted JSON.

## Files Modified

### src/oneshot/oneshot.py
- **Added `extract_lenient_json()` function**: Implements multi-strategy JSON parsing with fallbacks
- **Added `contains_completion_indicators()` function**: Checks for completion signals in text
- **Updated AUDITOR_PROMPT**: Modified to accept non-JSON responses and evaluate completion indicators
- **Updated WORKER_PREFIX**: Changed from strict JSON requirement to encouragement with alternatives
- **Modified `run_oneshot()`**: Replaced strict JSON validation with lenient validation
- **Added logging**: Tracks which validation method was used for each response

### tests/test_oneshot.py
- **Added tests for lenient JSON parsing**: Various malformed JSON scenarios with completion indicators
- **Updated existing tests**: Ensured backward compatibility with valid JSON
- **Added completion indicator detection tests**: Plain text responses with completion signals

## Impact Assessment
- **Positive**: Cheaper worker models can now succeed with jumbled JSON containing completion signals
- **Positive**: Maintains backward compatibility with valid JSON responses
- **Neutral**: Slight performance overhead from lenient parsing attempts
- **Positive**: Better error messages guide workers toward better formatting
- **Low Risk**: Auditor evaluation provides safety net against accepting truly incomplete responses

## Testing Strategy
- Unit tests for various malformed JSON patterns
- Integration tests with simulated worker responses
- Regression tests ensuring valid JSON still works perfectly
- Manual testing with responses containing completion indicators

## Next Steps
- Monitor real-world usage with cheaper models
- Consider additional completion indicators if needed
- Evaluate auditor feedback quality with lenient responses