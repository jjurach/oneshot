# Project Plan: Enhanced Debugging for Data Flow Tracing

## Objective
Add comprehensive debugging output to trace data flow through the oneshot worker-auditor loop, providing visibility into:
1. Raw input to worker agent
2. Raw output from worker agent
3. Raw input to auditor agent
4. Raw output from auditor agent
5. JSON chunk reading and buffering from PTY process
6. Confirmation that auditor receives correct data

## Context
Current `--debug --verbose` flags show minimal information about data flow. Users cannot easily see what inputs/outputs are being sent to providers or how JSON chunks are being buffered from subprocess streams. This makes debugging extraction issues difficult.

## Implementation Steps

### Step 1: Add Enhanced Debugging to PTY JSON Chunk Reading
**File**: `src/oneshot/oneshot.py`, function `call_executor_pty()` (lines 85-278)

Add debug output at:
- **Line ~100**: When buffer accumulation starts
  - Show accumulation buffer size threshold
  - Show JSON detection logic being used

- **Lines ~194-196** (after `os.read()` call):
  - Show raw bytes read (first 200 chars, truncated)
  - Show accumulated buffer size before/after

- **Lines ~206-235** (inside flushing logic):
  - Show why flush was triggered (size limit, line boundary, JSON boundary)
  - Show how many JSON objects detected
  - Show what was flushed (first 300 chars, truncated)

- **Lines ~239-242** (after flush):
  - Show total stdout accumulated so far
  - Show buffer reset

**Expected Output Format**:
```
[PTY CHUNK] Read 1024 bytes
[PTY CHUNK] Accumulated: 5432 bytes (threshold: 4096)
[PTY JSON] Detected complete JSON object, flushing
[PTY FLUSH] Size trigger: 5432 >= 4096 bytes
[PTY FLUSH] Content preview (first 300 chars): {...
[PTY STDOUT] Total accumulated: 12456 bytes
```

### Step 2: Add Worker Input/Output Debugging
**File**: `src/oneshot/oneshot.py`, function `run_oneshot()` (lines 1320-1494)

Add debug output around worker execution (lines 1321-1345):

- **Before worker call** (~line 1334):
  - Show full prompt being sent (truncate to 500 chars with "...")
  - Show prompt length and structure
  - Label which prompt type: "worker_prompt" or "reworker_prompt"

- **After worker call** (~line 1343):
  - Show raw worker output (first 800 chars)
  - Show worker activities list length and types
  - Show total bytes received

**Expected Output Format**:
```
[WORKER INPUT] Iteration 1: Using worker_prompt
[WORKER INPUT] Prompt length: 342 chars
[WORKER INPUT] Preview: "I will help you answer this question. Please structure your response..."
[WORKER OUTPUT] Raw output received: 1234 bytes
[WORKER OUTPUT] Preview (first 800 chars): "I need to find information about Denmark's capital..."
[WORKER ACTIVITIES] Extracted 3 activities: [TOOL_CALL, REASONING, FILE_OPERATION]
```

### Step 3: Add JSON Extraction Debugging
**File**: `src/oneshot/oneshot.py`, function `run_oneshot()` (lines 1378-1391)

Add debug output around JSON extraction:

- **After extraction** (~line 1383):
  - Show extraction method used (strict, fixed, lenient_fallback, etc)
  - Show extracted JSON (first 500 chars)
  - Show whether extraction succeeded
  - Show completion indicators found (if any)

**Expected Output Format**:
```
[JSON EXTRACT] Method: strict
[JSON EXTRACT] Success: true
[JSON EXTRACT] Completion indicators: ["done"]
[JSON EXTRACT] JSON preview (first 500 chars): {"response": "Copenhagen is the capital of Denmark..."
[JSON EXTRACT] Skipping auditor: no acceptable response extracted
```

### Step 4: Add Auditor Input Debugging
**File**: `src/oneshot/oneshot.py`, function `run_oneshot()` (lines 1393-1410)

Add debug output before auditor execution:

- **Before auditor call** (~line 1409):
  - Show activities being sent to auditor
  - Show full audit prompt being sent (truncate to 500 chars)
  - Show what feedback (if any) is being included
  - Show auditor model name

