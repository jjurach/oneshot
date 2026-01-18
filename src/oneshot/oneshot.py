#!/usr/bin/env python3
"""
Oneshot - Autonomous task completion with auditor validation
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

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
# CONFIGURATION - Edit these defaults
# ============================================================================

DEFAULT_WORKER_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_AUDITOR_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_MAX_ITERATIONS = 5
SESSION_DIR = Path.cwd()
SESSION_LOG_NAME = "session_summary.md"
ITERATION_SLEEP = 2

WORKER_PREFIX = """
IMPORTANT: Provide your final answer in valid JSON format when possible. Include completion indicators like "DONE", "success", or "status" even in non-JSON responses.

PREFERRED FORMAT (valid JSON):
{
  "status": "DONE",
  "result": "<your answer/output here>",
  "confidence": "<high/medium/low>",
  "validation": "<how you verified this answer - sources, output shown, reasoning explained>",
  "execution_proof": "<what you actually did - optional if no external tools were used>"
}

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

AUDITOR_PROMPT = """
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
- Valid JSON: {"status": "DONE", "result": "Task completed"}
- Malformed JSON: {status: "success", result: "Answer here"}
- Plain text: "Task completed successfully. The answer is..."
- Mixed: "DONE\n{\"result\": \"Answer\", \"status\": \"complete\"}"

Use the original task context to provide helpful feedback if reiteration is needed.

PREFERRED FORMAT (JSON):
{
  "verdict": "DONE",
  "reason": "<brief explanation>"
}

ALTERNATIVE: If JSON is difficult, include clear completion indicators:
- "status": "DONE" or "verdict": "DONE" patterns
- Words like "DONE", "success", "completed", "finished"
- Clear indication that the task is complete

The system will accept both valid JSON and responses with clear completion indicators.
"""

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


def call_executor(prompt, model, executor="claude", initial_timeout=300, max_timeout=3600, activity_interval=30):


    """Call executor (claude or cline) with adaptive timeout and activity monitoring."""


    try:


        log_debug(f"Calling {executor} with model: {model}")


        log_debug(f"Prompt length: {len(prompt)} chars")


        log_debug(f"Timeout config: initial={initial_timeout}s, max={max_timeout}s, activity_check={activity_interval}s")





        if executor == "cline":


            # For cline, the model is configured in the tool itself


            cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', prompt]


            log_debug(f"Command: {' '.join(cmd)}")

            _check_test_mode_blocking()
            result = subprocess.run(


                cmd,


                text=True,


                capture_output=True,


                timeout=initial_timeout


            )


        else:  # default to claude


            cmd = ['claude', '-p', '--model', model, '--dangerously-skip-permissions']


            log_debug(f"Command: {' '.join(cmd)}")

            _check_test_mode_blocking()
            result = subprocess.run(


                cmd,


                input=prompt,


                text=True,


                capture_output=True,


                timeout=initial_timeout


            )





        log_verbose(f"{executor} call completed, output length: {len(result.stdout)} chars")


        if result.stderr:


            log_debug(f"{executor} stderr: {result.stderr}")


        return result.stdout


    except subprocess.TimeoutExpired:


        log_info(f"Initial timeout ({initial_timeout}s) exceeded, checking for activity...")


        # Try adaptive timeout with activity monitoring


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
            cmd = f'cline --yolo --no-interactive --oneshot {shlex.quote(prompt)}'
            log_debug(f"Command: {cmd}")
        else:  # claude
            # For claude, we need to handle stdin input
            cmd = f'claude -p --model {model} --dangerously-skip-permissions'

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
            return result.output
        else:
            error_msg = result.error or f"Task failed with exit code {result.exit_code}"
            log_info(f"ERROR: Async {executor} call failed: {error_msg}")
            return f"ERROR: {error_msg}"

    except Exception as e:
        log_info(f"ERROR in async executor: {e}")
        return f"ERROR: {e}"


def call_executor_adaptive(prompt, model, executor, max_timeout, activity_interval):
    """Adaptive timeout with activity monitoring for long-running tasks."""
    import threading
    import time

    log_debug(f"Starting adaptive timeout monitoring (max: {max_timeout}s, check: {activity_interval}s)")

    # Track activity
    last_activity_time = time.time()
    activity_detected = False
    output_buffer = []
    error_buffer = []

    def monitor_activity():
        nonlocal last_activity_time, activity_detected
        start_time = time.time()

        while time.time() - start_time < max_timeout:
            time.sleep(activity_interval)

            # Check if we have new output (simplified activity detection)
            current_output_len = len(''.join(output_buffer))
            if current_output_len > 0:
                activity_detected = True
                last_activity_time = time.time()
                log_verbose(f"Activity detected at {time.time() - start_time:.1f}s")

            # If no activity for too long, timeout
            if time.time() - last_activity_time > activity_interval * 2:
                log_info(f"No activity for {activity_interval * 2}s, timing out")
                return False

        return True

    try:
        if executor == "cline":
            cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', prompt]
        else:
            cmd = ['claude', '-p', '--model', model, '--dangerously-skip-permissions']

        log_debug(f"Starting monitored process: {' '.join(cmd)}")

        # Start activity monitor in background
        monitor_thread = threading.Thread(target=monitor_activity, daemon=True)
        monitor_thread.start()

        # Run the process with extended timeout
        if executor == "cline":
            _check_test_mode_blocking()
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=max_timeout
            )
        else:
            _check_test_mode_blocking()
            result = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=max_timeout
            )

        log_verbose(f"Adaptive {executor} call completed, output length: {len(result.stdout)} chars")

        if result.stderr:
            log_debug(f"{executor} stderr: {result.stderr}")

        return result.stdout

    except subprocess.TimeoutExpired:
        log_info(f"ERROR: {executor} call timed out after {max_timeout}s (max timeout reached)")
        return f"ERROR: {executor} call timed out after {max_timeout}s (max timeout reached)"
    except Exception as e:
        log_info(f"ERROR in adaptive timeout: {e}")
        return f"ERROR: {e}"


