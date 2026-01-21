#!/usr/bin/env python3
"""
Oneshot - Autonomous task completion with auditor validation

Main CLI entry point and utility functions for session management.
The core orchestration logic has been moved to OnehotEngine (engine.py).
"""

import argparse
import datetime
import os
import sys
from pathlib import Path
from typing import Optional

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

from .cli.session_utils import find_latest_session, DEFAULT_SESSION_DIR

# Local variable for runtime modification
SESSION_DIR = DEFAULT_SESSION_DIR

# ============================================================================
# EXECUTOR FACTORY
# ============================================================================

def _create_executor_instance(executor_type: str, model: Optional[str]) -> 'BaseExecutor':
    """
    Create an executor instance using the ExecutorRegistry.
    """
    from .providers.executor_registry import create_executor
    
    # Map CLI model selection to executor constructor arguments
    kwargs = {}
    if executor_type in ('claude', 'aider', 'direct'):
        kwargs['model'] = model
        
    return create_executor(executor_type, **kwargs)

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
        # Update task if provided (allows changing task on resume)
        if task_prompt:
            context.set_variable('task', task_prompt)
    else:
        # Create new context with a generated filepath
        log_verbose("Creating new execution context")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        oneshot_id = f"oneshot_{timestamp}"
        filename = f"{oneshot_id}.json"
        filepath = SESSION_DIR / filename
        context = ExecutionContext(str(filepath))
        context._data['oneshot_id'] = oneshot_id
        context.set_variable('task', task_prompt)
        context.save()

    return context

# ============================================================================
# UI CALLBACKS
# ============================================================================

def _print_pipeline_event(event: dict):
    """
    Format and print pipeline events to stdout in a readable format.

    Args:
        event (dict): The event dictionary from the pipeline
    """
    if event.get('is_heartbeat'):
        return

    data = event.get('data')
    if data:
        # Format different types of activity data
        if isinstance(data, str):
            # Handle string data (like conversation headers)
            if data.startswith('*') and data.endswith('*'):
                # Conversation header
                print(f"\n📝 {data[1:-1]}")
            else:
                # Regular text output
                print(data, end='', flush=True)
        elif isinstance(data, dict):
            # Handle structured activity data
            activity_type = data.get('say', 'unknown')
            text_content = data.get('text', '')

            # Format based on activity type
            if activity_type == 'text':
                # Regular text output from agent
                print(text_content, end='', flush=True)
            elif activity_type == 'reasoning':
                # Agent reasoning/thinking
                print(f"\n🤔 {text_content}")
            elif activity_type == 'checkpoint_created':
                # Checkpoint marker
                print(f"\n📌 Checkpoint saved")
            elif activity_type == 'completion_result':
                # Final result
                print(f"\n✅ {text_content}")
            elif activity_type == 'api_req_started':
                # API request (less verbose)
                if text_content and len(text_content) > 100:
                    truncated = text_content[:100] + "..."
                    print(f"\n🔄 API request: {truncated}")
                else:
                    print(f"\n🔄 API request initiated")
            else:
                # Unknown activity type - show as generic activity
                print(f"\n📋 Activity ({activity_type}): {text_content[:100]}{'...' if len(text_content) > 100 else ''}")
        else:
            # Fallback for other data types
            print(f"\n📄 {str(data)}")

        # Ensure at least one newline after each activity
        print("", flush=True)


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

        # Populate metadata
        context.set_metadata("provider_worker", args.worker_model)
        context.set_metadata("provider_auditor", args.auditor_model)
        context.set_metadata("executor_type", args.executor)
        context.set_metadata("start_time", datetime.datetime.now().isoformat())
        context.set_metadata("cwd", os.getcwd())
        context.set_metadata("max_iterations", args.max_iterations)
        context.set_metadata("initial_timeout", args.initial_timeout)
        context.set_metadata("max_timeout", args.max_timeout)
        context.set_metadata("activity_interval", args.activity_interval)
        
        if args.session_log:
            context.set_metadata("session_log_path", args.session_log)
        
        context.save()

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
            ui_callback=_print_pipeline_event,
            worker_prompt_header=args.worker_prompt_header,
            auditor_prompt_header=args.auditor_prompt_header,
            reworker_prompt_header=args.reworker_prompt_header,
            keep_log=args.keep_log,
            session_log_path=args.session_log,
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


if __name__ == '__main__':
    main()