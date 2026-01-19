#!/usr/bin/env python3
"""
Oneshot - Autonomous task completion with auditor validation
"""

import argparse
import asyncio
import json
import os
import platform
import pty
import re
import select
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# Import activity visualization components
from oneshot.providers.activity_interpreter import get_interpreter, ActivityType
from oneshot.providers.activity_formatter import ActivityFormatter, format_for_display
from oneshot.events import emit_executor_activity

# ============================================================================
# TEST CONFIGURATION - Prevent blocking subprocess calls in tests
# ============================================================================

# Set ONESHOT_TEST_MODE=1 to prevent blocking subprocess calls
TEST_MODE = os.environ.get('ONESHOT_TEST_MODE', '0') == '1'

def _check_test_mode_blocking():
    """Raise exception if test mode is enabled and blocking call is attempted."""
    if TEST_MODE:
        import traceback
        stack = ''.join(traceback.format_stack())
        raise RuntimeError(
            f"BLOCKED: Subprocess call attempted in test mode!\n"
            f"All subprocess.run() calls should be mocked in tests.\n"
            f"Stack trace:\n{stack}"
        )

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

VERBOSITY = 2  # 0=default, 1=verbose, 2=debug (set to 2 for debugging)

def log_info(msg):
    """Default informational message to stderr."""
    if VERBOSITY >= 0:
        print(f"[INFO] {msg}", file=sys.stderr)

def log_verbose(msg):
    """Verbose output - more details."""
    if VERBOSITY >= 1:
        print(f"[VERBOSE] {msg}", file=sys.stderr)

def log_debug(msg):
    """Debug output - detailed internals."""
    if VERBOSITY >= 2:
        print(f"[DEBUG] {msg}", file=sys.stderr)

def dump_buffer(label, content, max_lines=20):
    """Dump a buffer (with truncation if needed)."""
    if VERBOSITY >= 1:
        lines = content.split('\n')
        if len(lines) > max_lines:
            display = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"]
        else:
            display = lines
        print(f"\n[BUFFER] {label}:", file=sys.stderr)
        for line in display:
            print(f"  {line}", file=sys.stderr)

# ============================================================================
# PTY STREAMING INFRASTRUCTURE
# ============================================================================

DISABLE_STREAMING = os.environ.get('ONESHOT_DISABLE_STREAMING', '0') == '1'
SUPPORTS_PTY = platform.system() in ('Linux', 'Darwin')  # Unix/Linux and macOS


def call_executor_pty(cmd: List[str], input_data: Optional[str] = None,
                       timeout: Optional[float] = None,
                       buffer_size: int = 1024,
                       accumulation_buffer_size: int = 4096) -> Tuple[str, str, int]:
    """
    Execute command using PTY allocation for real-time streaming output.

    PTY allocation forces CLI tools to detect a terminal and use line-buffering
    instead of full buffering, enabling real-time output streaming.

    Args:
        cmd: Command and arguments as list
        input_data: Optional stdin data for the process
        timeout: Subprocess timeout in seconds
        buffer_size: Size of read buffer (1024 bytes typical for line-buffered output)
        accumulation_buffer_size: Size of accumulation buffer before activity processing (4096 bytes)

    Returns:
        Tuple of (stdout, stderr, exit_code)

    Raises:
        OSError: If PTY allocation fails
        subprocess.TimeoutExpired: If timeout is exceeded
    """
    if not SUPPORTS_PTY:
        log_debug("PTY not supported on this platform, falling back to buffered execution")
        raise OSError("PTY not supported on Windows")

    if DISABLE_STREAMING:
        log_debug("Streaming disabled via ONESHOT_DISABLE_STREAMING environment variable")
        raise OSError("Streaming disabled")

    try:
        # Allocate master and slave PTY file descriptors
        master_fd, slave_fd = pty.openpty()
        log_debug(f"PTY allocated: master={master_fd}, slave={slave_fd}")

        stdout_data = []
        stderr_data = []
        accumulation_buffer = []  # Buffer for accumulating chunks before processing
        buffer_total_bytes = 0
        chunk_count = 0
        exit_code = 1  # Default exit code
        start_time = time.time()

        try:
            # Fork and execute process
            pid = os.fork()

            if pid == 0:
                # Child process
                os.setsid()  # Create new session
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr

                # Close PTY file descriptors in child
                os.close(master_fd)
                os.close(slave_fd)

                try:
                    os.execvp(cmd[0], cmd)
                except Exception as e:
                    log_info(f"Failed to execute {cmd[0]}: {e}")
                    sys.exit(1)
            else:
                # Parent process
                os.close(slave_fd)
                log_debug(f"Child process spawned with PID {pid}")

                # Read output from master PTY with chunk accumulation
                process_exited = False
                while True:
                    # Check timeout
                    if timeout is not None:
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            import signal
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                            raise subprocess.TimeoutExpired(cmd[0], timeout)

                    # Check if process is done
                    if not process_exited:
                        try:
                            wpid, status = os.waitpid(pid, os.WNOHANG)
                            if wpid == pid:
                                exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 1
                                log_debug(f"Process exited with code {exit_code}")
                                process_exited = True

                                # Flush any remaining accumulated data
                                if accumulation_buffer:
                                    accumulated_text = ''.join(accumulation_buffer)
                                    stdout_data.append(accumulated_text)
                                    if VERBOSITY >= 1:
                                        log_verbose(f"[Accumulate] Flushed {len(accumulated_text)} chars ({len(accumulation_buffer)} chunks) on process exit")
                                    accumulation_buffer = []
                                    buffer_total_bytes = 0
                        except OSError:
                            break

                    # Read available data with select for non-blocking I/O
                    try:
                        ready, _, _ = select.select([master_fd], [], [], 0.1)
                        if ready:
                            try:
                                data = os.read(master_fd, buffer_size)
                                if data:
                                    chunk_count += 1
                                    chunk_text = data.decode('utf-8', errors='replace')
                                    accumulation_buffer.append(chunk_text)
                                    buffer_total_bytes += len(chunk_text)

                                    # Enhanced logging with more details
                                    if VERBOSITY >= 2:
                                        log_debug(f"[Chunk #{chunk_count}] {len(data)} bytes received, buffer now {buffer_total_bytes} chars")
                                        # Show preview of chunk content (first 50 chars)
                                        preview = chunk_text.replace('\n', '\\n').replace('\r', '\\r')[:50]
                                        log_debug(f"[Chunk Content] {preview}{'...' if len(chunk_text) > 50 else ''}")
                                    elif VERBOSITY >= 1:
                                        log_verbose(f"[Stream] Chunk #{chunk_count}: {len(data)} bytes, total buffered: {buffer_total_bytes}")

                                    # Check if we should flush the accumulation buffer
                                    should_flush = False

                                    # Flush on accumulation buffer size limit
                                    if buffer_total_bytes >= accumulation_buffer_size:
                                        should_flush = True
                                        flush_reason = f"buffer size limit ({accumulation_buffer_size} chars)"
                                    # Flush on complete lines (good boundary for text output)
                                    elif '\n' in chunk_text and buffer_total_bytes > 100:
                                        should_flush = True
                                        flush_reason = "line boundary detected"
                                    # Flush on JSON object boundaries (for structured output)
                                    elif ('}' in chunk_text or '{' in chunk_text) and buffer_total_bytes > 50:
                                        # Check if we have a complete JSON object
                                        accumulated_text = ''.join(accumulation_buffer)
                                        try:
                                            json.loads(accumulated_text.strip())
                                            should_flush = True
                                            flush_reason = "complete JSON object detected"
                                        except json.JSONDecodeError:
                                            # Check for multiple JSON objects
                                            lines = accumulated_text.split('\n')
                                            complete_objects = 0
                                            for line in lines:
                                                line = line.strip()
                                                if line and (line.startswith('{') and line.endswith('}')):
                                                    try:
                                                        json.loads(line)
                                                        complete_objects += 1
                                                    except json.JSONDecodeError:
                                                        pass
                                            if complete_objects > 0:
                                                should_flush = True
                                                flush_reason = f"{complete_objects} complete JSON line(s) detected"

                                    if should_flush:
                                        accumulated_text = ''.join(accumulation_buffer)
                                        stdout_data.append(accumulated_text)
                                        if VERBOSITY >= 1:
                                            log_verbose(f"[Accumulate] Flushed {len(accumulated_text)} chars ({len(accumulation_buffer)} chunks) - {flush_reason}")
                                        accumulation_buffer = []
                                        buffer_total_bytes = 0
                                else:
                                    # No more data, flush any remaining accumulated data
                                    if accumulation_buffer:
                                        accumulated_text = ''.join(accumulation_buffer)
                                        stdout_data.append(accumulated_text)
                                        if VERBOSITY >= 1:
                                            log_verbose(f"[Accumulate] Final flush: {len(accumulated_text)} chars ({len(accumulation_buffer)} chunks)")
                                        accumulation_buffer = []
                                        buffer_total_bytes = 0
                                    break
                            except OSError:
                                break
                    except Exception as e:
                        log_debug(f"Error in select/read: {e}")
                        break

                    # If process has exited and we've read all available data, break
                    if process_exited:
                        break

                # Handle stdin input if provided
                if input_data and False:  # We handle stdin via shell redirection for now
                    pass

        finally:
            # Cleanup PTY
            try:
                os.close(master_fd)
            except OSError:
                pass

        return ''.join(stdout_data), ''.join(stderr_data), exit_code

    except Exception as e:
        log_debug(f"PTY execution failed: {e}")
        raise