def find_latest_session(sessions_dir):
    """Find the latest session file."""
    session_files = sorted(
        Path(sessions_dir).glob(f"session_*.md"),
        key=lambda p: p.name,
        reverse=True
    )
    return session_files[0] if session_files else None


def read_session_context(session_file):
    """Read and parse existing session to understand context."""
    try:
        with open(session_file, 'r') as f:
            content = f.read()
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


def run_oneshot(prompt, worker_provider, auditor_provider, max_iterations, resume=False, session_file=None, session_log=None, keep_log=False, initial_timeout=300, max_timeout=3600, activity_interval=30):
    """Run the oneshot task with worker and auditor loop using provider objects."""
    from .providers import Provider

    log_info(f"Starting oneshot with worker provider: {worker_provider.config.provider_type}, auditor provider: {auditor_provider.config.provider_type}")
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
        # Append to existing log
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

    while iteration <= max_iterations:
        print(f"\n--- 🤖 Worker: Iteration {iteration} ---")
        log_info(f"Iteration {iteration}/{max_iterations}")

        # 1. Execute the Worker
        log_verbose(f"Building worker prompt (prefix + task)")
        full_prompt = WORKER_PREFIX + prompt
        log_debug(f"Full prompt length: {len(full_prompt)} chars")
        dump_buffer("Worker Prompt", full_prompt, max_lines=10)

        log_verbose(f"Calling worker provider")
        worker_output = worker_provider.generate(full_prompt)
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
            time.sleep(ITERATION_SLEEP)
            continue

        # Real Auditor Call
        log_verbose(f"Preparing auditor prompt (extraction method: {extraction_method})")
        if extraction_method == "strict":
            audit_input = f"Original Task: {prompt}\n\nEvaluate this valid JSON response:\n\n{worker_json}"
        else:
            audit_input = f"Original Task: {prompt}\n\nEvaluate this response (parsed with {extraction_method} method):\n\n{worker_output}\n\nParsed as: {worker_json}"
        full_auditor_prompt = AUDITOR_PROMPT + "\n\n" + audit_input
        log_debug(f"Full auditor prompt length: {len(full_auditor_prompt)} chars")

        log_verbose(f"Calling auditor provider")
        audit_response = auditor_provider.generate(full_auditor_prompt)
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
                       initial_timeout=300, max_timeout=3600, activity_interval=30):
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
    parser = argparse.ArgumentParser(
        description='Oneshot - Autonomous task completion with auditor validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  oneshot 'What is the capital of Denmark?'
  oneshot --worker-model claude-3-5-sonnet-20241022 'Complex task'
  oneshot --resume 'Continue working on this'
  oneshot --session-log my_task.md 'Task with custom logging'
        """
    )

    parser.add_argument(
        'prompt',
        help='The task/prompt to complete'
    )

    parser.add_argument(
        '--max-iterations',
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f'Maximum iterations (default: {DEFAULT_MAX_ITERATIONS})'
    )

    parser.add_argument(
        '--worker-model',
        help='Model for worker (defaults vary by executor)'
    )

    parser.add_argument(
        '--auditor-model',
        help='Model for auditor (defaults vary by executor)'
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
        default='cline',
        choices=['claude', 'cline'],
        help='Which executor to use: claude or cline (default: cline)'
    )

    parser.add_argument(
        '--initial-timeout',
        type=int,
        default=300,
        help='Initial timeout in seconds before activity monitoring (default: 300)'
    )

    parser.add_argument(
        '--max-timeout',
        type=int,
        default=3600,
        help='Maximum timeout in seconds with activity monitoring (default: 3600)'
    )

    parser.add_argument(
        '--activity-interval',
        type=int,
        default=30,
        help='Activity check interval in seconds (default: 30)'
    )

    args = parser.parse_args()

    # Set default models based on executor
    if args.executor == "cline":
        if args.worker_model or args.auditor_model:
            print("Model selection is not supported for the cline executor. Please configure the model in the cline tool.", file=sys.stderr)
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
        activity_interval=args.activity_interval
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()