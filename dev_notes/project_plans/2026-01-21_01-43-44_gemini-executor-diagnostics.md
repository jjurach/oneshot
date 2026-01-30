# Project Plan: Gemini Executor Diagnostics & JSON Stream Formatting

**Status:** COMPLETED
**Source:** dev_notes/specs/2026-01-21_01-43-05_prompt-16.5.md

## Objective

Diagnose and fix the Gemini executor's JSON stream formatting to ensure it correctly parses and processes streaming output from the gemini-cli tool. Use actual Gemini internal test data to validate the streaming format and provide accurate resultSummary to the auditor.

## Implementation Steps

### Phase 1: Diagnostic Gathering
- [ ] Examine `tmp/test-cases/gemini2/notes.md` to understand Gemini internal file structure
- [ ] Review existing Gemini internal test case data to understand expected streaming format
- [ ] Compare current oneshot gemini_executor implementation against Gemini's native output format
- [ ] Identify discrepancies between expected and actual JSON stream formatting

### Phase 2: Test Execution & Data Collection
- [ ] Run `oneshot --executor gemini "what is the capital of india?" --debug --verbose`
- [ ] Capture streaming output and compare against reference data from `tmp/test-cases/gemini2/`
- [ ] Run `gemini --yolo --output-format stream-json "what is the capital of spain?"` to establish baseline
- [ ] Compare both outputs to identify formatting differences

### Phase 3: Root Cause Analysis
- [ ] Document specific JSON formatting issues in gemini_executor
- [ ] Analyze how streaming content is being parsed and transformed
- [ ] Identify gaps in resultSummary generation for auditor
- [ ] Review activity parsing logic for accuracy

### Phase 4: Debugging & Instrumentation
- [ ] Add additional debug logging to gemini_executor's stream parsing
- [ ] Instrument activity parsing to show intermediate steps
- [ ] Log raw streaming data before and after transformation
- [ ] Add verbose output for JSON format validation

### Phase 5: Fix Implementation
- [ ] Correct JSON stream formatting in gemini_executor based on diagnostics
- [ ] Update parse_activity() method to handle Gemini's streaming format accurately
- [ ] Ensure resultSummary is correctly extracted and formatted
- [ ] Validate format_output() produces correct audit log entries

### Phase 6: Validation & Testing
- [ ] Re-run diagnostic commands to verify fixes
- [ ] Run full executor test suite to ensure no regressions
- [ ] Validate that gemini executor output matches baseline format
- [ ] Verify auditor receives accurate resultSummary

## Success Criteria

- gemini_executor correctly parses streaming JSON from gemini-cli
- Output format matches Gemini's native `--output-format stream-json` format
- Accurate resultSummary provided to auditor
- Debug output clearly shows transformation steps
- All executor tests pass with no regressions
- Diagnostic commands complete successfully without errors

## Testing Strategy

1. **Unit Testing**: Run `pytest tests/test_executor_framework.py -v` to validate executor interface
2. **Diagnostic Testing**:
   - Execute both diagnostic commands with `--debug --verbose` flags
   - Compare outputs side-by-side
   - Verify JSON structure and content match
3. **Regression Testing**: Run full test suite to ensure other executors unaffected
4. **Manual Validation**: Review audit logs and resultSummary for accuracy

## Risk Assessment

- **Low Risk**: Changes isolated to gemini_executor module
- **Dependency Risk**: Requires gemini-cli tool to be installed and functional
- **Test Data Risk**: Reference test data in `tmp/test-cases/gemini2/` must be accurate
- **Mitigation**: Add comprehensive debug logging at each transformation step

## Files to Modify

- `src/oneshot/providers/gemini_executor.py` - Main implementation
- `tests/test_executor_framework.py` - Add Gemini-specific diagnostics test (if needed)

## Notes

- Reference test case: `tmp/test-cases/gemini2/notes.md` - Contains actual Gemini internal format
- Key commands for validation documented in prompt
- Focus on JSON stream formatting accuracy and complete activity parsing