def parse_streaming_json(data: str) -> List[Dict[str, Any]]:
    """
    Parse streaming JSON output from CLI tools.

    Handles partial/incomplete JSON messages during streaming by buffering
    and returning complete JSON objects as they become available.

    Args:
        data: Raw streaming output containing newline-delimited JSON

    Returns:
        List of parsed JSON objects

    Raises:
        JSONDecodeError: If JSON parsing fails completely
    """
    json_objects = []
    lines = data.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
            json_objects.append(obj)
        except json.JSONDecodeError as e:
            log_debug(f"Failed to parse JSON line: {line[:100]}... ({e})")
            # Continue to next line, graceful degradation

    return json_objects


def get_cline_task_dir(task_id: str) -> Optional[Path]:
    """
    Get the task directory for a Cline task.

    Cline stores task state and progress in ~/.cline/data/tasks/$task_id/

    Args:
        task_id: The Cline task ID

    Returns:
        Path to task directory if it exists, None otherwise
    """
    home = Path.home()
    task_dir = home / '.cline' / 'data' / 'tasks' / task_id

    if task_dir.exists():
        log_debug(f"Found Cline task directory: {task_dir}")
        return task_dir

    log_debug(f"Cline task directory not found: {task_dir}")
    return None


def monitor_task_activity(task_dir: Path, timeout: float = 60.0,
                          check_interval: float = 2.0) -> bool:
    """
    Monitor task files for activity (file modification timestamps).

    Polls task directory files to detect when Cline is actively working.
    Returns False if no activity detected within timeout period.

    Args:
        task_dir: Path to Cline task directory
        timeout: Maximum time to wait for activity (seconds)
        check_interval: Time between checks (seconds)

    Returns:
        True if activity detected, False if timeout exceeded
    """
    if not task_dir.exists():
        log_debug(f"Task directory does not exist: {task_dir}")
        return False

    start_time = time.time()
    last_mtime = 0.0

    while time.time() - start_time < timeout:
        try:
            # Get the most recent modification time of any file in the directory
            current_mtime = 0.0
            for item in task_dir.rglob('*'):
                if item.is_file():
                    try:
                        mtime = item.stat().st_mtime
                        current_mtime = max(current_mtime, mtime)
                    except OSError:
                        pass

            # Activity detected if modification time changed
            if current_mtime > last_mtime:
                log_debug(f"Activity detected in task directory at {current_mtime}")
                last_mtime = current_mtime
                return True

            time.sleep(check_interval)

        except Exception as e:
            log_debug(f"Error monitoring task directory: {e}")
            return False

    log_debug(f"No activity detected in task directory after {timeout}s")
    return False

# ============================================================================
# CONFIGURATION - Edit these defaults
# ============================================================================

DEFAULT_WORKER_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_AUDITOR_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_MAX_ITERATIONS = 5
SESSION_DIR = Path.cwd()
SESSION_LOG_NAME = "session_summary.md"
ITERATION_SLEEP = 2

def get_worker_prompt(header: str = "oneshot execution") -> str:
    """
    Generate the worker prompt with a customizable header.

    Args:
        header: Custom header to prepend to the prompt

    Returns:
        Complete worker prompt string
    """
    return f"""{header}

IMPORTANT: Provide your final answer in valid JSON format when possible. Include completion indicators like "DONE", "success", or "status" even in non-JSON responses.

PREFERRED FORMAT (valid JSON):
{{
  "status": "DONE",
  "result": "<your answer/output here>",
  "confidence": "<high/medium/low>",
  "validation": "<how you verified this answer - sources, output shown, reasoning explained>",
  "execution_proof": "<what you actually did - optional if no external tools were used>"
}}

ALTERNATIVE: If JSON is difficult, include clear completion indicators:
- Words like "DONE", "success", "completed", "finished"
- Status/result fields even in malformed JSON
- Clear indication that the task is complete

IMPORTANT GUIDANCE:
- "result" should be your final answer
- "validation" should describe HOW you got it (tools used, sources checked, actual output if execution)
- "execution_proof" is optional - only include if you used external tools, commands, or computations
- For knowledge-based answers: brief validation is sufficient
- For coding tasks: describe the changes made
- Be honest and specific - don't make up results
- Set "status" to "DONE" or use completion words when you believe the task is completed

Complete this task:
"""

# Backward compatibility: default WORKER_PREFIX constant
WORKER_PREFIX = get_worker_prompt()

def get_auditor_prompt(header: str = "oneshot auditor") -> str:
    """
    Generate the auditor prompt with a customizable header.

    Args:
        header: Custom header to prepend to the prompt

    Returns:
        Complete auditor prompt string
    """
    return f"""{header}

You are a Success Auditor. Evaluate the worker's response with TRUST by default, accepting both valid JSON and responses with clear completion indicators.

The original task and project context should guide your evaluation of what "DONE" means. Be lenient and trust the worker's judgment unless there are clear, serious issues.

ACCEPT responses that show clear completion intent:
- Valid JSON with "status": "DONE" or similar
- Malformed JSON with completion words like "success", "completed", "finished"
- Plain text with clear completion indicators
- Any response that reasonably addresses the task

Only reject if there are REAL, significant issues:
1. Does the response show clear completion intent? (reject only if completely unclear)
2. Does the result seem reasonable for the task? (reject only if completely implausible)
3. Is there any indication of task completion? (reject only if entirely missing)

TRUST the worker by default:
- Accept reasonable answers even with poor formatting
- For coding tasks, trust the worker's assessment of completion
- Focus on whether the task appears addressed, not perfect JSON formatting
- Give the benefit of the doubt for subjective judgments
- Look for completion indicators: DONE, success, completed, finished, etc.

Examples of ACCEPTABLE responses:
- Valid JSON: {{"status": "DONE", "result": "Task completed"}}
- Malformed JSON: {{status: "success", result: "Answer here"}}
- Plain text: "Task completed successfully. The answer is..."
- Mixed: "DONE\n{{"result\": \"Answer\", \"status\": \"complete\"}}"

Use the original task context to provide helpful feedback if reiteration is needed.

PREFERRED FORMAT (JSON):
{{
  "verdict": "DONE",
  "reason": "<brief explanation>"
}}

ALTERNATIVE: If JSON is difficult, include clear completion indicators:
- "status": "DONE" or "verdict": "DONE" patterns
- Words like "DONE", "success", "completed", "finished"
- Clear indication that the task is complete

The system will accept both valid JSON and responses with clear completion indicators.
"""

