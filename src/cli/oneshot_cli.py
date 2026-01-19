#!/usr/bin/env python3
"""Command line interface for oneshot."""

import asyncio
import sys
from oneshot.oneshot import main, run_oneshot_async_legacy

async def main_async():
    """Async version of main function."""
    # Import here to avoid circular imports
    import argparse
    from oneshot.oneshot import (
        DEFAULT_WORKER_MODEL, DEFAULT_AUDITOR_MODEL, DEFAULT_MAX_ITERATIONS,
        VERBOSITY, log_debug, log_verbose, log_info, find_latest_session, SESSION_DIR,
        count_iterations
    )
    from oneshot.config import get_global_config, apply_executor_defaults
    from pathlib import Path

    # Load configuration file
    config, config_error = get_global_config()
    if config_error:
        print(f"Warning: Configuration file error: {config_error}", file=sys.stderr)
        print("Using default settings.", file=sys.stderr)

    # Apply executor-specific defaults to config
    config = apply_executor_defaults(config)

    parser = argparse.ArgumentParser(
        description='Oneshot - Autonomous task completion with auditor validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  oneshot 'What is the capital of Denmark?'
  oneshot --async --worker-model claude-3-5-sonnet-20241022 'Complex task'
  oneshot --resume 'Continue working on this'
  oneshot --session-log my_task.md 'Task with custom logging'

Async Mode:
  oneshot --async --max-concurrent 5 'Run multiple tasks concurrently'
  oneshot --async --idle-threshold 120 'Custom idle detection timeout'

Configuration:
  Create ~/.oneshot.json to set default values. Command-line options override config file.
        """
    )

    parser.add_argument(
        'prompt',
        help='The task/prompt to complete'
    )

    parser.add_argument(
        '--async',
        dest='async_mode',
        action='store_true',
        help='Use asynchronous execution with state machines and concurrency'
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
        choices=['claude', 'cline', 'aider'],
        help=f'Which executor to use: claude, cline, or aider (default: {config["executor"]})'
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

    # Provider configuration options
    parser.add_argument(
        '--worker-provider',
        choices=['executor', 'direct'],
        help='Worker provider type: executor (subprocess) or direct (HTTP API)'
    )

    parser.add_argument(
        '--worker-endpoint',
        type=str,
        help='API endpoint URL for worker when using direct provider'
    )

    parser.add_argument(
        '--worker-api-key',
        type=str,
        help='API key for worker direct provider (optional for local models)'
    )

    parser.add_argument(
        '--auditor-provider',
        choices=['executor', 'direct'],
        help='Auditor provider type: executor (subprocess) or direct (HTTP API)'
    )

    parser.add_argument(
        '--auditor-executor',
        choices=['claude', 'cline'],
        help='Executor to use for auditor when using executor provider'
    )

    parser.add_argument(
        '--auditor-endpoint',
        type=str,
        help='API endpoint URL for auditor when using direct provider'
    )

    parser.add_argument(
        '--auditor-api-key',
        type=str,
        help='API key for auditor direct provider (optional for local models)'
    )

    # Async-specific options
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=config['max_concurrent'],
        help=f'Maximum concurrent tasks in async mode (default: {config["max_concurrent"]})'
    )

    parser.add_argument(
        '--idle-threshold',
        type=int,
        default=config['idle_threshold'],
        help=f'Global idle threshold in seconds for async orchestrator (default: {config["idle_threshold"]})'
    )

    parser.add_argument(
        '--heartbeat-interval',
        type=int,
        default=config['heartbeat_interval'],
        help=f'Heartbeat check interval in seconds for async orchestrator (default: {config["heartbeat_interval"]})'
    )

    # UI options
    parser.add_argument(
        '--web-ui',
        action='store_true',
        help='Enable web-based dashboard UI'
    )

    parser.add_argument(
        '--web-port',
        type=int,
        default=config['web_port'],
        help=f'Port for web dashboard (default: {config["web_port"]})'
    )

    parser.add_argument(
        '--tui',
        action='store_true',
        help='Enable terminal user interface (TUI)'
    )

    parser.add_argument(
        '--tui-refresh',
        type=float,
        default=config['tui_refresh'],
        help=f'TUI refresh rate in seconds (default: {config["tui_refresh"]})'
    )

    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Show example configuration file content and exit'
    )

    args = parser.parse_args()

    # Handle --show-config option
    if args.show_config:
        from oneshot.config import create_example_config
        print("Example configuration file content:")
        print("=" * 50)
        print(create_example_config())
        print("=" * 50)
        print(f"Save this to {get_config_path()} to use these defaults.")
        print("Command-line options will override configuration file settings.")
        sys.exit(0)

    # Determine if using new provider-based API or legacy API
    use_provider_api = (args.worker_provider is not None or args.auditor_provider is not None or
                        args.worker_endpoint is not None or args.auditor_endpoint is not None)

    if use_provider_api:
        # Use new provider-based API
        from oneshot.providers import ProviderConfig, create_provider

        # Build worker provider config
        if args.worker_provider == 'direct' or args.worker_endpoint:
            if not args.worker_endpoint:
                print("ERROR: --worker-endpoint required when using direct worker provider", file=sys.stderr)
                sys.exit(1)
            if not args.worker_model:
                print("ERROR: --worker-model required when using direct worker provider", file=sys.stderr)
                sys.exit(1)

            worker_config = ProviderConfig(
                provider_type='direct',
                endpoint=args.worker_endpoint,
                model=args.worker_model,
                api_key=args.worker_api_key,
                timeout=args.initial_timeout
            )
        else:
            # Default to executor provider
            executor = args.executor
            model = args.worker_model

            # Set default model for claude executor
            if executor == "claude" and not model:
                model = "claude-3-5-haiku-20241022"
            elif executor == "cline":
                if model:
                    print("Model selection is not supported for the cline executor. Please configure the model in the cline tool.", file=sys.stderr)
                    sys.exit(1)
                model = None
            elif executor == "aider":
                # Aider uses built-in default, but model can be overridden if needed
                model = args.worker_model

            worker_config = ProviderConfig(
                provider_type='executor',
                executor=executor,
                model=model,
                timeout=args.initial_timeout
            )

        # Build auditor provider config
        if args.auditor_provider == 'direct' or args.auditor_endpoint:
            if not args.auditor_endpoint:
                print("ERROR: --auditor-endpoint required when using direct auditor provider", file=sys.stderr)
                sys.exit(1)
            if not args.auditor_model:
                print("ERROR: --auditor-model required when using direct auditor provider", file=sys.stderr)
                sys.exit(1)

            auditor_config = ProviderConfig(
                provider_type='direct',
                endpoint=args.auditor_endpoint,
                model=args.auditor_model,
                api_key=args.auditor_api_key,
                timeout=args.initial_timeout
            )
        else:
            # Default to executor provider
            executor = args.auditor_executor if args.auditor_executor else args.executor
            model = args.auditor_model

            # Set default model for claude executor
            if executor == "claude" and not model:
                model = "claude-3-5-haiku-20241022"
            elif executor == "cline":
                if model:
                    print("Model selection is not supported for the cline executor. Please configure the model in the cline tool.", file=sys.stderr)
                    sys.exit(1)
                model = None
            elif executor == "aider":
                # Aider uses built-in default, but model can be overridden if needed
                model = args.auditor_model

            auditor_config = ProviderConfig(
                provider_type='executor',
                executor=executor,
                model=model,
                timeout=args.initial_timeout
            )

        worker_provider = create_provider(worker_config)
        auditor_provider = create_provider(auditor_config)

    else:
        # Use legacy API with model strings
        if args.executor == "cline":
            if args.worker_model or args.auditor_model:
                print("Model selection is not supported for the cline executor. Please configure the model in the cline tool.", file=sys.stderr)
                sys.exit(1)
            args.worker_model = None
            args.auditor_model = None
        elif args.executor == "aider":
            # Aider executor uses built-in models, no model selection needed via CLI
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

    # Run oneshot (async or sync)
    if args.async_mode:
        log_info("Using async execution mode")

        # UI components not yet fully integrated with async mode
        if args.web_ui or args.tui:
            print("Warning: UI components (--web-ui, --tui) are not yet fully integrated with async mode. Running without UI.", file=sys.stderr)

        try:
            if use_provider_api:
                # Use new provider-based async API
                from oneshot.oneshot import run_oneshot_async

                success = await run_oneshot_async(
                    prompt=args.prompt,
                    worker_provider=worker_provider,
                    auditor_provider=auditor_provider,
                    max_iterations=args.max_iterations,
                    resume=resume,
                    session_file=session_file,
                    session_log=args.session_log,
                    keep_log=args.keep_log,
                    initial_timeout=args.initial_timeout,
                    max_timeout=args.max_timeout,
                    activity_interval=args.activity_interval
                )
            else:
                # Use legacy async API
                from oneshot.oneshot import run_oneshot_async_legacy

                success = await run_oneshot_async_legacy(
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
        except Exception as e:
            log_info(f"Async execution error: {e}")
            import traceback
            traceback.print_exc()
            success = False

    else:
        if use_provider_api:
            # Use new provider-based sync API
            from oneshot.oneshot import run_oneshot

            success = run_oneshot(
                prompt=args.prompt,
                worker_provider=worker_provider,
                auditor_provider=auditor_provider,
                max_iterations=args.max_iterations,
                resume=resume,
                session_file=session_file,
                session_log=args.session_log,
                keep_log=args.keep_log,
                initial_timeout=args.initial_timeout,
                max_timeout=args.max_timeout,
                activity_interval=args.activity_interval
            )
        else:
            # Use legacy sync API
            from oneshot.oneshot import run_oneshot_legacy

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


def main():
    """Entry point that routes to async main (which handles both async and sync)."""
    # Always use main_async, which handles both --async mode and sync mode
    asyncio.run(main_async())


if __name__ == "__main__":
    main()