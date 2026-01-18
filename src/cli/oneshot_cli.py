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
    from pathlib import Path

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
        default=5,
        help='Maximum concurrent tasks in async mode (default: 5)'
    )

    parser.add_argument(
        '--idle-threshold',
        type=int,
        default=60,
        help='Global idle threshold in seconds for async orchestrator (default: 60)'
    )

    parser.add_argument(
        '--heartbeat-interval',
        type=int,
        default=10,
        help='Heartbeat check interval in seconds for async orchestrator (default: 10)'
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
        default=8000,
        help='Port for web dashboard (default: 8000)'
    )

    parser.add_argument(
        '--tui',
        action='store_true',
        help='Enable terminal user interface (TUI)'
    )

    parser.add_argument(
        '--tui-refresh',
        type=float,
        default=1.0,
        help='TUI refresh rate in seconds (default: 1.0)'
    )

    args = parser.parse_args()

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
    """Synchronous wrapper for backward compatibility."""
    # Check if --async flag is used
    import sys
    if '--async' in sys.argv:
        # Run async version
        asyncio.run(main_async())
    else:
        # Run sync version
        from oneshot.oneshot import main as sync_main
        sync_main()


if __name__ == "__main__":
    main()