# Backward compatibility: default AUDITOR_PROMPT constant
AUDITOR_PROMPT = get_auditor_prompt()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def extract_json(text):
    """Extract JSON object from text (handles multiline JSON). Returns the last complete JSON if multiple found."""
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    lines = text.split('\n')
    json_blocks = []
    current_json = []
    brace_count = 0
    in_json = False

    for line in lines:
        if '{' in line and not in_json:
            in_json = True
            # Extract from the opening brace onwards, preserving leading whitespace
            brace_index = line.find('{')
            # Check if text before brace is only whitespace
            prefix = line[:brace_index]
            if prefix.strip() == '':
                # Only whitespace before brace, include it
                current_json = [line]
                brace_count = line.count('{') - line.count('}')
            else:
                # Non-whitespace text before brace, extract from brace onwards
                current_json = [line[brace_index:]]
                brace_count = line[brace_index:].count('{') - line[brace_index:].count('}')
        elif in_json:
            current_json.append(line)
            brace_count += line.count('{') - line.count('}')

            if brace_count == 0 and line.strip().endswith('}'):
                json_blocks.append('\n'.join(current_json))
                in_json = False
                current_json = []

    # Return the last valid JSON block, or None if none found
    for block in reversed(json_blocks):
        try:
            json.loads(block)
            return block
        except json.JSONDecodeError:
            pass
    return None


def contains_completion_indicators(text):
    """Check if text contains clear completion indicators."""
    text_lower = text.lower().strip()

    # Look for explicit completion words
    completion_words = ['done', 'success', 'successful', 'completed', 'finished', 'complete']
    for word in completion_words:
        if word in text_lower:
            return True

    # Look for status patterns
    if '"status"' in text_lower and ('"done"' in text_lower or '"success"' in text_lower):
        return True

    # Look for result patterns
    if '"result"' in text_lower and len(text.strip()) > 20:  # Has some content
        return True

    return False


def extract_lenient_json(text):
    """Extract JSON from text with lenient parsing for malformed JSON."""
    # First try strict JSON extraction
    strict_json = extract_json(text)
    if strict_json:
        return strict_json, "strict"

    # Check if text contains completion indicators
    has_completion = contains_completion_indicators(text)
    if not has_completion:
        return None, "no_completion_indicators"

    # Try to fix common JSON issues
    fixed_text = text.strip()

    # Remove trailing commas before closing braces/brackets
    fixed_text = re.sub(r',(\s*[}\]])', r'\1', fixed_text)

    # Try to fix unquoted keys (simple cases)
    # This is tricky to do safely, so we'll be conservative

    # Try parsing the "fixed" text
    try:
        json.loads(fixed_text)
        return fixed_text, "fixed"
    except json.JSONDecodeError:
        pass

    # Last resort: look for JSON-like structure and extract key completion info
    # Check for basic structure with status/result
    if ('{' in text and '}' in text and
        ('status' in text.lower() or 'result' in text.lower())):

        # Create a minimal valid JSON structure
        mock_json = '{"status": "DONE", "result": "Task completed", "confidence": "medium", "validation": "Lenient parsing accepted completion indicators"}'
        return mock_json, "lenient_fallback"

    # If we have completion indicators but no valid structure, still accept it
    if has_completion:
        mock_json = '{"status": "DONE", "result": "Task completed", "confidence": "medium", "validation": "Lenient parsing accepted completion indicators"}'
        return mock_json, "lenient_fallback"

    return None, "no_valid_structure"


def parse_lenient_verdict(text):
    """Parse verdict and reason from auditor response with lenient parsing."""
    # First try strict JSON parsing
    try:
        data = json.loads(text)
        verdict = data.get('verdict')
        if verdict:
            verdict = verdict.upper()  # Normalize to uppercase
        reason = data.get('reason', '')
        advice = data.get('advice', '')
        return verdict, reason, advice
    except json.JSONDecodeError:
        pass

    # Fall back to pattern matching for completion indicators
    text_lower = text.lower().strip()

    # Look for verdict patterns (quoted and unquoted keys)
    if 'verdict' in text_lower:
        # Extract verdict value - look for verdict: "DONE" or "verdict": "DONE"
        verdict_match = re.search(r'(?:"verdict"|\bverdict\b)\s*:\s*"([^"]*)"', text, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            if verdict in ['DONE', 'REITERATE']:
                # Try to extract reason (quoted and unquoted keys)
                reason_match = re.search(r'(?:"reason"|\breason\b)\s*:\s*"([^"]*)"', text, re.IGNORECASE)
                reason = reason_match.group(1) if reason_match else "Parsed from lenient verdict extraction"
                return verdict, reason, ''

    # Look for status patterns (user's specific suggestion)
    if '"status"' in text_lower:
        # Look for "status": "DONE" on the same line
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if '"status"' in line_lower and ('"done"' in line_lower or '"success"' in line_lower):
                # Check if DONE/success appears after status on the same line
                status_pos = line_lower.find('"status"')
                done_pos = line_lower.find('"done"', status_pos)
                success_pos = line_lower.find('"success"', status_pos)
                if done_pos > status_pos or success_pos > status_pos:
                    return "DONE", "Parsed from status completion indicator", ''

    # Look for plain completion indicators as fallback
    completion_indicators = ['done', 'success', 'successful', 'completed', 'finished']
    for indicator in completion_indicators:
        if indicator in text_lower:
            return "DONE", f"Parsed from completion indicator: {indicator}", ''

    # No clear verdict found
    return None, None, None


def parse_json_verdict(json_text):
    """Parse verdict and reason from auditor JSON response (backward compatibility)."""
    return parse_lenient_verdict(json_text)


def _process_executor_output(raw_output: str, executor_name: str = "executor", task_id: Optional[str] = None) -> Tuple[str, List[Any]]:
    """
    Process executor output through activity interpreter.

    Returns:
        Tuple of (filtered_output, activity_events)
    """
    try:
        interpreter = get_interpreter()

        # Extract activities from raw output
        activities = interpreter.interpret_activity(raw_output)

        # Emit activity events asynchronously (non-blocking)
        if activities:
            try:
                # Schedule emission of events without blocking
                asyncio.create_task(_emit_activities(activities, executor_name, task_id))
            except RuntimeError:
                # Not in async context, skip event emission
                log_debug("Not in async context, skipping activity event emission")

        # Get filtered output (without cost/token metadata)
        filtered_output = interpreter.get_filtered_output(raw_output)

        return filtered_output, activities
    except Exception as e:
        log_debug(f"Error processing executor output for activity visualization: {e}")
        # On error, return raw output with empty activities
        return raw_output, []


async def _emit_activities(activities: List[Any], executor_name: str, task_id: Optional[str]) -> None:
    """Emit executor activity events asynchronously."""
    try:
        for activity in activities:
            # Only emit non-sensitive activities
            if not activity.is_sensitive:
                await emit_executor_activity(
                    activity_type=activity.activity_type.value,
                    description=activity.description,
                    executor=executor_name,
                    task_id=task_id,
                    details=activity.details,
                    is_sensitive=activity.is_sensitive
                )
    except Exception as e:
        log_debug(f"Error emitting executor activities: {e}")


def call_executor(prompt, model, executor="claude", initial_timeout=300, max_timeout=3600, activity_interval=30):
    """
    Call executor (claude or cline) with streaming output and adaptive timeout.

    Attempts PTY-based streaming first for real-time output, falls back to buffered
    execution if PTY is unavailable or disabled.
    """
    try:
        log_debug(f"Calling {executor} with model: {model}")
        log_debug(f"Prompt length: {len(prompt)} chars")
        log_debug(f"Timeout config: initial={initial_timeout}s, max={max_timeout}s, activity_check={activity_interval}s")

        # Build command
        if executor == "cline":
            cmd = ['cline', '--yolo', '--no-interactive', '--output-format', 'json', '--oneshot', prompt]
        else:  # claude
            cmd = ['claude', '-p', '--output-format', 'stream-json', '--verbose']
            if model:
                cmd.extend(['--model', model])
            cmd.append('--dangerously-skip-permissions')
            cmd.append(prompt)  # Pass prompt as command-line argument for --print mode

        log_debug(f"Command: {' '.join(cmd)}")

        # Try PTY-based streaming first
        if SUPPORTS_PTY and not DISABLE_STREAMING:
            try:
                log_debug("Attempting PTY-based streaming execution...")
                stdout, stderr, exit_code = call_executor_pty(
                    cmd,
                    input_data=None,  # Prompt is now passed as command argument for Claude
                    timeout=initial_timeout
                )
                log_verbose(f"{executor} call completed (PTY), output length: {len(stdout)} chars")
                if stderr:
                    log_debug(f"{executor} stderr: {stderr}")

                # Process output through activity interpreter to filter sensitive data
                filtered_output, activities = _process_executor_output(stdout, executor, task_id=None)
                if activities:
                    log_debug(f"Extracted {len(activities)} activity events from executor output")
                return filtered_output
            except (OSError, subprocess.TimeoutExpired) as e:
                log_debug(f"PTY execution failed, falling back to buffered: {e}")
                # Fall through to buffered execution

        # Fallback: buffered execution via subprocess.run
        log_debug("Using buffered execution (non-PTY)")
        _check_test_mode_blocking()

        if executor == "cline":
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=initial_timeout
            )
        else:  # claude
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=initial_timeout
            )

        log_verbose(f"{executor} call completed (buffered), output length: {len(result.stdout)} chars")
        if result.stderr:
            log_debug(f"{executor} stderr: {result.stderr}")

        # Process output through activity interpreter to filter sensitive data
        filtered_output, activities = _process_executor_output(result.stdout, executor, task_id=None)
        if activities:
            log_debug(f"Extracted {len(activities)} activity events from executor output")
        return filtered_output

    except subprocess.TimeoutExpired:
        log_info(f"Initial timeout ({initial_timeout}s) exceeded, checking for activity...")
        return call_executor_adaptive(prompt, model, executor, max_timeout, activity_interval)

    except Exception as e:
        log_info(f"ERROR: {e}")
        return f"ERROR: {e}"



