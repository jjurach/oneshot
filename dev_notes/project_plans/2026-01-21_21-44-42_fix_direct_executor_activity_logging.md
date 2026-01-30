# Project Plan: Fix Direct Executor Activity Logging

**Source:** dev_notes/specs/2026-01-30_00-30-06_prompt-18.md

## Objective

Implement streaming activity event generation for the Direct executor to properly display activity in the CLI and log structured JSON events to the `$id-oneshot-log.json` file. The Direct executor currently shows "Activity (unknown)" because it doesn't generate the JSON activity events that the pipeline expects. This plan implements a solution where the Direct executor creates JavaScript objects on LLM ingress and egress to emulate the JSON activity stream produced by subprocess-based executors like Cline.

## Root Cause Analysis

### Current Behavior
When running:
```bash
$ oneshot --executor direct "what is the capital of iraq?"
📋 Activity (unknown):
📋 Activity (unknown):
```

The Direct executor:
1. **Does not emit streaming JSON activity objects** like Cline/Claude executors
2. Uses a simple `yield ollama_response.response` that just returns raw text (line 104 of `direct_executor.py`)
3. The pipeline's `extract_json_objects()` expects JSON objects with structure like `{"type": "...", "text": "..."}` but receives plain strings
4. The UI callback in `oneshot.py` (_print_pipeline_event, line 124) cannot interpret the activity type

### How Other Executors Work

**Cline Executor** (subprocess-based):
- Spawns `cline` subprocess with `--output-format json`
- Subprocess naturally streams JSON objects to stdout: `{"say":"text","text":"..."}`, `{"say":"tool_use",...}`, etc.
- Pipeline's `extract_json_objects()` parses these
- `timestamp_activity()` wraps them with timestamp
- Logs to NDJSON file with executor attribution
- UI interprets activity types for display

**Direct Executor** (HTTP API-based):
- Makes synchronous HTTP call to Ollama/OpenAI endpoint
- Receives complete response in one shot
- Currently just yields the raw response text
- **No JSON activity objects generated**

### Expected Solution

The Direct executor should generate synthetic JSON activity events that emulate what subprocess executors produce:

1. **On LLM Ingress** (prompt sent):
   ```json
   {
     "type": "api_request_started",
     "timestamp": 1737495882.123,
     "request": {
       "model": "llama-pro",
       "prompt_length": 245,
       "endpoint": "http://localhost:11434/v1/chat/completions"
     }
   }
   ```

2. **On LLM Egress** (response received):
   ```json
   {
     "type": "api_response_received",
     "timestamp": 1737495885.456,
     "response": {
       "content": "The capital of Iraq is Baghdad.",
       "eval_count": 12,
       "total_duration": 3333,
       "model": "llama-pro"
     }
   }
   ```

3. **Completion Indicator**:
   ```json
   {
     "say": "completion_result",
     "text": "The capital of Iraq is Baghdad."
   }
   ```

