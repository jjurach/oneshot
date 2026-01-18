# Project Plan: Implement Lenient JSON Validation for Worker Responses

## Objective
Address "No valid JSON found in worker output" errors by implementing lenient JSON validation that accepts malformed JSON containing completion indicators ("success", "DONE", "status") to support cheaper worker models.

## Current Problem
- Workers are required to output strictly valid JSON
- Auditor rejects responses when JSON is malformed, even if completion intent is clear
- Expensive models produce valid JSON, but cheaper models may produce jumbled responses with clear completion signals

## Implementation Steps

### 1. Analyze Current JSON Validation Logic
- Review `extract_json()` function behavior with malformed JSON
- Document current strict validation requirements
- Identify common failure patterns (missing quotes, trailing commas, etc.)

### 2. Design Lenient JSON Parser
- Create `extract_lenient_json()` function that attempts multiple parsing strategies:
  - Standard JSON parsing first
  - Fix common JSON issues (missing quotes, trailing commas)
  - Extract key-value pairs from malformed JSON-like structures
  - Look for completion indicators in plain text
- Implement fallback parsing for responses with clear "DONE"/"success" sentiment

### 3. Update Auditor Prompt for Leniency
- Modify AUDITOR_PROMPT to accept non-JSON responses
- Add instructions to look for completion indicators in plain text
- Trust worker judgment even with malformed responses

### 4. Modify Worker Prompt (Optional)
- Update WORKER_PREFIX to encourage but not require valid JSON
- Add guidance for cheaper models on completion indicators

### 5. Update Validation Logic in run_oneshot
- Replace strict JSON requirement with lenient validation
- Only skip auditor if response shows clear failure/incompletion
- Log validation method used (strict JSON vs lenient parsing)

### 6. Update Tests
- Add tests for lenient JSON parsing scenarios
- Test malformed JSON with completion indicators
- Ensure backward compatibility with valid JSON responses

## Success Criteria
- Workers with jumbled JSON containing "DONE"/"success"/"status" are accepted
- Valid JSON responses continue to work as before
- Auditor provides helpful feedback for truly incomplete responses
- Performance impact is minimal
- Clear logging of validation method used

## Testing Strategy
- Unit tests for lenient JSON parsing with various malformed inputs
- Integration tests with simulated worker responses
- Manual testing with actual cheap models producing malformed JSON
- Regression tests to ensure valid JSON still works

## Risk Assessment
- **Medium**: May accept truly incomplete responses - mitigated by auditor evaluation
- **Low**: Performance impact from lenient parsing - minimal additional processing
- **Low**: Backward compatibility - existing valid JSON continues to work
- **Medium**: Complex parsing logic - requires thorough testing

## Implementation Notes
- Lenient parsing should be a fallback, not replace strict JSON validation
- Completion indicators should be configurable/context-aware
- Error messages should guide workers toward better formatting without being punitive