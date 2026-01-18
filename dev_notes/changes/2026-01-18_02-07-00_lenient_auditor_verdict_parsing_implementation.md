# Change: Implement Lenient Auditor Verdict Parsing to Fix Cline Communication Issues

## Related Project Plan
None - Direct implementation to address user-reported issue

## Overview
Implemented lenient verdict parsing for auditor responses to resolve consistent failures with Cline provider. The auditor was previously required to return valid JSON, but Cline often returns plain text or malformed responses containing completion indicators. This change makes the auditor parsing as flexible as worker parsing, accepting various response formats.

## Files Modified

### src/oneshot/oneshot.py
- **Added `parse_lenient_verdict()` function**: Implements multi-strategy verdict extraction with fallbacks, similar to worker JSON parsing
  - First tries strict JSON parsing for backward compatibility
  - Falls back to pattern matching for `"verdict": "DONE"` patterns (quoted and unquoted keys)
  - Supports user's specific request: `"status": "DONE"` patterns on same line
  - Accepts plain completion indicators as final fallback
  - Normalizes verdict values to uppercase
- **Updated AUDITOR_PROMPT**: Removed strict JSON requirement, added alternative format guidance encouraging completion indicators
- **Modified verdict parsing logic**: Replaced `parse_json_verdict()` calls with `parse_lenient_verdict()` in both `run_oneshot()` and `run_oneshot_async()`
- **Updated `parse_json_verdict()` function**: Now serves as backward compatibility wrapper calling `parse_lenient_verdict()`

### tests/test_json_parsing.py
- **Added `TestParseLenientVerdict` class**: Comprehensive test suite for lenient verdict parsing
  - Tests valid JSON responses (backward compatibility)
  - Tests `"verdict": "DONE"` pattern extraction
  - Tests user's specific `"status": "DONE"` same-line pattern
  - Tests multiline status patterns
  - Tests plain completion word detection
  - Tests REITERATE verdicts
  - Tests case insensitive parsing
  - Tests malformed JSON with unquoted keys
  - Tests responses with no clear verdict

## Impact Assessment
- **Positive**: Fixes consistent Cline provider failures where auditor responses couldn't be parsed
- **Positive**: Maintains full backward compatibility with valid JSON responses
- **Positive**: Makes auditor parsing as flexible as worker parsing
- **Positive**: Addresses user's specific request for `"status": "DONE"` pattern recognition
- **Neutral**: Slight performance overhead from multiple parsing attempts (minimal impact)
- **Low Risk**: Fallback parsing only activates when strict JSON fails, preserving existing behavior

## Testing Strategy
- Unit tests for all lenient verdict parsing patterns
- Comprehensive test coverage for edge cases
- Regression tests ensuring valid JSON still works perfectly
- Integration testing with Cline executor (manual verification needed)

## Next Steps
- Test with actual Cline executor to verify the fix resolves the user's issue
- Monitor for any edge cases in production use
- Consider adding more completion indicators if needed