# Cline Streaming Capability Research
**Date:** 2026-01-17
**Related Project Plan:** dev_notes/project_plans/2026-01-17_23-16-01_cline_streaming_research_and_experiments.md

## Executive Summary
This document presents research findings on cline's streaming capabilities, output format options, task file structure, and integration points for the oneshot tool. The research confirms that cline supports JSON output format and stores detailed task information in `$HOME/.cline/data/tasks/$task_id` directories.

## Cline Version Information
```
Cline CLI Version:  1.0.9
Cline Core Version: 3.47.0
Commit:             2ebbe95
Built:              2026-01-08T22:15:09Z
Built by:           runner
Go version:         go1.24.11
OS/Arch:            linux/amd64
```

## Command-Line Interface

### Available Output Formats
Cline supports three output formats via the `-F` or `--output-format` flag:
- `rich` (default) - Rich terminal UI with colors and formatting
- `json` - Structured JSON output for programmatic parsing
- `plain` - Plain text output without formatting

### Key Flags for Non-Interactive Execution
```bash
cline [prompt] \
  --yolo / -y / --no-interactive   # Enable non-interactive mode
  --oneshot / -o                    # Full autonomous mode
  --output-format json / -F json    # JSON output format
  --mode plan|act / -m              # Execution mode (default: plan)
  --verbose / -v                    # Verbose output
```

### Current oneshot.py Implementation
The existing code (src/oneshot/oneshot.py:298) uses:
```python
cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', prompt]
```

**Finding:** The current implementation does NOT use `--output-format json`, which means it's receiving rich terminal output instead of structured JSON.

## Task Directory Structure

### Location
Tasks are stored in: `$HOME/.cline/data/tasks/$task_id/`

Where `$task_id` is a Unix timestamp in milliseconds (e.g., `1768622672614`).

### Files in Each Task Directory

#### 1. task_metadata.json
Contains:
- **files_in_context**: Array of files with read/edit tracking
  - `path`: File path
  - `record_state`: "active" | "stale"
  - `record_source`: "read_tool" | "cline_edited"
  - `cline_read_date`: Timestamp (ms)
  - `cline_edit_date`: Timestamp (ms) or null
  - `user_edit_date`: Timestamp (ms) or null

- **model_usage**: Array of model usage records
  - `ts`: Timestamp (ms)
  - `model_id`: Model identifier
  - `model_provider_id`: Provider (e.g., "cline")
  - `mode`: "plan" | "act"

- **environment_history**: Array of environment snapshots
  - `ts`: Timestamp (ms)
  - `os_name`, `os_version`, `os_arch`
  - `host_name`, `host_version`
  - `cline_version`

**Activity Detection Value:** The `cline_edit_date` and timestamp fields in `task_metadata.json` can be monitored to detect task activity.

#### 2. settings.json
Contains task-specific settings:
```json
{
  "yoloModeToggled": true
}
```

#### 3. ui_messages.json
Array of UI messages showing task progression:
- Message types: "say", "checkpoint_created", etc.
- Each message has:
  - `ts`: Timestamp (ms)
  - `type`: Message type
  - `text`: Message content (for "say" type)
  - `modelInfo`: Provider and model details
  - `conversationHistoryIndex`: Index in conversation

**Activity Detection Value:** New messages being appended to `ui_messages.json` indicates active task execution. File modification time can be monitored.

#### 4. api_conversation_history.json
Full API conversation history with:
- `role`: "user" | "assistant"
- `content`: Array of content blocks
  - `type`: "text" | "image" | etc.
  - `text`: Content text
  - Environment details and task context

**Activity Detection Value:** Similar to ui_messages.json, this file is updated as the task progresses.

#### 5. focus_chain_taskid_{task_id}.md
Markdown file tracking the task's focus chain and progress.

### Activity Monitoring Strategy
The most reliable activity indicators are:
1. **File modification timestamps** on `ui_messages.json` and `api_conversation_history.json`
2. **File size growth** as new messages are appended
3. **Timestamp fields** in `task_metadata.json` being updated

**Implementation Approach:**
```python
import os
import time
from pathlib import Path

def monitor_task_activity(task_dir: Path, interval: int = 5) -> bool:
    """
    Monitor task directory for activity by checking file modification times.

    Returns True if activity detected, False if idle for too long.
    """
    ui_messages_file = task_dir / "ui_messages.json"
    api_history_file = task_dir / "api_conversation_history.json"

    last_modified = max(
        ui_messages_file.stat().st_mtime if ui_messages_file.exists() else 0,
        api_history_file.stat().st_mtime if api_history_file.exists() else 0
    )

    # Check every interval seconds
    time.sleep(interval)

    current_modified = max(
        ui_messages_file.stat().st_mtime if ui_messages_file.exists() else 0,
        api_history_file.stat().st_mtime if api_history_file.exists() else 0
    )

    return current_modified > last_modified
```

