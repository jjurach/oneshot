#!/usr/bin/env python3
"""
Oneshot - Autonomous task completion with auditor validation

Main CLI entry point and utility functions for session management.
The core orchestration logic has been moved to OnehotEngine (engine.py).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Import for test patching compatibility
from .providers.pty_utils import call_executor_pty

# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

# Default models and constants for legacy API compatibility
DEFAULT_WORKER_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_AUDITOR_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_MAX_ITERATIONS = 10

# PTY support detection
import os
SUPPORTS_PTY = hasattr(os, 'openpty')

# Streaming configuration
DISABLE_STREAMING = os.environ.get('ONESHOT_DISABLE_STREAMING', '').lower() in ('true', '1', 'yes')

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

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

# Default session directory
SESSION_DIR = Path.home() / '.oneshot' / 'sessions'

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


def count_iterations(session_file):
    """Count the number of iterations in a session."""
    if not session_file or not Path(session_file).exists():
        return 0
    try:
        from .context import ExecutionContext
        context = ExecutionContext.load(str(session_file))
        return context.iteration if hasattr(context, 'iteration') else 0
    except Exception as e:
        log_debug(f"Failed to count iterations: {e}")
        return 0


def _check_test_mode_blocking():
    """Check if running in test mode and should block."""
    return False


def call_executor(prompt, model, executor_type, initial_timeout=None, max_timeout=None):
    """
    Legacy function to call an executor with a prompt.
    Returns tuple of (stdout, stderr, returncode).

    Supports adaptive timeout: if initial_timeout is reached, retries with max_timeout.
    """
    # Build command based on executor type
    cmd = []
    if executor_type == 'claude':
        cmd = ['claude', '--model', model, prompt]
    elif executor_type == 'cline':
        cmd = ['cline', '--oneshot', prompt]
    elif executor_type == 'aider':
        cmd = ['aider', prompt]
    elif executor_type == 'gemini':
        cmd = ['gemini', prompt]
    elif executor_type == 'direct':
        cmd = ['ollama', 'run', model, prompt]
    else:
        raise ValueError(f"Unknown executor type: {executor_type}")

    try:
        # Try PTY first
        result = call_executor_pty(cmd)
        return result
    except (OSError, Exception) as e:
        # Fall back to subprocess if PTY fails
        timeout = initial_timeout or 300
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return (result.stdout, result.stderr, result.returncode)
        except subprocess.TimeoutExpired:
            # If adaptive timeout is enabled and we haven't hit max yet, retry
            if max_timeout and timeout < max_timeout:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=max_timeout)
                    return (result.stdout, result.stderr, result.returncode)
                except subprocess.TimeoutExpired:
                    return (f"Command timed out after {max_timeout} seconds: {cmd}", "", 124)
                except Exception as exc:
                    return (f"ERROR: {exc}", "", 1)
            else:
                return (f"Command timed out after {timeout} seconds: {cmd}", "", 124)
        except Exception as exc:
            return (f"ERROR: {exc}", "", 1)


async def call_executor_async(prompt, model, executor_type):
    """
    Legacy async function to call an executor with a prompt.
    Returns tuple of (stdout, stderr, returncode).

    For cline, uses OneshotTask. For other executors, falls back to sync.
    """
    if executor_type == 'cline':
        # Use OneshotTask for async cline execution
        try:
            from .task import OneshotTask
            task = OneshotTask(prompt, executor_type=executor_type)
            result = await task.run()
            if hasattr(result, 'success') and result.success:
                output = getattr(result, 'output', '')
                return (output, '')
            else:
                return ('', getattr(result, 'error', 'Unknown error'))
        except Exception as e:
            # Fallback to sync if OneshotTask fails
            loop = __import__('asyncio').get_event_loop()
            return await loop.run_in_executor(None, call_executor, prompt, model, executor_type)
    else:
        # For other executors, use sync version
        loop = __import__('asyncio').get_event_loop()
        return await loop.run_in_executor(None, call_executor, prompt, model, executor_type)


def run_oneshot_legacy(
    prompt,
    worker_model,
    auditor_model,
    max_iterations=DEFAULT_MAX_ITERATIONS,
    executor='claude',
    resume=False,
    session_file=None,
    session_log=None,
    keep_log=False,
    initial_timeout=30,
    max_timeout=300,
    activity_interval=5,
    worker_prompt_header='oneshot worker',
    auditor_prompt_header='oneshot auditor'
):
    """Legacy API for running oneshot synchronously."""
    from .engine import OnehotEngine
    from .state import StateMachine

    context = _load_or_create_context(resume, session_file, prompt)
    worker_executor = _create_executor_instance(executor, worker_model)
    auditor_executor = _create_executor_instance(executor, auditor_model)

    state_machine = StateMachine()
    engine = OnehotEngine(
        state_machine=state_machine,
        executor_worker=worker_executor,
        executor_auditor=auditor_executor,
        context=context,
        max_iterations=max_iterations,
        inactivity_timeout=initial_timeout,
        verbose=VERBOSITY > 0,
        worker_prompt_header=worker_prompt_header,
        auditor_prompt_header=auditor_prompt_header,
    )

    return engine.run()


async def run_oneshot_async_legacy(
    prompt,
    worker_model,
    auditor_model,
    max_iterations=DEFAULT_MAX_ITERATIONS,
    executor='claude',
    resume=False,
    session_file=None,
    session_log=None,
    keep_log=False,
    initial_timeout=30,
    max_timeout=300,
    activity_interval=5,
    worker_prompt_header='oneshot worker',
    auditor_prompt_header='oneshot auditor'
):
    """Legacy API for running oneshot asynchronously."""
    # For now, this just calls the sync version wrapped in an async context
    # A truly async implementation would require refactoring the engine
    loop = __import__('asyncio').get_event_loop()
    return await loop.run_in_executor(
        None,
        run_oneshot_legacy,
        prompt,
        worker_model,
        auditor_model,
        max_iterations,
        executor,
        resume,
        session_file,
        session_log,
        keep_log,
        initial_timeout,
        max_timeout,
        activity_interval,
        worker_prompt_header,
        auditor_prompt_header
    )

# ============================================================================
# EXECUTOR FACTORY
# ============================================================================

def _create_executor_instance(executor_type: str, model: Optional[str]) -> 'BaseExecutor':
    """
    Create an executor instance of the specified type.

    Args:
        executor_type: Type of executor ('claude', 'cline', 'aider', 'gemini', 'direct')
        model: Optional model name for executors that support it

    Returns:
        BaseExecutor instance

    Raises:
        ValueError: If executor type is not recognized
    """
    if executor_type == 'claude':
        from .providers.claude_executor import ClaudeExecutor
        return ClaudeExecutor(model=model)
    elif executor_type == 'cline':
        from .providers.cline_executor import ClineExecutor
        return ClineExecutor()
    elif executor_type == 'aider':
        from .providers.aider_executor import AiderExecutor
        return AiderExecutor(model=model)
    elif executor_type == 'gemini':
        from .providers.gemini_executor import GeminiCLIExecutor
        return GeminiCLIExecutor()
    elif executor_type == 'direct':
        from .providers.direct_executor import DirectExecutor
        return DirectExecutor(model=model or "llama-pro:latest")
    else:
        raise ValueError(f"Unknown executor type: {executor_type}")

# ============================================================================
# EXECUTION CONTEXT MANAGEMENT
# ============================================================================

def _load_or_create_context(resume: bool, session_file: Optional[Path], task_prompt: str) -> 'ExecutionContext':
    """
    Load an existing execution context or create a new one.

    Args:
        resume: Whether resuming a session
        session_file: Path to session file if resuming specific session
        task_prompt: The task prompt to execute

    Returns:
        ExecutionContext instance

    Raises:
        FileNotFoundError: If session_file doesn't exist
    """
    from .context import ExecutionContext

    if resume and session_file:
        log_verbose(f"Loading context from: {session_file}")
        context = ExecutionContext.load(str(session_file))
    else:
        # Create new context
        log_verbose("Creating new execution context")
        context = ExecutionContext(
            session_dir=str(SESSION_DIR),
            task=task_prompt,
            executor="oneshot",  # Will be updated by engine
        )

    return context

# ============================================================================
# CLI ENTRY POINT
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
        '--reworker-prompt-header',
        default='oneshot reworker',
        help='Custom header for reworker prompts (default: "oneshot reworker")'
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
        choices=['claude', 'cline', 'aider', 'gemini', 'direct'],
        help=f'Which executor to use: claude, cline, aider, gemini, or direct (default: cline)'
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
    elif args.executor == "direct":
        # Direct executor uses Ollama models
        default_worker = "llama-pro:latest"
        default_auditor = "llama-pro:latest"

        if args.worker_model is None:
            args.worker_model = default_worker
        if args.auditor_model is None:
            args.auditor_model = default_auditor
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

    # Use new OnehotEngine for execution
    try:
        from .engine import OnehotEngine
        from .state import StateMachine

        # Load or create execution context
        context = _load_or_create_context(resume, session_file, args.prompt)

        # Create executor instances
        worker_executor = _create_executor_instance(args.executor, args.worker_model)
        auditor_executor = _create_executor_instance(args.executor, args.auditor_model)

        # Create state machine
        state_machine = StateMachine()

        # Create and run engine
        engine = OnehotEngine(
            state_machine=state_machine,
            executor_worker=worker_executor,
            executor_auditor=auditor_executor,
            context=context,
            max_iterations=args.max_iterations,
            inactivity_timeout=args.initial_timeout,
            verbose=args.verbose or args.debug,
            worker_prompt_header=args.worker_prompt_header,
            auditor_prompt_header=args.auditor_prompt_header,
            reworker_prompt_header=args.reworker_prompt_header,
        )

        # Run the engine
        success = engine.run()

    except Exception as e:
        log_debug(f"Engine execution failed: {e}")
        import traceback
        if args.debug:
            traceback.print_exc()
        success = False

    sys.exit(0 if success else 1)


# ============================================================================
# JSON PARSING UTILITIES (Legacy Functions)
# ============================================================================

import json
import re


def extract_json(text):
    """
    Legacy function to extract JSON from text.
    Returns the first valid JSON object or array found in the text.
    """
    # Try to find JSON in the text
    # Look for patterns like {...} or [...]

    # Find all potential JSON objects
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
    matches = re.finditer(json_pattern, text)

    for match in matches:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            continue

    # Try parsing the entire text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_json_verdict(text):
    """
    Legacy function to parse JSON verdict from text.
    Extracts and returns JSON verdict or parsed result.
    """
    json_obj = extract_json(text)
    if json_obj:
        return json_obj
    return None


def parse_lenient_verdict(text):
    """
    Legacy function to parse verdict in a lenient way.
    Tries to extract structured data even if not strict JSON.
    """
    # Try strict JSON first
    json_obj = extract_json(text)
    if json_obj:
        return json_obj

    # Try to extract key-value pairs
    verdict = {}
    for line in text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            verdict[key.strip()] = value.strip()

    return verdict if verdict else None


def contains_completion_indicators(text):
    """
    Legacy function to check if text contains completion indicators.
    Returns True if text indicates task completion.
    """
    completion_keywords = [
        'complete', 'done', 'finished', 'success',
        'accomplished', 'resolved', 'achieved',
        'final', 'concluded', 'finished'
    ]

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in completion_keywords)


def extract_lenient_json(text):
    """
    Legacy function to extract JSON leniently.
    Similar to extract_json but more forgiving.
    """
    # Try strict JSON extraction first
    json_obj = extract_json(text)
    if json_obj:
        return json_obj

    # Try extracting from markdown code blocks
    code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
    matches = re.finditer(code_block_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    return None


def read_session_context(session_file):
    """
    Legacy function to read session context from file.
    Returns the context or None if file doesn't exist.
    """
    if not session_file or not Path(session_file).exists():
        return None
    try:
        from .context import ExecutionContext
        return ExecutionContext.load(str(session_file))
    except Exception as e:
        log_debug(f"Failed to read session context: {e}")
        return None


def parse_streaming_json(stream_data):
    """
    Legacy function to parse streaming JSON data.
    Handles JSON Lines format and partial JSON objects.
    """
    if isinstance(stream_data, str):
        lines = stream_data.split('\n')
    else:
        lines = stream_data

    results = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError:
            # Try to handle partial JSON
            log_debug(f"Failed to parse JSON line: {line}")
            continue

    return results if results else None


def get_cline_task_dir():
    """
    Legacy function to get the cline task directory.
    Returns the cline task directory path.
    """
    from pathlib import Path
    return Path.home() / '.cline' / 'task'


def strip_ansi(text):
    """
    Legacy function to strip ANSI color codes from text.
    Returns text without ANSI escape sequences.
    """
    # Pattern to match ANSI escape sequences
    ansi_escape_pattern = r'\x1b\[[0-9;]*m'
    return re.sub(ansi_escape_pattern, '', text)


def run_oneshot(
    prompt,
    worker_provider=None,
    auditor_provider=None,
    max_iterations=DEFAULT_MAX_ITERATIONS,
    resume=False,
    session_file=None,
    session_log=None,
    keep_log=False,
    initial_timeout=30,
    max_timeout=300,
    activity_interval=5
):
    """
    Legacy function to run oneshot with provider-based API.
    Creates executors from providers if needed.
    """
    from .engine import OnehotEngine
    from .state import StateMachine

    # If providers are given, extract executors
    if worker_provider:
        worker_executor = worker_provider if isinstance(worker_provider, object) and hasattr(worker_provider, 'select_command') else worker_provider
    else:
        worker_executor = _create_executor_instance('claude', None)

    if auditor_provider:
        auditor_executor = auditor_provider if isinstance(auditor_provider, object) and hasattr(auditor_provider, 'select_command') else auditor_provider
    else:
        auditor_executor = _create_executor_instance('claude', None)

    context = _load_or_create_context(resume, session_file, prompt)
    state_machine = StateMachine()
    engine = OnehotEngine(
        state_machine=state_machine,
        executor_worker=worker_executor,
        executor_auditor=auditor_executor,
        context=context,
        max_iterations=max_iterations,
        inactivity_timeout=initial_timeout,
        verbose=VERBOSITY > 0,
    )

    return engine.run()


async def run_oneshot_async(
    prompt,
    worker_provider=None,
    auditor_provider=None,
    max_iterations=DEFAULT_MAX_ITERATIONS,
    resume=False,
    session_file=None,
    session_log=None,
    keep_log=False,
    initial_timeout=30,
    max_timeout=300,
    activity_interval=5
):
    """
    Legacy async function to run oneshot with provider-based API.
    """
    loop = __import__('asyncio').get_event_loop()
    return await loop.run_in_executor(
        None,
        run_oneshot,
        prompt,
        worker_provider,
        auditor_provider,
        max_iterations,
        resume,
        session_file,
        session_log,
        keep_log,
        initial_timeout,
        max_timeout,
        activity_interval
    )


def monitor_task_activity(task_id, initial_timeout=30, max_timeout=300, activity_interval=5):
    """
    Legacy function to monitor task activity.
    Checks if a task is still running and updates timeout accordingly.
    """
    import time

    start_time = time.time()
    last_activity = start_time

    # Simulate activity monitoring
    while True:
        current_time = time.time()
        elapsed = current_time - start_time

        if elapsed > max_timeout:
            return {'status': 'timeout', 'elapsed': elapsed}

        # Check inactivity
        inactivity_time = current_time - last_activity
        if inactivity_time > initial_timeout and elapsed < max_timeout:
            # Task is still running, extend timeout
            last_activity = current_time

        time.sleep(activity_interval)

        # Placeholder: would check actual task status here
        break

    return {'status': 'monitoring', 'elapsed': elapsed}


if __name__ == '__main__':
    main()