async def call_executor_async(prompt: str, model: Optional[str], executor: str = "claude",
                            initial_timeout: float = 300, max_timeout: float = 3600,
                            activity_interval: float = 30) -> str:
    """
    Async version of call_executor using OneshotTask for better process management.

    Args:
        prompt: The prompt to send to the executor
        model: Model name (ignored for cline executor)
        executor: Either 'claude' or 'cline'
        initial_timeout: Initial timeout before activity monitoring
        max_timeout: Maximum timeout with activity monitoring
        activity_interval: How often to check for activity

    Returns:
        The executor's output as a string
    """
    from .task import OneshotTask
    import shlex

    try:
        log_debug(f"Calling {executor} asynchronously with model: {model}")
        log_debug(f"Prompt length: {len(prompt)} chars")
        log_debug(f"Timeout config: initial={initial_timeout}s, max={max_timeout}s, activity_check={activity_interval}s")

        # Build command
        if executor == "cline":
            # Properly escape the prompt for shell execution
            cmd = f'cline --yolo --no-interactive --output-format json --oneshot {shlex.quote(prompt)}'
            log_debug(f"Command: {cmd}")
        else:  # claude
            # For claude, we need to handle stdin input
            # Only include --model if explicitly provided
            if model:
                cmd = f'claude -p --output-format stream-json --model {model} --dangerously-skip-permissions'
            else:
                cmd = f'claude -p --output-format stream-json --dangerously-skip-permissions'

        # Create task with appropriate timeouts
        # Use max_timeout as idle threshold since OneshotTask handles activity monitoring
        task = OneshotTask(
            command=cmd,
            idle_threshold=max_timeout,
            activity_check_interval=activity_interval,
        )

        # For claude, we need to handle stdin
        if executor != "cline":
            # This is more complex - we'd need to modify OneshotTask to handle stdin
            # For now, fall back to sync version
            log_debug("Falling back to sync executor for claude with stdin")
            return call_executor(prompt, model, executor, initial_timeout, max_timeout, activity_interval)

        # Run the task
        result = await task.run()

        if result.success:
            log_verbose(f"Async {executor} call completed, output length: {len(result.output)} chars")
            # Process output through activity interpreter to filter sensitive data
            filtered_output, activities = _process_executor_output(result.output, executor, task_id=None)
            if activities:
                log_debug(f"Extracted {len(activities)} activity events from async executor output")
            return filtered_output
        else:
            error_msg = result.error or f"Task failed with exit code {result.exit_code}"
            log_info(f"ERROR: Async {executor} call failed: {error_msg}")
            return f"ERROR: {error_msg}"

    except Exception as e:
        log_info(f"ERROR in async executor: {e}")
        return f"ERROR: {e}"