## JSON Output Format Testing

### Challenge: TTY Requirement
When testing cline with JSON output format via stdin (e.g., `echo "test" | cline --output-format json --yolo --oneshot`), the following error occurs:
```
Error: huh: could not open a new TTY: open /dev/tty: no such device or address
```

**Finding:** Even with `--yolo` and `--no-interactive` flags, cline attempts to open /dev/tty when receiving input via stdin/pipe.

### Current Integration Method
The existing oneshot.py implementation passes the prompt as a command-line argument:
```python
cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', prompt]
```

This avoids the TTY issue since the prompt is not piped via stdin.

### Recommendation
To enable JSON output, modify the command to:
```python
cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', '--output-format', 'json', prompt]
```

**Next Step Required:** Test this with actual cline execution to capture the JSON output structure and validate parsing.

## Buffering Behavior Analysis

### Current Implementation
The current code uses `capture_output=True` in subprocess.run():
```python
result = subprocess.run(
    cmd,
    text=True,
    capture_output=True,
    timeout=initial_timeout
)
```

### Buffering Implications
- **capture_output=True**: Buffers all output until process completes
- **No streaming**: Cannot detect activity or process output in real-time
- **Timeout handling**: Limited to simple timeout expiry detection

### Proposed Streaming Approach
Replace with streaming subprocess execution:
```python
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0  # Unbuffered
)

# Read output in real-time
for line in process.stdout:
    # Process JSON messages as they arrive
    handle_json_message(line)
```

## Integration Points for Oneshot Tool

### 1. Command Construction
**Current:**
```python
cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', prompt]
```

**Proposed:**
```python
def call_executor(prompt, model, executor="claude", output_format=None, ...):
    if executor == "cline":
        cmd = ['cline', '--yolo', '--no-interactive', '--oneshot']

        # Add output format if specified
        if output_format == "json":
            cmd.extend(['--output-format', 'json'])

        cmd.append(prompt)
```

### 2. Activity Monitoring
**Current:** No activity monitoring for cline executor

**Proposed:**
- Option A: Monitor task directory files for modifications
- Option B: Parse streaming JSON output for progress indicators
- Option C: Hybrid approach using both methods

### 3. Timeout Handling
**Current:** Simple timeout expiry

**Proposed:**
- Initial timeout before activity monitoring kicks in
- Extended timeout with activity checks
- Terminate process if no activity detected for N seconds

## Next Steps

### Phase 2: Buffering and Streaming Experiments
1. Test cline with `--output-format json` and capture actual JSON message structure
2. Implement streaming subprocess execution with `Popen` and unbuffered I/O
3. Test different buffer sizes (0, 4096, 8192) and measure latency
4. Implement real-time JSON parsing with error handling for partial messages

### Phase 3: File-Based Activity Monitoring
1. Implement task directory detection (extract task_id from cline process)
2. Build file monitoring system using os.stat() for modification times
3. Test accuracy of activity detection across different task types
4. Implement fallback to process monitoring if file monitoring fails

### Phase 4: Performance Experiments
1. **Experiment A**: Measure output latency with different buffer sizes
2. **Experiment B**: Compare activity detection accuracy (file vs process)
3. **Experiment C**: Monitor resource usage (CPU, memory) during streaming
4. **Experiment D**: Test JSON parsing performance and error handling

## Risk Assessment

### High Risk
- **JSON output format may change structure**: Need robust parsing with error handling
- **Task directory location/format may change**: Implement version detection and fallbacks

### Medium Risk
- **File-based monitoring permission issues**: Handle gracefully with fallback to process monitoring
- **Performance overhead**: Minimize by using efficient file stat() calls

### Low Risk
- **Backward compatibility**: Changes are additive and can be feature-flagged
- **Integration complexity**: Well-defined boundaries for modifications

## Conclusion
Cline provides sufficient capabilities for streaming integration:
- ✅ JSON output format available (`--output-format json`)
- ✅ Task directory structure well-defined and accessible
- ✅ Activity indicators present (file modification times, timestamps)
- ⚠️  TTY requirement needs testing with direct argument passing (not stdin)
- 🔄 Further testing required for JSON message structure validation

**Recommendation:** Proceed with Phase 2 implementation to enable JSON output and test actual message structure before implementing streaming logic.
