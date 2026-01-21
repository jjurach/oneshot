"""
Oneshot Engine (Phase 5 - The Orchestrator)

The main event loop connecting the State Machine, Executors, and Pipeline.

Responsibilities:
- Load and manage execution context
- Query the state machine for next actions
- Invoke executors and pipeline
- Handle inactivity timeouts and interruptions
- Persist state transitions to oneshot.json
"""

import asyncio
import signal
import sys
from typing import Optional, List, Any, Dict
from contextlib import contextmanager

from .state import OnehotState, ActionType, StateMachine, Action
from .context import ExecutionContext
from .pipeline import (
    ingest_stream,
    timestamp_activity,
    InactivityMonitor,
    log_activity,
    parse_activity,
    InactivityTimeoutError,
    build_pipeline
)
from .protocol import ResultExtractor
from .providers.base import BaseExecutor, RecoveryResult


class OnehotEngine:
    """
    The main orchestrator loop for Oneshot task execution.

    Responsibilities:
    - Load execution context from oneshot.json
    - Query the state machine for next actions based on current state
    - Execute actions (run worker, run auditor, recover, exit)
    - Handle inactivity timeouts and keyboard interrupts
    - Persist state changes back to oneshot.json
    - Coordinate between executors, pipeline, and UI
    """

    def __init__(
        self,
        state_machine: Optional[StateMachine] = None,
        executor_worker: Optional[BaseExecutor] = None,
        executor_auditor: Optional[BaseExecutor] = None,
        context: Optional[ExecutionContext] = None,
        max_iterations: int = 5,
        inactivity_timeout: float = 300.0,
        result_extractor: Optional[ResultExtractor] = None,
        verbose: bool = False,
        ui_callback=None,
        worker_prompt_header: str = "oneshot execution",
        auditor_prompt_header: str = "oneshot auditor",
        reworker_prompt_header: str = "oneshot reworker",
        keep_log: bool = False,
    ):
        """
        Initialize the OnehotEngine.

        Args:
            state_machine: StateMachine instance (default: new instance)
            executor_worker: Worker executor instance
            executor_auditor: Auditor executor instance
            context: ExecutionContext instance (default: new instance)
            max_iterations: Maximum number of worker iterations
            inactivity_timeout: Timeout for inactivity detection (seconds)
            result_extractor: ResultExtractor instance for parsing results
            verbose: Enable verbose logging
            ui_callback: Optional callback for UI rendering
            worker_prompt_header: Custom header for worker prompts
            auditor_prompt_header: Custom header for auditor prompts
            reworker_prompt_header: Custom header for reworker prompts
            keep_log: Whether to keep the session log file after successful completion (default: False)
        """
        self.state_machine = state_machine or StateMachine()
        self.executor_worker = executor_worker
        self.executor_auditor = executor_auditor
        self.context = context
        self.max_iterations = max_iterations
        self.inactivity_timeout = inactivity_timeout
        self.result_extractor = result_extractor or ResultExtractor()
        self.verbose = verbose
        self.ui_callback = ui_callback
        self.worker_prompt_header = worker_prompt_header
        self.auditor_prompt_header = auditor_prompt_header
        self.reworker_prompt_header = reworker_prompt_header
        self.keep_log = keep_log
        self._interrupted = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful interruption."""
        def handle_interrupt(signum, frame):
            self._interrupted = True
            self.log_debug("Received SIGINT (Ctrl-C), will transition to INTERRUPTED state")

        try:
            signal.signal(signal.SIGINT, handle_interrupt)
        except ValueError:
            # Signal handlers can only be set in the main thread
            # This happens when running in a background thread (e.g. tests)
            self.log_debug("Warning: Could not set signal handlers (not in main thread)")

    def log_debug(self, msg: str):
        """Log debug message if verbose mode is enabled."""
        if self.verbose:
            print(f"[ENGINE] {msg}", file=sys.stderr)

    def _get_context_value(self, key: str, default: Any = None) -> Any:
        """Safely get a value from the execution context."""
        if not self.context:
            return default
        # Try the generic method first
        if hasattr(self.context, 'get_variable'):
            val = self.context.get_variable(key)
            if val is not None:
                return val
        # Fallback to direct access
        if hasattr(self.context, 'to_dict'):
            return self.context.to_dict().get(key, default)
        return default

    def run(self) -> bool:
        """
        Run the main orchestration loop.

        Returns:
            True if task completed successfully, False otherwise.
        """
        try:
            self.log_debug(f"Starting engine with initial state: {self.state_machine.current_state.name}")

            while True:
                # Check for interruption signal
                if self._interrupted:
                    self.log_debug("Processing SIGINT: transitioning to INTERRUPTED")
                    next_state = self.state_machine.transition(
                        self.state_machine.current_state,
                        "interrupt"
                    )
                    self.state_machine.current_state = next_state
                    self._save_state()
                    return False

                # Get current state and next action
                current_state = self.state_machine.current_state
                action = self.state_machine.get_next_action(current_state)

                iteration_count = self.context.get_iteration_count() if self.context else 0
                self.log_debug(
                    f"State: {current_state.name}, Action: {action.type.name}, "
                    f"Iteration: {iteration_count}/{self.max_iterations}"
                )

                # Execute action
                if action.type == ActionType.EXIT:
                    self.log_debug(f"Exiting: {action.payload.get('reason', 'unknown')}")
                    success = self._should_exit_success(current_state)

                    # Cleanup log file on success if keep_log is False
                    if success and not self.keep_log:
                        import os
                        log_path = self._get_context_value('session_log_path')
                        if log_path and os.path.exists(log_path):
                            try:
                                os.remove(log_path)
                                self.log_debug(f"Deleted session log: {log_path}")
                            except OSError as e:
                                self.log_debug(f"Failed to delete session log: {e}")

                    return success

                elif action.type == ActionType.RUN_WORKER:
                    self._execute_worker(current_state)

                elif action.type == ActionType.RUN_AUDITOR:
                    self._execute_auditor(current_state)

                elif action.type == ActionType.RECOVER:
                    self._execute_recovery(current_state)

                elif action.type == ActionType.WAIT:
                    # Wait states should not occur in single-threaded engine
                    # but included for completeness
                    self.log_debug("Engine in WAIT state")
                    asyncio.sleep(0.1)

        except KeyboardInterrupt:
            self.log_debug("Caught KeyboardInterrupt, transitioning to INTERRUPTED")
            self._interrupted = True
            try:
                next_state = self.state_machine.transition(
                    self.state_machine.current_state,
                    "interrupt"
                )
                self.state_machine.current_state = next_state
                self._save_state()
            except Exception as e:
                self.log_debug(f"Error during interrupt handling: {e}")
            return False

    def _execute_worker(self, current_state: OnehotState):
        """
        Execute the worker agent.

        Args:
            current_state: The current state (should be CREATED or REITERATION_PENDING)
        """
        if not self.executor_worker:
            self.log_debug("ERROR: No worker executor configured")
            next_state = self.state_machine.transition(current_state, "crash")
            self.state_machine.current_state = next_state
            self._save_state()
            return

        # Check max iterations
        iteration_count = self.context.get_iteration_count() if self.context else 0
        is_reiteration = current_state == OnehotState.REITERATION_PENDING
        if is_reiteration:
            iteration_count += 1
            if iteration_count >= self.max_iterations:
                self.log_debug(f"Max iterations ({self.max_iterations}) reached")
                next_state = self.state_machine.transition(current_state, "max_iterations")
                self.state_machine.current_state = next_state
                self._save_state()
                return
            if self.context:
                # Update iteration count in context
                self.context._data['iteration_count'] = iteration_count
                self.context.save()

        # Transition to WORKER_EXECUTING
        next_state = self.state_machine.transition(current_state, "start" if current_state == OnehotState.CREATED else "next")
        self.state_machine.current_state = OnehotState.WORKER_EXECUTING

        # Store reiteration flag in context for prompt generation
        if self.context and is_reiteration:
            self.context._data['is_reiteration'] = True
            self.context.save()
        self._save_state()

        # Execute worker with streaming pipeline
        try:
            prompt = self._generate_worker_prompt(iteration_count)
            self._pump_pipeline(
                self.executor_worker,
                prompt,
                "worker",
                current_state
            )

            # Worker completed successfully
            self.log_debug("Worker completed with exit code 0")
            next_state = self.state_machine.transition(OnehotState.WORKER_EXECUTING, "success")
            self.state_machine.current_state = next_state
            self._save_state()

        except InactivityTimeoutError:
            self.log_debug("Worker inactivity timeout detected")
            next_state = self.state_machine.transition(OnehotState.WORKER_EXECUTING, "inactivity")
            self.state_machine.current_state = next_state
            self._save_state()

        except KeyboardInterrupt:
            self._interrupted = True
            self.log_debug("Worker interrupted by user")
            next_state = self.state_machine.transition(OnehotState.WORKER_EXECUTING, "interrupt")
            self.state_machine.current_state = next_state
            self._save_state()

        except Exception as e:
            self.log_debug(f"Worker crashed: {e}")
            next_state = self.state_machine.transition(OnehotState.WORKER_EXECUTING, "crash")
            self.state_machine.current_state = next_state
            self._save_state()

    def _execute_auditor(self, current_state: OnehotState):
        """
        Execute the auditor agent.

        Args:
            current_state: The current state (should be AUDIT_PENDING)
        """
        if not self.executor_auditor:
            self.log_debug("ERROR: No auditor executor configured")
            next_state = self.state_machine.transition(current_state, "crash")
            self.state_machine.current_state = next_state
            self._save_state()
            return

        # Transition to AUDITOR_EXECUTING
        next_state = self.state_machine.transition(current_state, "next")
        self.state_machine.current_state = OnehotState.AUDITOR_EXECUTING
        self._save_state()

        # Execute auditor with streaming pipeline
        try:
            prompt = self._generate_auditor_prompt()
            self._pump_pipeline(
                self.executor_auditor,
                prompt,
                "auditor",
                current_state
            )

            # Parse auditor result (verdict: done/retry/impossible)
            verdict = self._extract_auditor_verdict()
            self.log_debug(f"Auditor verdict: {verdict}")

            # Transition based on verdict
            if verdict == "done":
                next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "done")
            elif verdict == "retry":
                next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "retry")
            elif verdict == "impossible":
                next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "impossible")
            else:
                # Default to done if unclear
                next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "done")

            self.state_machine.current_state = next_state
            self._save_state()

        except InactivityTimeoutError:
            self.log_debug("Auditor inactivity timeout (fatal)")
            next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "inactivity")
            self.state_machine.current_state = next_state
            self._save_state()

        except KeyboardInterrupt:
            self._interrupted = True
            self.log_debug("Auditor interrupted by user")
            next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "interrupt")
            self.state_machine.current_state = next_state
            self._save_state()

        except Exception as e:
            self.log_debug(f"Auditor crashed: {e}")
            next_state = self.state_machine.transition(OnehotState.AUDITOR_EXECUTING, "crash")
            self.state_machine.current_state = next_state
            self._save_state()

    def _execute_recovery(self, current_state: OnehotState):
        """
        Execute recovery logic for dead worker processes.

        Args:
            current_state: The current state (should be RECOVERY_PENDING)
        """
        if not self.executor_worker:
            self.log_debug("ERROR: No worker executor for recovery")
            next_state = self.state_machine.transition(current_state, "zombie_dead")
            self.state_machine.current_state = next_state
            self._save_state()
            return

        self.log_debug("Attempting to recover from dead worker process")

        try:
            task_id = self.context.to_dict().get('oneshot_id', 'unknown') if self.context else 'unknown'
            recovery_result: RecoveryResult = self.executor_worker.recover(task_id)

            if recovery_result.success:
                # Recovered activity found - replay into logs
                self.log_debug(f"Recovery successful: {recovery_result.verdict}")

                # Log recovered activities (store in context metadata)
                if self.context:
                    self.context.set_metadata('recovered_activities', recovery_result.recovered_activity)

                # Determine next state based on verdict
                if recovery_result.verdict == "success":
                    next_state = self.state_machine.transition(current_state, "zombie_success")
                elif recovery_result.verdict == "partial":
                    next_state = self.state_machine.transition(current_state, "zombie_partial")
                else:
                    next_state = self.state_machine.transition(current_state, "zombie_dead")
            else:
                # Nothing recovered
                self.log_debug("Recovery found no salvageable work")
                next_state = self.state_machine.transition(current_state, "zombie_dead")

            self.state_machine.current_state = next_state
            self._save_state()

        except Exception as e:
            self.log_debug(f"Recovery failed: {e}")
            next_state = self.state_machine.transition(current_state, "zombie_dead")
            self.state_machine.current_state = next_state
            self._save_state()

    def _pump_pipeline(
        self,
        executor: BaseExecutor,
        prompt: str,
        executor_name: str,
        state_before: OnehotState
    ):
        """
        Execute the streaming pipeline (ingest -> timestamp -> timeout check -> log -> parse -> render).

        Args:
            executor: The executor to run
            prompt: The prompt to send to the executor
            executor_name: Name of executor ("worker" or "auditor")
            state_before: State before execution

        Raises:
            InactivityTimeoutError: If inactivity timeout occurs
            KeyboardInterrupt: If user interrupts
        """
        with executor.execute(prompt) as stream:
            # Build and execute the complete pipeline
            log_path = self._get_context_value('session_log_path', 'oneshot-log.json')
            pipeline = build_pipeline(
                stream,
                log_path,
                inactivity_timeout=self.inactivity_timeout,
                executor_name=executor_name
            )

            # Pump through pipeline
            for event in pipeline:
                # Render to UI if callback provided
                if self.ui_callback:
                    self.ui_callback(event)

    def _generate_worker_prompt(self, iteration: int) -> str:
        """
        Generate the prompt for the worker agent.

        Args:
            iteration: Current iteration number (0-indexed)

        Returns:
            The worker prompt with context injected
        """
        # Get base task from context
        task = self._get_context_value('task', 'Undefined task')

        # Use reworker header if this is a reiteration (retry after auditor feedback)
        is_reiteration = self._get_context_value('is_reiteration', False)
        header = self.reworker_prompt_header if is_reiteration else self.worker_prompt_header

        # Build the worker prompt with header template
        header_template = f"""{header}

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

        # Inject iteration context if not first iteration
        if iteration > 0:
            # Get feedback from previous iteration
            last_auditor_result = self.context.get_auditor_result() if self.context else None
            feedback_text = f"\n\nAUDITOR FEEDBACK:\n{last_auditor_result}" if last_auditor_result else ""

            iteration_context = f"\n\n[Iteration {iteration + 1}/{self.max_iterations}]\nPrevious attempts did not complete the task. Try again with a different approach.{feedback_text}\n"
            return header_template + iteration_context + task
        else:
            return header_template + task

    def _generate_auditor_prompt(self) -> str:
        """
        Generate the prompt for the auditor agent.

        Returns:
            The auditor prompt with context and work results injected
        """
        # Extract the best result from logs
        log_path = self._get_context_value('session_log_path', 'oneshot-log.json')
        result = self.result_extractor.extract_result(log_path)

        if not result:
            result = "(No worker output found)"

        task = self._get_context_value('task', 'Undefined task')

        # Build auditor prompt with header template
        header_template = f"""{self.auditor_prompt_header}

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

Make your decision based on the task, work result, and these guidelines:

"""

        prompt = header_template + f"""TASK:
{task}

WORK RESULT:
{result}

Your verdict must be one of:
- "DONE": The task has been completed successfully.
- "RETRY": The task is incomplete. Ask the worker to try again.
- "IMPOSSIBLE": The task cannot be completed (missing resources, permissions denied, etc.).

Respond with ONLY your verdict and a brief explanation."""

        return prompt

    def _extract_auditor_verdict(self) -> str:
        """
        Extract the auditor's verdict from the latest activity logs.

        Returns:
            One of: "done", "retry", "impossible", or "unknown"
        """
        # Simple heuristic: look for keywords in latest output
        log_path = self._get_context_value('session_log_path', 'oneshot-log.json')

        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-10:]):  # Check last 10 lines
                    line_lower = line.lower()
                    if 'done' in line_lower or 'completed' in line_lower:
                        return "done"
                    elif 'retry' in line_lower or 'incomplete' in line_lower or 'reiterate' in line_lower:
                        return "retry"
                    elif 'impossible' in line_lower or 'cannot' in line_lower:
                        return "impossible"
        except Exception as e:
            self.log_debug(f"Error extracting verdict: {e}")

        return "unknown"

    def _save_state(self):
        """Save current state to oneshot.json."""
        if self.context:
            try:
                self.context.set_state(self.state_machine.current_state.name)
                self.context.save()
                self.log_debug(f"State saved: {self.state_machine.current_state.name}")
            except Exception as e:
                self.log_debug(f"Error saving state: {e}")

    def _should_exit_success(self, state: OnehotState) -> bool:
        """
        Determine if exit should be considered a success.

        Args:
            state: The final state

        Returns:
            True if successful completion, False otherwise
        """
        return state == OnehotState.COMPLETED