def call_executor_adaptive(prompt, model, executor, max_timeout, activity_interval):
    """
    Adaptive timeout with activity monitoring for long-running tasks.

    Uses PTY streaming where available, falls back to buffered execution
    with activity-based timeout extension.
    """
    import threading

    log_debug(f"Starting adaptive timeout monitoring (max: {max_timeout}s, check: {activity_interval}s)")

    # Build command
    if executor == "cline":
        cmd = ['cline', '--yolo', '--no-interactive', '--output-format', 'json', '--oneshot', prompt]
    else:
        cmd = ['claude', '-p', '--output-format', 'stream-json', '--verbose']
        if model:
            cmd.extend(['--model', model])
        cmd.append('--dangerously-skip-permissions')
        cmd.append(prompt)  # Pass prompt as command-line argument for --print mode

    log_debug(f"Starting monitored process: {' '.join(cmd)}")

    # Track activity
    last_activity_time = time.time()
    output_parts = []

    def monitor_activity_thread():
        nonlocal last_activity_time
        start_time = time.time()

        while time.time() - start_time < max_timeout:
            time.sleep(activity_interval)

            # Check if we have new output (simplified activity detection)
            current_output_len = len(''.join(output_parts))
            if current_output_len > 0:
                last_activity_time = time.time()
                log_verbose(f"Activity detected at {time.time() - start_time:.1f}s (output: {current_output_len} bytes)")

            # If no activity for too long, allow timeout
            if time.time() - last_activity_time > activity_interval * 2:
                log_info(f"No activity for {activity_interval * 2}s, allowing timeout")
                return False

        return True

    try:
        # Try PTY-based streaming first if available
        if SUPPORTS_PTY and not DISABLE_STREAMING:
            try:
                log_debug("Attempting PTY-based adaptive streaming...")

                # Start activity monitoring thread
                monitor_thread = threading.Thread(target=monitor_activity_thread, daemon=True)
                monitor_thread.start()

                stdout, stderr, exit_code = call_executor_pty(
                    cmd,
                    input_data=None,  # Prompt is now passed as command argument for Claude
                    timeout=max_timeout
                )
                output_parts.append(stdout)
                log_verbose(f"Adaptive {executor} call completed (PTY), output length: {len(stdout)} chars")
                if stderr:
                    log_debug(f"{executor} stderr: {stderr}")
                # Process output through activity interpreter to filter sensitive data
                filtered_output, activities = _process_executor_output(stdout, executor, task_id=None)
                if activities:
                    log_debug(f"Extracted {len(activities)} activity events from adaptive PTY output")
                return filtered_output
            except (OSError, subprocess.TimeoutExpired) as e:
                log_debug(f"PTY adaptive execution failed, falling back to buffered: {e}")
                # Fall through to buffered execution

        # Fallback: buffered execution via subprocess.run with activity monitoring
        log_debug("Using buffered adaptive execution (non-PTY)")

        # Start activity monitor in background
        monitor_thread = threading.Thread(target=monitor_activity_thread, daemon=True)
        monitor_thread.start()

        _check_test_mode_blocking()

        if executor == "cline":
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=max_timeout
            )
        else:
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=max_timeout
            )

        output_parts.append(result.stdout)
        log_verbose(f"Adaptive {executor} call completed (buffered), output length: {len(result.stdout)} chars")

        if result.stderr:
            log_debug(f"{executor} stderr: {result.stderr}")

        # Process output through activity interpreter to filter sensitive data
        filtered_output, activities = _process_executor_output(result.stdout, executor, task_id=None)
        if activities:
            log_debug(f"Extracted {len(activities)} activity events from adaptive buffered output")
        return filtered_output

    except subprocess.TimeoutExpired:
        log_info(f"ERROR: {executor} call timed out after {max_timeout}s (max timeout reached)")
        return f"ERROR: {executor} call timed out after {max_timeout}s (max timeout reached)"
    except Exception as e:
        log_info(f"ERROR in adaptive timeout: {e}")
        return f"ERROR: {e}"



def find_latest_session(sessions_dir):
    """Find the latest session file."""
    # Support both old (session_*.md) and new (oneshot_*.json) formats
    session_files = sorted(
        list(Path(sessions_dir).glob(f"session_*.md")) +
        list(Path(sessions_dir).glob(f"*oneshot*.json")),
        key=lambda p: p.name,
        reverse=True
    )
    return session_files[0] if session_files else None


def read_session_context(session_file):
    """Read and parse existing session to understand context."""
    try:
        session_path = Path(session_file)
        with open(session_path, 'r') as f:
            content = f.read()

        # If JSON format, extract iterations text
        if session_path.suffix == '.json':
            try:
                data = json.loads(content)
                # Reconstruct text from iterations for context
                context_parts = []
                for iteration in data.get('iterations', []):
                    if 'worker_output' in iteration:
                        context_parts.append(f"Worker: {iteration['worker_output']}")
                    if 'auditor_output' in iteration:
                        context_parts.append(f"Auditor: {iteration['auditor_output']}")
                return '\n'.join(context_parts) if context_parts else content
            except json.JSONDecodeError:
                return content

        return content
    except Exception as e:
        print(f"Error reading session: {e}")
        return None


