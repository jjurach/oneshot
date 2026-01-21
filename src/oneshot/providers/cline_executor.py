"""
ClineExecutor - Executor implementation for Cline agent.

Encapsulates all Cline-specific command construction, activity parsing,
and output formatting logic.
"""

import json
import re
import subprocess
import select
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Generator
from .base import BaseExecutor, ExecutionResult, RecoveryResult


class ClineExecutor(BaseExecutor):
    """
    Executor for the Cline agent.

    Cline outputs streaming JSON objects containing activity information.
    This executor handles command construction with Cline-specific flags,
    parsing of JSON stream output, and extraction of meaningful activity.
    """

    def __init__(self):
        """Initialize ClineExecutor."""
        self.process = None

    def get_provider_name(self) -> str:
        """
        Get the executor type identifier.

        Returns:
            str: "cline"
        """
        return "cline"

    def get_provider_metadata(self) -> Dict[str, Any]:
        """
        Get Cline-specific configuration metadata.

        Returns:
            Dict[str, Any]: Metadata including type, capabilities, constraints
        """
        return {
            "type": "cline",
            "name": "Cline",
            "description": "Autonomous AI agent with code editing capabilities",
            "output_format": "json_stream",
            "supports_model_selection": False,
            "captures_git_commits": True,
            "requires_pty": True,
            "timeout_seconds": 300,
            "flags": ["--yolo", "--mode", "act", "--no-interactive", "--output-format", "json", "--oneshot"]
        }

    def should_capture_git_commit(self) -> bool:
        """
        Cline creates git commits for its changes.

        Returns:
            bool: True
        """
        return True

    @contextmanager
    def execute(self, prompt: str) -> Generator[str, None, None]:
        """
        Execute a task via Cline as a subprocess and yield streaming output.

        This context manager starts the Cline process, yields a generator that
        produces streaming output, and ensures the process is terminated on exit.

        Args:
            prompt (str): The task prompt to execute

        Yields:
            Generator[str, None, None]: A generator yielding lines of output

        Raises:
            OSError: If Cline command is not found or cannot be executed
        """
        cmd = self.build_command(prompt)
        self.process = None

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            yield self._stream_output(self.process)

        finally:
            if self.process is not None and self.process.poll() is None:
                # Process still running, terminate it
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if termination times out
                    self.process.kill()
                    self.process.wait()

    def recover(self, task_id: str) -> RecoveryResult:
        """
        Recover activity from Cline's task state files (forensic analysis).

        Cline stores task information in ~/.cline/tasks/{task_id}/ui_messages.json.
        This method attempts to parse that file to recover lost activity.

        Args:
            task_id (str): The Cline task ID to recover from

        Returns:
            RecoveryResult: Result with recovered activities or failure info
        """
        try:
            task_path = Path.home() / ".cline" / "tasks" / task_id / "ui_messages.json"

            if not task_path.exists():
                return RecoveryResult(
                    success=False,
                    recovered_activity=[],
                    verdict=f"No task state found at {task_path}"
                )

            with open(task_path, 'r') as f:
                messages = json.load(f)

            if not isinstance(messages, list):
                return RecoveryResult(
                    success=False,
                    recovered_activity=[],
                    verdict="Task state is not a list of messages"
                )

            # Filter for completion/error messages
            recovered = []
            final_verdict = "INCOMPLETE"

            for msg in messages:
                if isinstance(msg, dict):
                    recovered.append(msg)
                    # Check for completion indicators
                    if msg.get('type') == 'completion' or msg.get('say') == 'completion_result':
                        final_verdict = "DONE"

            return RecoveryResult(
                success=True,
                recovered_activity=recovered,
                verdict=final_verdict
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                recovered_activity=[],
                verdict=f"Recovery failed: {str(e)}"
            )

    def _stream_output(self, process: subprocess.Popen) -> Generator[str, None, None]:
        """
        Generator that yields lines from a subprocess stdout with timeout support.

        Uses select.select for non-blocking I/O on Unix systems, allowing
        for timeout and inactivity monitoring.

        Args:
            process (subprocess.Popen): The subprocess to read from

        Yields:
            str: Lines of output from stdout
        """
        while True:
            line = process.stdout.readline()
            if not line:
                break
            yield line

    def build_command(self, prompt: str, model: Optional[str] = None) -> List[str]:
        """
        Build Cline CLI command for executing a task.

        Cline command format:
        cline --yolo --mode act --no-interactive --output-format json --oneshot "<prompt>"

        Args:
            prompt (str): The task prompt to send to Cline
            model (Optional[str]): Ignored for Cline (not supported)

        Returns:
            List[str]: Command and arguments for subprocess execution
        """
        cmd = [
            'cline',
            '--yolo',  # Auto-approve user interactions
            '--mode', 'act',  # Action mode (vs planning mode)
            '--no-interactive',  # Non-interactive mode
            '--output-format', 'json',  # Output as JSON stream
            '--oneshot',  # One-shot mode (single execution)
            prompt  # The task prompt
        ]
        return cmd

    def parse_streaming_activity(self, raw_output: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse Cline's streaming JSON output into structured results.

        Cline outputs a stream of JSON objects. Each object may contain:
        - "say": "completion_result" with "text" field for final result
        - "ask": "plan_mode_respond" with "text" field for plan responses
        - Other activity types with execution details

        Args:
            raw_output (str): Raw streaming output containing JSON objects

        Returns:
            Tuple[str, Dict[str, Any]]: (stdout_summary, auditor_details)
        """
        # Split JSON stream into individual objects
        json_objects = self._split_json_stream(raw_output)

        # Extract completion results from JSON activity objects
        extracted_texts = []
        activity_details = []

        for json_obj in json_objects:
            text = self._extract_activity_text(json_obj)
            if text:
                extracted_texts.append(text)

            # Collect all activity for audit log
            activity_details.append({
                "type": self._get_activity_type(json_obj),
                "object": json_obj
            })

        # Aggregate extracted texts as primary output
        stdout_summary = '\n'.join(extracted_texts) if extracted_texts else raw_output

        # Prepare auditor details
        auditor_details = {
            "executor_type": "cline",
            "activity_count": len(activity_details),
            "activities": activity_details,
            "extracted_text_segments": len(extracted_texts),
            "raw_output_length": len(raw_output)
        }

        return stdout_summary, auditor_details

    def run_task(self, task: str) -> ExecutionResult:
        """
        Execute a task using Cline.

        Args:
            task (str): The task to execute

        Returns:
            ExecutionResult: Result with output and metadata
        """
        # This is implemented in the oneshot.py orchestrator
        # The abstract method is defined here for interface compliance
        raise NotImplementedError("run_task is implemented by orchestrator")

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    @staticmethod
    def _split_json_stream(raw_output: str) -> List[Dict[str, Any]]:
        """
        Split streaming JSON output from Cline by JSON object boundaries.

        Cline outputs a stream of JSON objects. This function finds each object
        by looking for complete JSON structures (starts with { and ends with }).

        Args:
            raw_output (str): Raw streaming output containing multiple JSON objects

        Returns:
            List[Dict[str, Any]]: List of parsed JSON objects, or empty list if none found
        """
        json_objects = []

        if not raw_output or not raw_output.strip():
            return json_objects

        # Remove ANSI escape codes that Cline includes
        ansi_escape = re.compile(r'\x1B\[[0-9;]*m|\[38;5;\d+m')
        cleaned = ansi_escape.sub('', raw_output)

        # Find each complete JSON object by tracking braces
        brace_count = 0
        current_json = []
        in_json = False

        for char in cleaned:
            if char == '{':
                if not in_json:
                    in_json = True
                    current_json = []
                current_json.append(char)
                brace_count += 1
            elif char == '}':
                current_json.append(char)
                brace_count -= 1
                if in_json and brace_count == 0:
                    # Complete JSON object found
                    json_str = ''.join(current_json)
                    try:
                        obj = json.loads(json_str)
                        json_objects.append(obj)
                    except json.JSONDecodeError:
                        pass  # Skip malformed JSON
                    in_json = False
                    current_json = []
            elif in_json:
                current_json.append(char)

        return json_objects

    @staticmethod
    def _extract_activity_text(json_object: Dict[str, Any]) -> Optional[str]:
        """
        Extract text content from specific Cline activity types.

        Looks for:
        - Activities with "say":"completion_result"
        - Activities with "ask":"plan_mode_respond"

        Args:
            json_object (Dict[str, Any]): Parsed JSON object from Cline output

        Returns:
            Optional[str]: The "text" property if matching activity, None otherwise
        """
        if not isinstance(json_object, dict):
            return None

        # Check for "say":"completion_result"
        if json_object.get('say') == 'completion_result':
            text = json_object.get('text')
            if text:
                return text

        # Check for "ask":"plan_mode_respond"
        if json_object.get('ask') == 'plan_mode_respond':
            text = json_object.get('text')
            if text:
                return text

        return None

    @staticmethod
    def _get_activity_type(json_object: Dict[str, Any]) -> str:
        """
        Determine the activity type from a JSON object.

        Args:
            json_object (Dict[str, Any]): Parsed JSON object

        Returns:
            str: Activity type name
        """
        if not isinstance(json_object, dict):
            return "unknown"

        if 'say' in json_object:
            return f"say_{json_object.get('say', 'unknown')}"
        if 'ask' in json_object:
            return f"ask_{json_object.get('ask', 'unknown')}"
        if 'event' in json_object:
            return f"event_{json_object.get('event', 'unknown')}"

        return "unknown_activity"