**Expected Output Format**:
```
[AUDITOR INPUT] Iteration 1: Using auditor_prompt
[AUDITOR INPUT] Auditor model: executor (claude)
[AUDITOR INPUT] Activities to evaluate: 3 activities, 1.2 KB
[AUDITOR INPUT] Activity types: [TOOL_CALL, REASONING, FILE_OPERATION]
[AUDITOR INPUT] Prompt length: 856 chars
[AUDITOR INPUT] Preview: "Evaluate whether this response completes the task. Look at the activities..."
[AUDITOR INPUT] Feedback from previous iteration: (none)
```

### Step 5: Add Auditor Output and Verdict Debugging
**File**: `src/oneshot/oneshot.py`, function `run_oneshot()` (lines 1410-1447)

Add debug output after auditor execution and verdict parsing:

- **After auditor call** (~line 1410):
  - Show raw auditor output (first 800 chars)

- **After verdict parsing** (~line 1432):
  - Show parsed verdict (DONE, REITERATE, or None)
  - Show reason and advice (if any)
  - Show which parsing method worked (strict JSON, pattern matching, fallback)

**Expected Output Format**:
```
[AUDITOR OUTPUT] Raw output received: 2145 bytes
[AUDITOR OUTPUT] Preview (first 800 chars): "Looking at this response, I can see the AI tool was called to search for...
[VERDICT] Parsed with method: strict_json
[VERDICT] Result: DONE
[VERDICT] Reason: "The response correctly identifies Copenhagen as Denmark's capital"
[VERDICT] Advice: (none)
```

### Step 6: Add Activity Filtering Debugging
**File**: `src/oneshot/oneshot.py`, function `run_oneshot()` (lines 1396-1398)

Add debug output in activity selection:

- **Before filtering** (~line 1396):
  - Show all activities before filtering (count and types)

- **After filtering** (~line 1398):
  - Show activities after filtering
  - Show which were removed and why
  - Show final size in bytes

**Expected Output Format**:
```
[AUDITOR ACTIVITIES] Before filtering: 8 activities total
[AUDITOR ACTIVITIES] Activity types: [PLANNING, TOOL_CALL, REASONING, THINKING, STATUS, FILE_OPERATION, ...]
[AUDITOR ACTIVITIES] Removing: [PLANNING (1), THINKING (2), STATUS (1)] = 4 activities removed
[AUDITOR ACTIVITIES] After filtering: 4 activities, 2.3 KB
[AUDITOR ACTIVITIES] Final types: [TOOL_CALL, REASONING, FILE_OPERATION]
```

### Step 7: Add Data Flow Confirmation
**File**: `src/oneshot/oneshot.py`, within `run_oneshot()` (new section ~line 1450)

After iteration completes:

- Show iteration result summary
- Confirm data flowing through correctly
- Show decision made (continue, retry, or done)

**Expected Output Format**:
```
[ITERATION 1] Complete
[ITERATION 1] Worker: 1234 bytes input → 5678 bytes output
[ITERATION 1] Extraction: method=strict, success=true
[ITERATION 1] Auditor: 856 bytes input → 2145 bytes output
[ITERATION 1] Verdict: DONE
[ITERATION 1] Decision: Returning success=true
```

## Success Criteria
- [ ] All debug statements only output when `--debug` flag is provided
- [ ] Debug messages use `log_debug()` function
- [ ] Each debug line is prefixed with clear category tags like `[WORKER INPUT]`, `[PTY CHUNK]`, etc.
- [ ] Raw data is truncated at 300-800 chars with ellipsis to avoid overwhelming output
- [ ] Running `oneshot --debug --verbose "test"` shows comprehensive data flow trace
- [ ] Can verify auditor is receiving correct data
- [ ] Can verify JSON chunk buffering is working correctly
- [ ] Debug output helps identify where data loss or corruption occurs

## Testing Strategy
1. Run with `--debug --verbose` flag and verify output shows all new debug messages
2. Test with simple query like "what is 2+2?" to see complete data flow
3. Test with query that requires multiple iterations to see feedback flowing through
4. Verify debug output matches actual data being processed
5. Confirm no sensitive data is leaked in debug output

## Risk Assessment
**Low Risk**:
- Only adds debug logging; no functional changes
- Guarded by existing `log_debug()` checks
- No performance impact when not using `--debug`
- No impact on normal operation

## Files to Modify
1. `src/oneshot/oneshot.py` - Main changes (7 sections)
2. Possibly `src/oneshot/providers/__init__.py` - If provider debug info needed
3. Possibly `src/oneshot/providers/activity_logger.py` - If activity logging debug needed