def strip_ansi(text):
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B\[([0-9]{1,3}(;[0-9]{1,2})?)?[mGK]')
    return ansi_escape.sub('', text)


# ============================================================================
# MAIN ONESHOT LOGIC
# ============================================================================


def run_oneshot(prompt, worker_provider, auditor_provider, max_iterations, resume=False, session_file=None, session_log=None, keep_log=False, initial_timeout=300, max_timeout=3600, activity_interval=30, worker_prompt_header="oneshot execution", auditor_prompt_header="oneshot auditor"):
    """Run the oneshot task with worker and auditor loop using provider objects."""
    from .providers import Provider

    log_info(f"Starting oneshot with worker provider: {worker_provider.config.provider_type}, auditor provider: {auditor_provider.config.provider_type}")
    log_debug(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")

    # Determine session file - use markdown for custom session logs, JSON for auto-generated
    auto_generated_log = False
    use_markdown_logging = False

    if session_log:
        log_file = Path(session_log)
        # Check if it's a markdown file (custom session log)
        if log_file.suffix.lower() == '.md':
            use_markdown_logging = True
        if log_file.exists():
            session_context = read_session_context(log_file)
            iteration = count_iterations(log_file) + 1
            print(f"📂 Resuming session: {log_file}")
            print(f"   Previous iterations: {iteration - 1}")
            log_verbose(f"Session context length: {len(session_context) if session_context else 0} chars")
            mode = 'a'
        else:
            session_context = None
            iteration = 1
            mode = 'w'
            if use_markdown_logging:
                log_info(f"Creating new markdown session: {log_file.name}")
                with open(log_file, mode) as f:
                    f.write(f"# Oneshot Session Log - {datetime.now()}\n\n")
            else:
                log_info(f"Creating new JSON session: {log_file.name}")
                # Initialize JSON session log structure for custom JSON logs
                session_data = {
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "prompt": prompt,
                        "worker_provider": worker_provider.config.provider_type,
                        "worker_executor": getattr(worker_provider.config, 'executor', None),
                        "worker_model": worker_provider.config.model,
                        "auditor_provider": auditor_provider.config.provider_type,
                        "auditor_executor": getattr(auditor_provider.config, 'executor', None),
                        "auditor_model": auditor_provider.config.model,
                        "max_iterations": max_iterations,
                        "working_directory": str(Path.cwd())
                    },
                    "iterations": []
                }
                with open(log_file, 'w') as f:
                    json.dump(session_data, f, indent=2)
    elif resume and session_file:
        log_file = session_file
        session_context = read_session_context(log_file)
        iteration = count_iterations(log_file) + 1
        print(f"📂 Resuming session: {log_file}")
        print(f"   Previous iterations: {iteration - 1}")
        log_verbose(f"Session context length: {len(session_context) if session_context else 0} chars")
        # Append to existing log
        mode = 'a'
        # Check if it's markdown based on content or extension
        if log_file.suffix.lower() == '.md':
            use_markdown_logging = True
    else:
        auto_generated_log = True
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = SESSION_DIR / f"{timestamp}_oneshot.json"
        session_context = None
        iteration = 1
        mode = 'w'
        log_info(f"Creating new session: {log_file.name}")
        log_verbose(f"Session directory: {SESSION_DIR}")

        # Initialize JSON session log structure
        session_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "worker_provider": worker_provider.config.provider_type,
                "worker_executor": getattr(worker_provider.config, 'executor', None),
                "worker_model": worker_provider.config.model,
                "auditor_provider": auditor_provider.config.provider_type,
                "auditor_executor": getattr(auditor_provider.config, 'executor', None),
                "auditor_model": auditor_provider.config.model,
                "max_iterations": max_iterations,
                "working_directory": str(Path.cwd())
            },
            "iterations": []
        }
        with open(log_file, 'w') as f:
            json.dump(session_data, f, indent=2)

    while iteration <= max_iterations:
        print(f"\n--- 🤖 Worker: Iteration {iteration} ---")
        log_info(f"Iteration {iteration}/{max_iterations}")

        # 1. Execute the Worker
        log_verbose(f"Building worker prompt (header + task)")
        full_prompt = get_worker_prompt(worker_prompt_header) + "\n\n" + prompt
        log_debug(f"Full prompt length: {len(full_prompt)} chars")
        dump_buffer("Worker Prompt", full_prompt, max_lines=10)

        log_verbose(f"Calling worker provider")
        worker_output = worker_provider.generate(full_prompt)
        dump_buffer("Worker Output", worker_output)
        print(worker_output)

        # Log worker output to session file
        log_verbose("Logging worker output to session file")
        if use_markdown_logging:
            # Append to markdown file
            with open(log_file, 'a') as f:
                f.write(f"\n--- 🤖 Worker: Iteration {iteration} ---\n")
                f.write(strip_ansi(worker_output) + "\n")
            session_data = None  # Not used for markdown
        else:
            # Use JSON format
            with open(log_file, 'r') as f:
                session_data = json.load(f)

            iteration_data = {"iteration": iteration, "worker_output": strip_ansi(worker_output)}
            session_data["iterations"].append(iteration_data)

            with open(log_file, 'w') as f:
                json.dump(session_data, f, indent=2)

        # 2. Summary Stats
        if use_markdown_logging:
            iteration_count = iteration
        else:
            iteration_count = len(session_data.get("iterations", []))
        print(f"Log Size: {iteration_count} iteration(s).")
        print("Last worker output:")
        print('\n'.join(worker_output.split('\n')[-3:]))
        log_debug(f"Session iterations: {iteration_count}")

        # 3. Success Auditor Step
        print("\n--- ⚖️ Auditor: Checking Progress ---")
        log_verbose("Extracting JSON from worker output (lenient parsing)")

        # Extract JSON from worker output using lenient parsing
        worker_json, extraction_method = extract_lenient_json(worker_output)
        log_info(f"JSON extraction method: {extraction_method}")
        dump_buffer("Extracted Worker JSON", worker_json or "NO JSON FOUND", max_lines=15)

        if not worker_json:
            print(f"❌ No acceptable response found in worker output (method: {extraction_method})")
            print("Worker said:", worker_output.split('\n')[:5])
            log_info(f"No acceptable response extracted (method: {extraction_method}), skipping auditor")
            iteration += 1
            time.sleep(ITERATION_SLEEP)
            continue

        # Real Auditor Call
        log_verbose(f"Preparing auditor prompt (extraction method: {extraction_method})")
        if extraction_method == "strict":
            audit_input = f"Original Task: {prompt}\n\nEvaluate this valid JSON response:\n\n{worker_json}"
        else:
            audit_input = f"Original Task: {prompt}\n\nEvaluate this response (parsed with {extraction_method} method):\n\n{worker_output}\n\nParsed as: {worker_json}"
        full_auditor_prompt = get_auditor_prompt(auditor_prompt_header) + "\n\n" + audit_input
        log_debug(f"Full auditor prompt length: {len(full_auditor_prompt)} chars")

        log_verbose(f"Calling auditor provider")
        audit_response = auditor_provider.generate(full_auditor_prompt)
        dump_buffer("Auditor Response", audit_response)

        # Log auditor response to session file
        log_verbose("Logging auditor response to session file")
        if use_markdown_logging:
            # Append to markdown file
            with open(log_file, 'a') as f:
                f.write(f"\n--- ⚖️ Auditor: Iteration {iteration} ---\n")
                f.write(strip_ansi(audit_response) + "\n")
        else:
            # Use JSON format
            with open(log_file, 'r') as f:
                session_data = json.load(f)

            # Update the last iteration with auditor output
            if session_data["iterations"]:
                session_data["iterations"][-1]["auditor_output"] = strip_ansi(audit_response)

            with open(log_file, 'w') as f:
                json.dump(session_data, f, indent=2)

        # Extract verdict from auditor response using lenient parsing
        log_verbose("Extracting verdict from auditor response (lenient parsing)")
        verdict, reason, advice = parse_lenient_verdict(audit_response)
        log_debug(f"Parsed verdict: {verdict}, reason: {reason}, advice: {advice}")

        # Also try to extract JSON for backward compatibility and logging
        auditor_json = extract_json(audit_response)
        dump_buffer("Extracted Auditor JSON", auditor_json or "NO JSON FOUND", max_lines=10)

        if not verdict:
            log_info("Could not extract verdict from auditor response")

        print(f"Auditor verdict: {verdict}")
        if reason:
            print(f"Reason: {reason}")

        # Handle verdict
        if verdict and verdict.upper() == "DONE":
            print("✅ Auditor confirmed: DONE.")
            log_info(f"Task completed successfully in {iteration} iteration(s)")

            # Update session file with completion status
            if not use_markdown_logging:
                with open(log_file, 'r') as f:
                    session_data = json.load(f)
                session_data["metadata"]["status"] = "completed"
                session_data["metadata"]["completion_iteration"] = iteration
                session_data["metadata"]["end_time"] = datetime.now().isoformat()
                with open(log_file, 'w') as f:
                    json.dump(session_data, f, indent=2)
            else:
                # Append completion status to markdown
                with open(log_file, 'a') as f:
                    f.write(f"\n--- ✅ Task Completed in Iteration {iteration} ---\n")

            # Clean up auto-generated session logs unless keep_log is True or session_log was specified
            if auto_generated_log and not keep_log:
                try:
                    log_file.unlink()
                    log_info(f"Cleaned up session log: {log_file}")
                except Exception as e:
                    log_info(f"Failed to clean up session log: {e}")

            return True

        elif verdict and verdict.upper() == "REITERATE":
            print("🔄 Auditor suggested: REITERATE")
            if reason:
                print(f"Issue: {reason}")
                prompt = f"{prompt}\n\n[Iteration {iteration} feedback: {reason}]"

        else:
            if TEST_MODE:
                raise ValueError(f"Auditor verdict unclear: '{verdict}'")
            print(f"❓ Auditor verdict unclear: '{verdict}'")
            if auditor_json:
                print(f"Auditor JSON: {auditor_json}")
            print("Continuing anyway...")

        iteration += 1
        time.sleep(ITERATION_SLEEP)

    msg = f"Max iterations ({max_iterations}) reached without completion. Session log retained at: {log_file}"
    print(f"\n❌ {msg}")
    log_info(msg)

    # Always retain session logs on failure (don't clean up)
    # Note: keep_log parameter only affects successful completion cleanup

    return False