These should be wrapped with:
- Timestamp envelope (via pipeline's `timestamp_activity()`)
- Executor attribution (`"executor": "direct"`)
- Written to `$id-oneshot-log.json` as NDJSON

## Implementation Steps

### Step 1: Modify DirectExecutor.execute() to Generate Activity Stream

**File:** `src/oneshot/providers/direct_executor.py`

**Current Implementation** (lines 78-107):
```python
@contextmanager
def execute(self, prompt: str) -> Generator[str, None, None]:
    if not self.client.check_connection():
        raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}")

    try:
        ollama_response: OllamaResponse = self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=False
        )
        yield ollama_response.response
    finally:
        pass
```

**New Implementation:**
```python
@contextmanager
def execute(self, prompt: str) -> Generator[Union[str, Dict[str, Any]], None, None]:
    """
    Execute a task via Ollama HTTP API and yield activity events.

    Generates synthetic JSON activity events on LLM ingress/egress to emulate
    streaming activity from subprocess-based executors.

    Args:
        prompt (str): The task prompt to execute

    Yields:
        Union[str, Dict[str, Any]]: Activity objects (dicts) or status messages (strings)

    Raises:
        RuntimeError: If connection fails or API error occurs
    """
    if not self.client.check_connection():
        raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}")

    try:
        # 1. Yield LLM INGRESS activity (prompt sent to model)
        ingress_activity = {
            "type": "api_request_started",
            "timestamp": time.time(),
            "request": {
                "model": self.model,
                "prompt_length": len(prompt),
                "endpoint": self.base_url
            }
        }
        yield ingress_activity

        # 2. Make API call to Ollama
        start_time = time.time()
        ollama_response: OllamaResponse = self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=False
        )
        duration_ms = (time.time() - start_time) * 1000

        # 3. Yield LLM EGRESS activity (response received from model)
        egress_activity = {
            "type": "api_response_received",
            "timestamp": time.time(),
            "response": {
                "content_length": len(ollama_response.response),
                "eval_count": ollama_response.eval_count,
                "total_duration": ollama_response.total_duration,
                "duration_ms": duration_ms,
                "model": self.model
            }
        }
        yield egress_activity

        # 4. Yield completion result in Cline-compatible format
        # This format is recognized by the UI formatter and result extractor
        completion_activity = {
            "say": "completion_result",
            "text": ollama_response.response.strip()
        }
        yield completion_activity

    finally:
        # No cleanup needed for HTTP API
        pass
```

**Changes:**
- Import `time` at the top of the file
- Change return type annotation to `Generator[Union[str, Dict[str, Any]], None, None]`
- Generate 3 synthetic activity objects:
  1. `api_request_started` - on prompt ingress
  2. `api_response_received` - on response egress
  3. `completion_result` - final result in Cline-compatible format
- Each activity is a dict that will be parsed by the pipeline

### Step 2: Update DirectExecutor Type Hints

**File:** `src/oneshot/providers/direct_executor.py`

**Line 8** - Update imports:
```python
from typing import Dict, Any, List, Optional, Tuple, Generator, Union
```

Add `Union` to the imports to support the new return type.

### Step 3: Verify Pipeline Compatibility

**File:** `src/oneshot/pipeline.py`

**No changes needed** - the pipeline is already designed to handle both strings and dicts:
- `extract_json_objects()` (line 61) handles both string preamble and JSON dicts
- `timestamp_activity()` (line 150) wraps any item in TimestampedActivity
- The pipeline will correctly process the activity dicts from DirectExecutor

### Step 4: Update UI Callback to Handle Direct Executor Activities

**File:** `src/oneshot/oneshot.py`

**Current Implementation** (lines 124-179) already handles:
- `data.get('say', 'unknown')` for activity type identification
- `'completion_result'` specifically (line 160)
- `'api_req_started'` specifically (line 163)

**Add handling for Direct executor's new activity types** (insert after line 172):
```python
            elif activity_type == 'api_request_started':
                # Direct executor API request start
                print(f"\n🔄 API request initiated")
            elif activity_type == 'api_response_received':
                # Direct executor API response
                print(f"\n✅ API response received")
```

**Note:** The completion_result format is already handled, so the final output will display correctly.

### Step 5: Verify Activity Logger Integration

**File:** `src/oneshot/providers/activity_logger.py`

**No changes needed** - ActivityLogger already supports:
- `log_enhanced_activity()` with arbitrary data dicts (line 96)
- `log_executor_interaction()` for request/response logging (line 169)
- The new activity objects will be logged correctly to NDJSON

### Step 6: Update ResultExtractor for Direct Executor

**File:** Check if `src/oneshot/protocol.py` or similar contains `ResultExtractor`

**Investigation needed:** Verify that ResultExtractor can parse the `completion_result` format from Direct executor's activity log.

**Expected behavior:**
- ResultExtractor should find the `{"say":"completion_result","text":"..."}` entry
- Extract the `text` field as the worker result
- Pass it to the auditor prompt generator

**If changes needed:**
- Update scoring logic to recognize Direct executor's completion format
- Ensure `extract_result()` method handles NDJSON from Direct executor

### Step 7: Test Activity Log Format

**File:** Create test to verify NDJSON format

**Expected NDJSON output** in `$id-oneshot-log.json`:
```json
{"timestamp":1737495882.123,"data":{"type":"api_request_started","timestamp":1737495882.123,"request":{"model":"llama-pro","prompt_length":245,"endpoint":"http://localhost:11434/v1/chat/completions"}},"executor":"worker","is_heartbeat":false}
{"timestamp":1737495885.456,"data":{"type":"api_response_received","timestamp":1737495885.456,"response":{"content_length":28,"eval_count":12,"total_duration":3333,"duration_ms":3333.45,"model":"llama-pro"}},"executor":"worker","is_heartbeat":false}
{"timestamp":1737495885.457,"data":{"say":"completion_result","text":"The capital of Iraq is Baghdad."},"executor":"worker","is_heartbeat":false}
```

**Verification:**
1. Each line is valid JSON (can be parsed with `json.loads()`)
2. Contains `timestamp` field (from pipeline's `timestamp_activity()`)
3. Contains `executor` field (`"worker"` or `"auditor"`)
4. Contains `data` field with the activity object
5. Contains `is_heartbeat` field (always false for real activities)

### Step 8: Update Auditor Prompt Generation

**File:** `src/oneshot/engine.py` (lines 514-545)

**Current Implementation:**
```python
def _generate_auditor_prompt(self) -> str:
    # ...
    log_path = self._get_context_value('session_log_path', 'oneshot-log.json')
    worker_result_summary = self.result_extractor.extract_result(log_path)
    # ...
```

**Verification needed:**
- Ensure `ResultExtractor.extract_result()` can parse Direct executor's NDJSON
- Look for `{"say":"completion_result","text":"..."}` in the NDJSON
- Extract the text field correctly

**If changes needed:**
- Update `ResultExtractor` to handle Direct executor's activity format
- Ensure it scores `completion_result` activities highly

### Step 9: Add Code Comments and Documentation

**File:** `src/oneshot/providers/direct_executor.py`

Add detailed comments explaining:
- Why Direct executor generates synthetic activity events
- The format of each activity type
- How they emulate subprocess executor behavior
- Reference to the architecture doc

**Example:**
```python
# Direct Executor Activity Stream Design
#
# Unlike subprocess-based executors (Cline, Claude, Aider) which naturally produce
# streaming JSON output, Direct executor makes synchronous HTTP API calls and receives
# complete responses. To maintain compatibility with the oneshot pipeline architecture,
# Direct executor generates synthetic JSON activity events that emulate the streaming
# behavior of subprocess executors.
#
# Activity Event Types:
# 1. api_request_started - Emitted when sending prompt to LLM (ingress)
# 2. api_response_received - Emitted when receiving response from LLM (egress)
# 3. completion_result - Final output in Cline-compatible format
#
# These events flow through the pipeline's stages:
# - ingest_stream: Receives the generator
# - timestamp_activity: Wraps each event with ingestion timestamp
# - InactivityMonitor: Detects timeouts (N/A for sync HTTP, but included for consistency)
# - log_activity: Writes to NDJSON log file
# - parse_activity: Interprets for UI display
#
# See docs/streaming-and-state-management.md for architecture details.
```

### Step 10: Update Direct Executor Documentation

**File:** `docs/direct-executor.md`

Add section explaining the activity logging implementation:

```markdown
## Activity Logging Implementation

The Direct executor generates synthetic JSON activity events to maintain compatibility
with the oneshot streaming pipeline architecture, despite using synchronous HTTP API
calls rather than subprocess streaming.

### Activity Event Types

#### 1. API Request Started (LLM Ingress)
Emitted when the prompt is sent to the model:
```json
{
  "type": "api_request_started",
  "timestamp": 1737495882.123,
  "request": {
    "model": "llama-pro",
    "prompt_length": 245,
    "endpoint": "http://localhost:11434/v1/chat/completions"
  }
}
```

#### 2. API Response Received (LLM Egress)
Emitted when the response is received from the model:
```json
{
  "type": "api_response_received",
  "timestamp": 1737495885.456,
  "response": {
    "content_length": 28,
    "eval_count": 12,
    "total_duration": 3333,
    "duration_ms": 3333.45,
    "model": "llama-pro"
  }
}
```

#### 3. Completion Result
Emitted with the final response in Cline-compatible format:
```json
{
  "say": "completion_result",
  "text": "The capital of Iraq is Baghdad."
}
```

### NDJSON Log Format

Activities are wrapped by the pipeline with timestamp and executor metadata:
```json
{"timestamp":1737495882.123,"data":{...},"executor":"worker","is_heartbeat":false}
```

### Auditor Integration

The auditor prompt generation uses `ResultExtractor` to parse the NDJSON log and
extract the completion result. The `{"say":"completion_result","text":"..."}` format
is compatible with Cline executor's output format, allowing the same result extraction
logic to work across all executors.
```

## Success Criteria

### Functional Requirements
- ✅ Direct executor emits JSON activity objects instead of raw strings
- ✅ Activity objects are properly timestamped by the pipeline
- ✅ NDJSON log file (`$id-oneshot-log.json`) contains valid JSON lines with:
  - `timestamp` field (ingestion time)
  - `executor` field (`"worker"` or `"auditor"`)
  - `data` field (the activity object)
  - `is_heartbeat` field (false for real activities)
- ✅ UI displays activity correctly (no "Activity (unknown)" messages)
- ✅ Auditor prompt generation can extract worker results from Direct executor logs
- ✅ Activity log is compatible with existing tooling (can be parsed as NDJSON)

### Display Requirements
When running `oneshot --executor direct "what is the capital of iraq?"`, the output should show:
```
🔄 API request initiated
✅ API response received
✅ The capital of Iraq is Baghdad.
```

Instead of:
```
📋 Activity (unknown):
📋 Activity (unknown):
```

### Integration Requirements
- ✅ Direct executor works with worker role
- ✅ Direct executor works with auditor role
- ✅ Auditor can parse Direct executor's worker output
- ✅ Multi-iteration flows work correctly (worker → auditor → worker loop)
- ✅ Session logs contain complete activity history

## Testing Strategy

### Unit Tests
**File:** `tests/test_direct_executor.py`

```python
def test_direct_executor_generates_activity_objects():
    """Test that Direct executor yields activity dicts, not raw strings."""
    executor = DirectExecutor(model="llama-pro", base_url="http://localhost:11434")

    with executor.execute("Test prompt") as stream:
        activities = list(stream)

        # Should yield 3 activities
        assert len(activities) == 3

        # First: API request started
        assert isinstance(activities[0], dict)
        assert activities[0]['type'] == 'api_request_started'
        assert 'request' in activities[0]
        assert activities[0]['request']['model'] == 'llama-pro'

        # Second: API response received
        assert isinstance(activities[1], dict)
        assert activities[1]['type'] == 'api_response_received'
        assert 'response' in activities[1]

        # Third: Completion result (Cline-compatible)
        assert isinstance(activities[2], dict)
        assert activities[2]['say'] == 'completion_result'
        assert 'text' in activities[2]
        assert len(activities[2]['text']) > 0

def test_direct_executor_activity_has_timestamps():
    """Test that activity objects contain timestamp fields."""
    executor = DirectExecutor(model="llama-pro", base_url="http://localhost:11434")

    with executor.execute("Test prompt") as stream:
        for activity in stream:
            if isinstance(activity, dict):
                assert 'timestamp' in activity
                assert isinstance(activity['timestamp'], (int, float))

def test_direct_executor_ndjson_format():
    """Test that activities can be serialized to valid NDJSON."""
    executor = DirectExecutor(model="llama-pro", base_url="http://localhost:11434")

    with executor.execute("Test prompt") as stream:
        for activity in stream:
            if isinstance(activity, dict):
                # Should be JSON-serializable
                json_str = json.dumps(activity)
                # Should be parseable back
                parsed = json.loads(json_str)
                assert parsed == activity
```

### Integration Tests
**File:** `tests/test_direct_integration.py`

```python
def test_direct_executor_with_pipeline():
    """Test that Direct executor output flows through the pipeline correctly."""
    from oneshot.pipeline import build_pipeline
    import tempfile
    import json

    executor = DirectExecutor(model="llama-pro", base_url="http://localhost:11434")

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        log_path = f.name

    try:
        with executor.execute("What is 2+2?") as stream:
            pipeline = build_pipeline(
                stream,
                log_path,
                inactivity_timeout=30.0,
                executor_name="worker"
            )

            events = list(pipeline)

            # Should have timestamped events
            assert len(events) > 0
            for event in events:
                assert hasattr(event, 'timestamp')
                assert hasattr(event, 'data')
                assert hasattr(event, 'executor')

        # Verify NDJSON log file
        with open(log_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 3  # At least 3 activity objects

            for line in lines:
                # Each line should be valid JSON
                obj = json.loads(line)
                assert 'timestamp' in obj
                assert 'executor' in obj
                assert 'data' in obj
                assert 'is_heartbeat' in obj
    finally:
        import os
        if os.path.exists(log_path):
            os.remove(log_path)

def test_direct_executor_auditor_can_parse_worker_result():
    """Test that auditor can extract results from Direct executor's activity log."""
    from oneshot.protocol import ResultExtractor
    import tempfile
    import json

    # Create a mock NDJSON log with Direct executor's completion format
    activities = [
        {
            "timestamp": 1737495882.123,
            "data": {
                "type": "api_request_started",
                "timestamp": 1737495882.123,
                "request": {"model": "llama-pro", "prompt_length": 10}
            },
            "executor": "worker",
            "is_heartbeat": False
        },
        {
            "timestamp": 1737495885.456,
            "data": {
                "type": "api_response_received",
                "timestamp": 1737495885.456,
                "response": {"content_length": 28, "eval_count": 12}
            },
            "executor": "worker",
            "is_heartbeat": False
        },
        {
            "timestamp": 1737495885.457,
            "data": {
                "say": "completion_result",
                "text": "The answer is 4."
            },
            "executor": "worker",
            "is_heartbeat": False
        }
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        for activity in activities:
            f.write(json.dumps(activity) + '\n')
        log_path = f.name

    try:
        extractor = ResultExtractor()
        result_summary = extractor.extract_result(log_path)

        # Should extract the completion result text
        assert result_summary is not None
        assert result_summary.result == "The answer is 4."
        assert result_summary.score > 0
    finally:
        import os
        if os.path.exists(log_path):
            os.remove(log_path)
```

### Manual Verification Steps
1. **Test Direct Executor with Simple Query:**
   ```bash
   oneshot --executor direct --verbose "What is the capital of Iraq?"
   ```
   - Should see "🔄 API request initiated"
   - Should see "✅ API response received"
   - Should see the answer displayed
   - Should NOT see "Activity (unknown)"

2. **Verify NDJSON Log File:**
   ```bash
   oneshot --executor direct "Test query"
   cat oneshot_*-oneshot-log.json | jq '.'
   ```
   - Each line should parse as valid JSON
   - Should contain `timestamp`, `executor`, `data`, `is_heartbeat` fields
   - Should have activity objects with types: `api_request_started`, `api_response_received`, `completion_result`

3. **Test Worker-Auditor Flow:**
   ```bash
   oneshot --executor direct --max-iterations 3 "Write a function that adds two numbers"
   ```
   - Worker should execute and generate activity
   - Auditor should receive worker output in prompt
   - Auditor should render a verdict (DONE/RETRY/IMPOSSIBLE)
   - System should complete successfully or iterate

4. **Test Activity Log Parsing:**
   ```bash
   # After running a Direct executor task
   python -c "
   import json
   with open('oneshot_*-oneshot-log.json', 'r') as f:
       for line in f:
           obj = json.loads(line)
           print(f\"Timestamp: {obj['timestamp']}, Type: {obj['data'].get('type', obj['data'].get('say'))}\")
   "
   ```
   - Should print timestamps and activity types
   - Should NOT raise JSON parsing errors

## Risk Assessment

### Risk 1: Breaking Existing Direct Executor Functionality
**Likelihood:** Low
**Impact:** High
**Mitigation:**
- Run existing `test_direct_executor.py` tests before and after changes
- Verify `run_task()` method still works (it's used in some code paths)
- Test both streaming path (`execute()`) and non-streaming path (`run_task()`)
- Keep `run_task()` unchanged initially, only modify `execute()`

### Risk 2: Activity Format Incompatibility
**Likelihood:** Medium
**Impact:** Medium
**Mitigation:**
- Use the same `{"say":"completion_result","text":"..."}` format as Cline executor
- Test with existing `ResultExtractor` logic
- Add unit tests to verify activity object structure
- Check that pipeline's `extract_json_objects()` handles the new format

### Risk 3: NDJSON Serialization Issues
**Likelihood:** Low
**Impact:** Medium
**Mitigation:**
- Ensure all activity objects are JSON-serializable (no datetime objects, etc.)
- Use `json.dumps()` in tests to verify serializability
- Test with ActivityLogger to ensure proper NDJSON formatting
- Verify each line in log file is valid JSON

### Risk 4: Auditor Cannot Parse Direct Executor Logs
**Likelihood:** Medium
**Impact:** High
**Mitigation:**
- Investigate `ResultExtractor` implementation before making changes
- Use Cline-compatible `completion_result` format
- Add integration test for auditor parsing
- Test full worker→auditor→worker iteration flow

### Risk 5: Performance Regression
**Likelihood:** Low
**Impact:** Low
**Mitigation:**
- Direct executor still makes single HTTP call (no performance change)
- Activity generation is lightweight (3 dict constructions)
- No additional I/O operations beyond existing logging
- Test with `--verbose` flag to measure execution time

### Risk 6: Timestamp Duplication
**Likelihood:** Low
**Impact:** Low
**Mitigation:**
- Activity objects include their own `timestamp` field
- Pipeline's `timestamp_activity()` adds ingestion timestamp at wrapper level
- These serve different purposes and don't conflict
- Document the dual-timestamp design in code comments

## Code Samples

### Updated DirectExecutor.execute() Method

```python
@contextmanager
def execute(self, prompt: str) -> Generator[Union[str, Dict[str, Any]], None, None]:
    """
    Execute a task via Ollama HTTP API and yield activity events.

    Direct Executor Activity Stream Design
    ======================================
    Unlike subprocess-based executors (Cline, Claude, Aider) which naturally produce
    streaming JSON output, Direct executor makes synchronous HTTP API calls and receives
    complete responses. To maintain compatibility with the oneshot pipeline architecture,
    Direct executor generates synthetic JSON activity events that emulate the streaming
    behavior of subprocess executors.

    Activity Event Types:
    1. api_request_started - Emitted when sending prompt to LLM (ingress)
    2. api_response_received - Emitted when receiving response from LLM (egress)
    3. completion_result - Final output in Cline-compatible format

    These events flow through the pipeline's stages:
    - ingest_stream: Receives the generator
    - extract_json_objects: Parses JSON from stream
    - timestamp_activity: Wraps each event with ingestion timestamp
    - InactivityMonitor: Detects timeouts
    - log_activity: Writes to NDJSON log file
    - parse_activity: Interprets for UI display

    See docs/streaming-and-state-management.md for architecture details.

    Args:
        prompt (str): The task prompt to execute

    Yields:
        Union[str, Dict[str, Any]]: Activity objects (dicts) representing LLM interactions

    Raises:
        RuntimeError: If connection fails or API error occurs
    """
    if not self.client.check_connection():
        raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}")

    try:
        # === LLM INGRESS ===
        # Generate activity event for prompt being sent to model
        ingress_activity = {
            "type": "api_request_started",
            "timestamp": time.time(),
            "request": {
                "model": self.model,
                "prompt_length": len(prompt),
                "endpoint": self.base_url
            }
        }
        yield ingress_activity

        # === API CALL ===
        # Make synchronous HTTP call to Ollama/OpenAI-compatible endpoint
        start_time = time.time()
        ollama_response: OllamaResponse = self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=False  # Non-streaming for simplicity
        )
        duration_ms = (time.time() - start_time) * 1000

        # === LLM EGRESS ===
        # Generate activity event for response received from model
        egress_activity = {
            "type": "api_response_received",
            "timestamp": time.time(),
            "response": {
                "content_length": len(ollama_response.response),
                "eval_count": ollama_response.eval_count,
                "total_duration": ollama_response.total_duration,
                "duration_ms": duration_ms,
                "model": self.model
            }
        }
        yield egress_activity

        # === COMPLETION RESULT ===
        # Generate completion activity in Cline-compatible format
        # This format is recognized by:
        # - ResultExtractor for auditor prompt generation
        # - UI formatter for display
        completion_activity = {
            "say": "completion_result",
            "text": ollama_response.response.strip()
        }
        yield completion_activity

    finally:
        # No cleanup needed for HTTP API (no subprocess to terminate)
        pass
```

### Example NDJSON Log Output

After running `oneshot --executor direct "What is 2+2?"`, the `$id-oneshot-log.json` file should contain:

```json
{"timestamp":1737495882.123,"data":{"type":"api_request_started","timestamp":1737495882.123,"request":{"model":"llama-pro","prompt_length":245,"endpoint":"http://localhost:11434/v1/chat/completions"}},"executor":"worker","is_heartbeat":false}
{"timestamp":1737495885.456,"data":{"type":"api_response_received","timestamp":1737495885.456,"response":{"content_length":14,"eval_count":8,"total_duration":3333,"duration_ms":3333.45,"model":"llama-pro"}},"executor":"worker","is_heartbeat":false}
{"timestamp":1737495885.457,"data":{"say":"completion_result","text":"2 + 2 = 4"},"executor":"worker","is_heartbeat":false}
```

Each line:
- Is valid JSON (can be parsed with `json.loads()`)
- Has `timestamp` (ingestion time from pipeline)
- Has `executor` (`"worker"` or `"auditor"`)
- Has `data` (the activity object from DirectExecutor)
- Has `is_heartbeat` (false for real activities)

### UI Output Example

Before (broken):
```
$ oneshot --executor direct "What is the capital of Iraq?"
📋 Activity (unknown):
📋 Activity (unknown):
```

After (fixed):
```
$ oneshot --executor direct "What is the capital of Iraq?"
🔄 API request initiated
✅ API response received
✅ The capital of Iraq is Baghdad.
```

## Implementation Checklist

### Phase 1: Core Implementation
- [ ] Update imports in `direct_executor.py` to include `Union` type hint
- [ ] Import `time` module in `direct_executor.py`
- [ ] Rewrite `DirectExecutor.execute()` to generate activity stream (3 activities)
- [ ] Update return type annotation to `Generator[Union[str, Dict[str, Any]], None, None]`
- [ ] Add comprehensive docstring explaining activity stream design
- [ ] Add inline comments for each activity generation step

### Phase 2: UI Integration
- [ ] Update `_print_pipeline_event()` in `oneshot.py` to handle new activity types
- [ ] Add display logic for `api_request_started` activity
- [ ] Add display logic for `api_response_received` activity
- [ ] Verify `completion_result` handling (should already work)

### Phase 3: Testing
- [ ] Write unit test: `test_direct_executor_generates_activity_objects()`
- [ ] Write unit test: `test_direct_executor_activity_has_timestamps()`
- [ ] Write unit test: `test_direct_executor_ndjson_format()`
- [ ] Write integration test: `test_direct_executor_with_pipeline()`
- [ ] Write integration test: `test_direct_executor_auditor_can_parse_worker_result()`
- [ ] Run existing Direct executor tests to ensure no regression

### Phase 4: Manual Verification
- [ ] Test with simple query: `oneshot --executor direct "What is 2+2?"`
- [ ] Verify no "Activity (unknown)" messages
- [ ] Check NDJSON log file format with `jq`
- [ ] Test worker-auditor iteration flow
- [ ] Test with different models (if available)

### Phase 5: Documentation
- [ ] Add code comments explaining activity stream design in `direct_executor.py`
- [ ] Update `docs/direct-executor.md` with activity logging section
- [ ] Add example NDJSON log output to documentation
- [ ] Document the relationship between Direct executor's timestamps and pipeline timestamps
- [ ] Update `docs/overview.md` to mention Direct executor's activity logging

### Phase 6: Validation
- [ ] Verify ResultExtractor can parse Direct executor logs
- [ ] Test auditor prompt generation with Direct executor worker output
- [ ] Verify multi-iteration flows work correctly
- [ ] Check that session logs are complete and parseable
- [ ] Run full integration test suite

## Notes

### Design Decisions

1. **Why generate synthetic activities?**
   - Direct executor uses HTTP API, not subprocess
   - No natural streaming output like Cline/Claude executors
   - Pipeline expects JSON activity stream
   - Synthetic activities maintain architectural consistency

2. **Why use Cline-compatible format for completion?**
   - ResultExtractor already parses `{"say":"completion_result","text":"..."}`
   - Auditor prompt generation works without modification
   - UI formatter handles this format
   - Avoids creating executor-specific parsing logic

3. **Why include timestamps in activity objects?**
   - Provides timing information for each API call stage
   - Helps with debugging and performance analysis
   - Distinct from pipeline's ingestion timestamp
   - Activity timestamp = when event occurred
   - Pipeline timestamp = when event was processed

4. **Why 3 separate activities instead of 1?**
   - Matches granularity of subprocess executors
   - Allows UI to show progress (request → response → completion)
   - Provides detailed timing information
   - Makes logs more useful for debugging

### Future Enhancements

1. **Streaming API Support**
   - Ollama supports streaming via `stream=True`
   - Could yield incremental text chunks as they arrive
   - Would provide real-time updates like subprocess executors
   - Requires handling partial responses and chunking

2. **Additional Activity Types**
   - `api_error` for error conditions
   - `api_retry` for retry attempts
   - `model_loading` for model load events (if detectable)
   - `token_usage` for token counting

3. **Enhanced Metadata**
   - Request/response headers
   - API version information
   - Model parameters (temperature, top_p, etc.)
   - Server health metrics

4. **Activity Filtering**
   - Option to suppress verbose activities
   - Configurable activity logging levels
   - UI preferences for activity display

## References

- **Source:** dev_notes/specs/2026-01-30_00-30-06_prompt-18.md
- **Architecture:** `docs/streaming-and-state-management.md`
- **Direct Executor:** `docs/direct-executor.md`
- **Activity Format:** `docs/cline-activity-json.md`
- **Project Structure:** `docs/project-structure.md`
- **Templates:** `docs/templates.md`
