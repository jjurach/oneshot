#!/usr/bin/env python3
"""
Oneshot - Autonomous task completion with auditor validation
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

VERBOSITY = 0  # 0=default, 1=verbose, 2=debug

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
CRITICAL: Output ONLY valid JSON with NOTHING else. No preamble, no explanation, no markdown.

You must provide your final answer as valid JSON with this exact structure:
{
  "status": "DONE",
  "result": "<your answer/output here>",
  "confidence": "<high/medium/low>",
  "validation": "<how you verified this answer - sources, output shown, reasoning explained>",
  "execution_proof": "<what you actually did - optional if no external tools were used>"
}

IMPORTANT GUIDANCE:
- "result" should be your final answer
- "validation" should describe HOW you got it (tools used, sources checked, actual output if execution)
- "execution_proof" is optional - only include if you used external tools, commands, or computations
- For knowledge-based answers: brief validation is sufficient
- For coding tasks: describe the changes made
- Be honest and specific - don't make up results
- Set "status" to "DONE" when you believe the task is completed according to the requirements

Complete this task:
"""

AUDITOR_PROMPT = """
You are a Success Auditor. Evaluate the worker's JSON response with TRUST by default.

The original task and project context should guide your evaluation of what "DONE" means. Be lenient and trust the worker's judgment unless there are clear, serious issues.

Only reject if there are REAL, significant issues:
1. Valid JSON structure? (reject if completely malformed)
2. Has "status": "DONE"? (reject if not)
3. Does the result seem reasonable for the task? (reject only if completely implausible)
4. Are validation details provided? (reject only if entirely missing and result is questionable)

TRUST the worker by default:
- Accept reasonable answers even if execution_proof is minimal or absent
- For coding tasks, trust the worker's assessment of completion
- Focus on whether the task appears addressed, not perfection
- Give the benefit of the doubt for subjective judgments

Examples of ACCEPTABLE responses:
- Code changes with description of what was modified
- Documentation improvements with summary of changes
- Knowledge answers with brief validation
- Any honest attempt that addresses the core task

Use the original task context to provide helpful feedback if reiteration is needed.

Respond ONLY with this JSON (no other text):
{
  "verdict": "DONE",
  "reason": "<brief explanation>"
}

Or if there are real issues:
{
  "verdict": "REITERATE",
  "reason": "<specific, actionable feedback to improve>"
}
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
            current_json = [line]
            brace_count = line.count('{') - line.count('}')
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


def parse_json_verdict(json_text):
    """Parse verdict and reason from auditor JSON response."""
    try:
        data = json.loads(json_text)
        return data.get('verdict'), data.get('reason'), data.get('advice', '')
    except json.JSONDecodeError:
        return None, None, None


def call_executor(prompt, model, executor="claude"):


    """Call executor (claude or cline) with a prompt."""


    try:


        log_debug(f"Calling {executor} with model: {model}")


        log_debug(f"Prompt length: {len(prompt)} chars")





        if executor == "cline":


            # For cline, the model is configured in the tool itself


            cmd = ['cline', '--yolo', '--no-interactive', '--oneshot', prompt]


            log_debug(f"Command: {' '.join(cmd)}")


            result = subprocess.run(


                cmd,


                text=True,


                capture_output=True,


                timeout=120


            )


        else:  # default to claude


            cmd = ['claude', '-p', '--model', model, '--dangerously-skip-permissions']


            log_debug(f"Command: {' '.join(cmd)}")


            result = subprocess.run(


                cmd,


                input=prompt,


                text=True,


                capture_output=True,


                timeout=120


            )





        log_verbose(f"{executor} call completed, output length: {len(result.stdout)} chars")


        if result.stderr:


            log_debug(f"{executor} stderr: {result.stderr}")


        return result.stdout


    except subprocess.TimeoutExpired:


        log_info(f"ERROR: {executor} call timed out")


        return f"ERROR: {executor} call timed out"


    except Exception as e:


        log_info(f"ERROR: {e}")


        return f"ERROR: {e}"


def find_latest_session(sessions_dir):
    """Find the latest session file."""
    session_files = sorted(
        sessions_dir.glob(f"session_*.md"),
        key=lambda p: p.stat().st_mtime,
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


def run_oneshot(prompt, worker_model, auditor_model, max_iterations, executor="claude", resume=False, session_file=None, session_log=None, keep_log=False):
    """Run the oneshot task with worker and auditor loop."""

    log_info(f"Starting oneshot: worker={worker_model}, auditor={auditor_model}, executor={executor}")
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

        log_verbose(f"Calling worker model: {worker_model}")
        worker_output = call_executor(full_prompt, worker_model, executor=executor)
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
        log_verbose("Extracting JSON from worker output")

        # Extract JSON from worker output
        worker_json = extract_json(worker_output)
        dump_buffer("Extracted Worker JSON", worker_json or "NO JSON FOUND", max_lines=15)

        if not worker_json:
            print("❌ No valid JSON found in worker output")
            print("Worker said:", worker_output.split('\n')[:5])
            log_info("No JSON extracted, skipping auditor")
            iteration += 1
            time.sleep(ITERATION_SLEEP)
            continue

        # Real Auditor Call
        log_verbose(f"Preparing auditor prompt")
        audit_input = f"Original Task: {prompt}\n\nEvaluate this JSON response:\n\n{worker_json}"
        full_auditor_prompt = AUDITOR_PROMPT + "\n\n" + audit_input
        log_debug(f"Full auditor prompt length: {len(full_auditor_prompt)} chars")

        log_verbose(f"Calling auditor model: {auditor_model}")
        audit_response = call_executor(full_auditor_prompt, auditor_model, executor=executor)
        dump_buffer("Auditor Response", audit_response)

        # Log auditor response
        log_verbose("Logging auditor response to session file")
        with open(log_file, 'a') as f:
            f.write(f"\n### Iteration {iteration} - Auditor Response\n\n")
            f.write(strip_ansi(audit_response) + "\n")

        # Extract JSON from auditor response
        log_verbose("Extracting JSON from auditor response")
        auditor_json = extract_json(audit_response)
        dump_buffer("Extracted Auditor JSON", auditor_json or "NO JSON FOUND", max_lines=10)

        if auditor_json:
            verdict, reason, advice = parse_json_verdict(auditor_json)
            log_debug(f"Parsed verdict: {verdict}, reason: {reason}, advice: {advice}")
        else:
            verdict, reason, advice = None, None, None
            log_info("Could not extract JSON from auditor response")

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
            print(f"❓ Auditor verdict unclear: '{verdict}'")
            if auditor_json:
                print(f"Auditor JSON: {auditor_json}")
            print("Continuing anyway...")

        iteration += 1
        time.sleep(ITERATION_SLEEP)

    msg = f"Max iterations ({max_iterations}) reached without completion."
    print(f"\n❌ {msg}")
    log_info(msg)

    # Clean up auto-generated session logs unless keep_log is True
    if auto_generated_log and not keep_log:
        try:
            log_file.unlink()
            log_info(f"Cleaned up session log: {log_file}")
        except Exception as e:
            log_info(f"Failed to clean up session log: {e}")

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

    # Run oneshot
    success = run_oneshot(
        prompt=args.prompt,
        worker_model=args.worker_model,
        auditor_model=args.auditor_model,
        max_iterations=args.max_iterations,
        executor=args.executor,
        resume=resume,
        session_file=session_file,
        session_log=args.session_log,
        keep_log=args.keep_log
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()