# Streaming JSON Output Investigation Report

## Executive Summary
- Total JSON files analyzed: 7
- Total NDJSON files analyzed: 11
- Valid standard JSON: 7
- Valid NDJSON: 11

## Key Findings

### Issue 1: NDJSON Format Not Being Parsed as Streaming Format
**Severity**: HIGH
- 0 NDJSON log files contain multiple JSON objects (one per line)
- Current parsers attempt to load these as single JSON objects, causing "Extra data" errors
- NDJSON format is correct for streaming; parser must be updated to handle it

### Issue 2: Inconsistent Structure
**Severity**: MEDIUM
- Standard JSON files have varying structures
- No unified schema across different executor types
- Need centralized streaming event format

### Recommendations
1. **Implement NDJSON Parser**: Update to read line-by-line and parse each as separate JSON object
2. **Define Unified Schema**: Create consistent event structure across all executors
3. **Standardize Event Types**: Define event types (activity_started, activity_completed, error, etc.)
4. **Add Provider Metadata**: Include provider name/version in each streamed event

## Test Results

### Prompt Used
what is the capital of australia?

### Executors Tested
- Planned: Claude, Cline, Aider, Gemini
- Current data: Analysis of existing output files (future cross-executor runs)

### Next Steps
1. Create streaming test harness that runs prompt across all executors
2. Capture and validate JSON output from each
3. Compare streaming format consistency
4. Generate cross-executor comparison report