async def run_oneshot_async(prompt, worker_provider, auditor_provider, max_iterations,
                          resume=False, session_file=None,
                          session_log=None, keep_log=False, initial_timeout=300,
                          max_timeout=3600, activity_interval=30):
    """
    Async version of run_oneshot using provider objects.
    """
    from .orchestrator import AsyncOrchestrator
    from .providers import Provider

    log_info(f"Starting async oneshot with worker provider: {worker_provider.config.provider_type}, auditor provider: {auditor_provider.config.provider_type}")
    log_debug(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")

    # Determine session file
    auto_generated_log = False
    if session_log:
        log_file = Path(session_log)
        if log_file.exists():
            session_context = read_session_context(log_file)
            iteration = count_iterations(log_file) + 1
            print(f"📂 Resuming session: {log_file}")
            print(f"   Previous iterations: {iteration - 1}")
            log_verbose(f"Session context length: {len(session_context) if session_context else 0} chars")
            mode = 'a'
        else:
            session_context = None
            iteration = 1
            mode = 'w'
            log_info(f"Creating new session: {log_file.name}")
            with open(log_file, mode) as f:
                f.write(f"# Oneshot Session Log - {datetime.now()}\n\n")
    elif resume and session_file:
        log_file = session_file
        session_context = read_session_context(log_file)
        iteration = count_iterations(log_file) + 1
        print(f"📂 Resuming session: {log_file}")
        print(f"   Previous iterations: {iteration - 1}")
        log_verbose(f"Session context length: {len(session_context) if session_context else 0} chars")
        mode = 'a'
    else:
        auto_generated_log = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = SESSION_DIR / f"session_{timestamp}.md"
        session_context = None
        iteration = 1
        mode = 'w'
        log_info(f"Creating new session: {log_file.name}")
        log_verbose(f"Session directory: {SESSION_DIR}")
        with open(log_file, mode) as f:
            f.write(f"# Oneshot Session Log - {datetime.now()}\n\n")

    # Create orchestrator for concurrent task execution
    orchestrator = AsyncOrchestrator(
        max_concurrent=2,  # Allow concurrent worker and auditor calls
        global_idle_threshold=max_timeout,
        heartbeat_interval=activity_interval,
    )

    try:
        while iteration <= max_iterations:
            print(f"\n--- 🤖 Worker: Iteration {iteration} ---")
            log_info(f"Iteration {iteration}/{max_iterations}")

            # 1. Execute the Worker asynchronously
            log_verbose(f"Building worker prompt (prefix + task)")
            full_prompt = WORKER_PREFIX + prompt
            log_debug(f"Full prompt length: {len(full_prompt)} chars")
            dump_buffer("Worker Prompt", full_prompt, max_lines=10)

            log_verbose(f"Calling worker provider asynchronously")

            # Use async provider
            worker_output = await worker_provider.generate_async(full_prompt)
            dump_buffer("Worker Output", worker_output)
            print(worker_output)

            # Log worker output
            log_verbose("Logging worker output to session file")
            with open(log_file, 'a') as f:
                f.write(f"\n## Iteration {iteration} - Worker Output\n\n")
                f.write(strip_ansi(worker_output) + "\n")

            # 2. Summary Stats
            with open(log_file, 'r') as f:
                log_lines = len(f.readlines())
            print(f"Log Size: {log_lines} lines.")
            print("Last worker output:")
            print('\n'.join(worker_output.split('\n')[-3:]))
            log_debug(f"Session file size: {log_lines} lines")

            # 3. Success Auditor Step
            print("\n--- ⚖️ Auditor: Checking Progress ---")
            log_verbose("Extracting JSON from worker output (lenient parsing)")

            # Extract JSON from worker output using lenient parsing
            worker_json, extraction_method = extract_lenient_json(worker_output)
            log_info(f"JSON extraction method: {extraction_method}")
            dump_buffer("Extracted Worker JSON", worker_json or "NO JSON FOUND", max_lines=15)

            if not worker_json:
                print(f"❌ No acceptable response found in worker output (method: {extraction_method})")
                print("Worker said:", worker_output.split('\n')[:5])
                log_info(f"No acceptable response extracted (method: {extraction_method}), skipping auditor")
                iteration += 1
                await asyncio.sleep(ITERATION_SLEEP)
                continue

            # Real Auditor Call (async)
            log_verbose(f"Preparing auditor prompt (extraction method: {extraction_method})")
            if extraction_method == "strict":
                audit_input = f"Original Task: {prompt}\n\nEvaluate this valid JSON response:\n\n{worker_json}"
            else:
                audit_input = f"Original Task: {prompt}\n\nEvaluate this response (parsed with {extraction_method} method):\n\n{worker_output}\n\nParsed as: {worker_json}"
            full_auditor_prompt = AUDITOR_PROMPT + "\n\n" + audit_input
            log_debug(f"Full auditor prompt length: {len(full_auditor_prompt)} chars")

            log_verbose(f"Calling auditor provider asynchronously")
            audit_response = await auditor_provider.generate_async(full_auditor_prompt)
            dump_buffer("Auditor Response", audit_response)

            # Log auditor response
            log_verbose("Logging auditor response to session file")
            with open(log_file, 'a') as f:
                f.write(f"\n### Iteration {iteration} - Auditor Response\n\n")
                f.write(strip_ansi(audit_response) + "\n")

            # Extract verdict from auditor response using lenient parsing
            log_verbose("Extracting verdict from auditor response (lenient parsing)")
            verdict, reason, advice = parse_lenient_verdict(audit_response)
            log_debug(f"Parsed verdict: {verdict}, reason: {reason}, advice: {advice}")

            # Also try to extract JSON for backward compatibility and logging
            auditor_json = extract_json(audit_response)
            dump_buffer("Extracted Auditor JSON", auditor_json or "NO JSON FOUND", max_lines=10)

            if not verdict:
                log_info("Could not extract verdict from auditor response")

            print(f"Auditor verdict: {verdict}")
            if reason:
                print(f"Reason: {reason}")

            # Handle verdict
            if verdict and verdict.upper() == "DONE":
                print("✅ Auditor confirmed: DONE.")
                log_info(f"Task completed successfully in {iteration} iteration(s)")
                with open(log_file, 'a') as f:
                    f.write("\n✅ Task completed successfully!\n")

                # Clean up auto-generated session logs unless keep_log is True or session_log was specified
                if auto_generated_log and not keep_log:
                    try:
                        log_file.unlink()
                        log_info(f"Cleaned up session log: {log_file}")
                    except Exception as e:
                        log_info(f"Failed to clean up session log: {e}")

                return True

            elif verdict and verdict.upper() == "REITERATE":
                print("🔄 Auditor suggested: REITERATE")
                if reason:
                    print(f"Issue: {reason}")
                    prompt = f"{prompt}\n\n[Iteration {iteration} feedback: {reason}]"

            else:
                if TEST_MODE:
                    raise ValueError(f"Auditor verdict unclear: '{verdict}'")
                print(f"❓ Auditor verdict unclear: '{verdict}'")
                if auditor_json:
                    print(f"Auditor JSON: {auditor_json}")
                print("Continuing anyway...")

            iteration += 1
            await asyncio.sleep(ITERATION_SLEEP)

        msg = f"Max iterations ({max_iterations}) reached without completion. Session log retained at: {log_file}"
        print(f"\n❌ {msg}")
        log_info(msg)

        # Always retain session logs on failure (don't clean up)
        # Note: keep_log parameter only affects successful completion cleanup

        return False

    except Exception as e:
        log_info(f"Async oneshot error: {e}")
        return False


def count_iterations(log_file):
    """Count iterations in existing session."""
    try:
        with open(log_file, 'r') as f:
            content = f.read()
        return len(re.findall(r'^## Iteration \d+', content, re.MULTILINE))
    except:
        return 0


# ============================================================================
# BACKWARD COMPATIBILITY WRAPPER
# ============================================================================

def run_oneshot_legacy(prompt, worker_model, auditor_model, max_iterations, executor="claude",
                       resume=False, session_file=None, session_log=None, keep_log=False,
                       initial_timeout=300, max_timeout=3600, activity_interval=30,
                       worker_prompt_header="oneshot execution", auditor_prompt_header="oneshot auditor"):
    """
    Backward-compatible wrapper that accepts model strings and creates providers.

    This function maintains the old API signature while using the new provider system internally.
    """
    from .providers import ProviderConfig, create_provider

    # Create worker provider config
    worker_config = ProviderConfig(
        provider_type='executor',
        executor=executor,
        model=worker_model,
        timeout=initial_timeout
    )

    # Create auditor provider config
    auditor_config = ProviderConfig(
        provider_type='executor',
        executor=executor,
        model=auditor_model,
        timeout=initial_timeout
    )

    # Create provider instances
    worker_provider = create_provider(worker_config)
    auditor_provider = create_provider(auditor_config)

    # Set custom headers on providers if they support it
    if hasattr(worker_provider, 'set_worker_prompt_header'):
        worker_provider.set_worker_prompt_header(worker_prompt_header)
    if hasattr(auditor_provider, 'set_auditor_prompt_header'):
        auditor_provider.set_auditor_prompt_header(auditor_prompt_header)

    # Call the new provider-based run_oneshot
    return run_oneshot(
        prompt=prompt,
        worker_provider=worker_provider,
        auditor_provider=auditor_provider,
        max_iterations=max_iterations,
        resume=resume,
        session_file=session_file,
        session_log=session_log,
        keep_log=keep_log,
        initial_timeout=initial_timeout,
        max_timeout=max_timeout,
        activity_interval=activity_interval
    )


async def run_oneshot_async_legacy(prompt, worker_model, auditor_model, max_iterations, executor="claude",
                                   resume=False, session_file=None, session_log=None, keep_log=False,
                                   initial_timeout=300, max_timeout=3600, activity_interval=30):
    """
    Backward-compatible async wrapper that accepts model strings and creates providers.
    """
    from .providers import ProviderConfig, create_provider

    # Create worker provider config
    worker_config = ProviderConfig(
        provider_type='executor',
        executor=executor,
        model=worker_model,
        timeout=initial_timeout
    )

    # Create auditor provider config
    auditor_config = ProviderConfig(
        provider_type='executor',
        executor=executor,
        model=auditor_model,
        timeout=initial_timeout
    )

    # Create provider instances
    worker_provider = create_provider(worker_config)
    auditor_provider = create_provider(auditor_config)

    # Call the new provider-based run_oneshot_async
    return await run_oneshot_async(
        prompt=prompt,
        worker_provider=worker_provider,
        auditor_provider=auditor_provider,
        max_iterations=max_iterations,
        resume=resume,
        session_file=session_file,
        session_log=session_log,
        keep_log=keep_log,
        initial_timeout=initial_timeout,
        max_timeout=max_timeout,
        activity_interval=activity_interval
    )


# ============================================================================
# ARGUMENT PARSING & MAIN
# ============================================================================


def main():
    from .config import get_global_config

    # Load configuration
    config, config_error = get_global_config()
    if config_error:
        print(f"Warning: Configuration error: {config_error}", file=sys.stderr)

    parser = argparse.ArgumentParser(
        description='Oneshot - Autonomous task completion with auditor validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  oneshot 'What is the capital of Denmark?'
  oneshot --worker-model claude-3-5-sonnet-20241022 'Complex task'
  oneshot --worker-prompt-header "custom project" 'Task with custom header'
  oneshot --resume 'Continue working on this'
  oneshot --session-log my_task.md 'Task with custom logging'

Configuration:
  Create ~/.oneshot.json or .oneshotrc to set default values.
  Command-line options override configuration file settings.
        """
    )

    parser.add_argument(
        'prompt',
        help='The task/prompt to complete'
    )

    parser.add_argument(
        '--max-iterations',
        type=int,
        default=config['max_iterations'],
        help=f'Maximum iterations (default: {config["max_iterations"]})'
    )

    parser.add_argument(
        '--worker-model',
        default=config['worker_model'],
        help='Model for worker (defaults vary by executor)'
    )

    parser.add_argument(
        '--auditor-model',
        default=config['auditor_model'],
        help='Model for auditor (defaults vary by executor)'
    )

    parser.add_argument(
        '--worker-prompt-header',
        default=config['worker_prompt_header'],
        help=f'Custom header for worker prompts (default: "{config["worker_prompt_header"]}")'
    )

    parser.add_argument(
        '--auditor-prompt-header',
        default=config['auditor_prompt_header'],
        help=f'Custom header for auditor prompts (default: "{config["auditor_prompt_header"]}")'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume the latest existing session'
    )

    parser.add_argument(
        '--session',
        type=str,
        help='Specific session file to resume (implies --resume)'
    )

    parser.add_argument(
        '--session-log',
        type=str,
        help='Path to session log file (will append if exists, will not auto-delete)'
    )

    parser.add_argument(
        '--keep-log',
        action='store_true',
        help='Keep the session log file after completion'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output with buffer dumps'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug output with detailed internals'
    )

    parser.add_argument(
        '--executor',
        default=config['executor'],
        choices=['claude', 'cline', 'aider', 'gemini'],
        help=f'Which executor to use: claude, cline, aider, or gemini (default: {config["executor"]})'
    )

    parser.add_argument(
        '--initial-timeout',
        type=int,
        default=config['initial_timeout'],
        help=f'Initial timeout in seconds before activity monitoring (default: {config["initial_timeout"]})'
    )

    parser.add_argument(
        '--max-timeout',
        type=int,
        default=config['max_timeout'],
        help=f'Maximum timeout in seconds with activity monitoring (default: {config["max_timeout"]})'
    )

    parser.add_argument(
        '--activity-interval',
        type=int,
        default=config['activity_interval'],
        help=f'Activity check interval in seconds (default: {config["activity_interval"]})'
    )

    parser.add_argument(
        '--logs-dir',
        type=str,
        default=None,
        help='Directory to store session logs (default: current directory)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to custom configuration file (overrides default locations)'
    )

    args = parser.parse_args()

    # Set default models based on executor
    if args.executor == "cline":
        if args.worker_model or args.auditor_model:
            print("Model selection is not supported for the cline executor. Please configure the model in the cline tool.", file=sys.stderr)
            sys.exit(1)
        args.worker_model = None
        args.auditor_model = None
    elif args.executor == "aider":
        if args.worker_model or args.auditor_model:
            print("Model selection is not supported for the aider executor. Please configure the model in the aider tool.", file=sys.stderr)
            sys.exit(1)
        args.worker_model = None
        args.auditor_model = None
    elif args.executor == "gemini":
        if args.worker_model or args.auditor_model:
            print("Model selection is not supported for the gemini executor. Please configure the model in the gemini CLI.", file=sys.stderr)
            sys.exit(1)
        args.worker_model = None
        args.auditor_model = None
    else:  # claude
        default_worker = "claude-3-5-haiku-20241022"
        default_auditor = "claude-3-5-haiku-20241022"

        if args.worker_model is None:
            args.worker_model = default_worker
        if args.auditor_model is None:
            args.auditor_model = default_auditor

    # Set global verbosity level
    global VERBOSITY
    if args.debug:
        VERBOSITY = 2
        log_debug("Debug mode enabled")
    elif args.verbose:
        VERBOSITY = 1
        log_verbose("Verbose mode enabled")
    else:
        VERBOSITY = 0

    # Validate prompt
    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    # Configure logs directory
    global SESSION_DIR
    if args.logs_dir:
        logs_dir = Path(args.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        SESSION_DIR = logs_dir
        log_verbose(f"Using logs directory: {SESSION_DIR}")
    else:
        # Ensure SESSION_DIR exists
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    # Handle resume
    resume = args.resume or args.session is not None
    session_file = None

    if resume:
        if args.session:
            session_file = Path(args.session)
            if not session_file.exists():
                print(f"❌ Session file not found: {session_file}")
                sys.exit(1)
        else:
            session_file = find_latest_session(SESSION_DIR)
            if not session_file:
                print("❌ No existing session found to resume")
                sys.exit(1)

    # Run oneshot using legacy wrapper for backward compatibility
    success = run_oneshot_legacy(
        prompt=args.prompt,
        worker_model=args.worker_model,
        auditor_model=args.auditor_model,
        max_iterations=args.max_iterations,
        executor=args.executor,
        resume=resume,
        session_file=session_file,
        session_log=args.session_log,
        keep_log=args.keep_log,
        initial_timeout=args.initial_timeout,
        max_timeout=args.max_timeout,
        activity_interval=args.activity_interval,
        worker_prompt_header=args.worker_prompt_header,
        auditor_prompt_header=args.auditor_prompt_header
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()