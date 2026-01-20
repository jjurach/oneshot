import os
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseExecutor, ExecutionResult

class GeminiCLIExecutor(BaseExecutor):
    """
    Executor for Gemini CLI, providing task execution through the Gemini CLI.

    Gemini outputs action/observation/error patterns which are filtered and parsed
    to extract meaningful activity information.
    """

    def __init__(self, working_dir: str = None, output_format: str = "json", approval_mode: str = "yolo"):
        """
        Initialize the GeminiCLIExecutor.

        Args:
            working_dir (str, optional): Working directory for task execution.
                                         Defaults to current working directory.
            output_format (str): Output format - "json" or "stream-json". Defaults to "json".
            approval_mode (str): Approval mode - "normal" or "yolo". Defaults to "yolo".
        """
        self.working_dir = working_dir or os.getcwd()
        self.output_format = output_format
        self.approval_mode = approval_mode
        # Ensure consistent working directory
        os.chdir(self.working_dir)

    def get_provider_name(self) -> str:
        """
        Get the executor type identifier.

        Returns:
            str: "gemini"
        """
        return "gemini"

    def get_provider_metadata(self) -> Dict[str, Any]:
        """
        Get Gemini-specific configuration metadata.

        Returns:
            Dict[str, Any]: Metadata including type, capabilities, constraints
        """
        return {
            "type": "gemini",
            "name": "Gemini CLI",
            "description": "Google Gemini CLI agent for autonomous tasks",
            "output_format": self.output_format,
            "supports_model_selection": False,
            "captures_git_commits": False,
            "approval_mode": self.approval_mode,
            "working_dir": self.working_dir,
            "timeout_seconds": 300,
            "flags": ["--prompt", f"--output-format {self.output_format}"]
        }

    def should_capture_git_commit(self) -> bool:
        """
        Gemini does not capture git commits.

        Returns:
            bool: False
        """
        return False

    def build_command(self, prompt: str, model: Optional[str] = None) -> List[str]:
        """
        Build Gemini CLI command for executing a task.

        Gemini command format:
        gemini --prompt "<prompt>" --output-format json/stream-json [--yolo]

        Args:
            prompt (str): The task prompt to send to Gemini
            model (Optional[str]): Ignored for Gemini (not supported)

        Returns:
            List[str]: Command and arguments for subprocess execution
        """
        cmd = [
            "gemini",
            "--prompt", prompt
        ]

        # Add output format flag
        if self.output_format == "stream-json":
            cmd.extend(["--output-format", "stream-json"])
        elif self.output_format == "json":
            cmd.extend(["--output-format", "json"])

        # Add approval mode flag
        if self.approval_mode == "yolo":
            cmd.append("--yolo")

        return cmd

    def parse_streaming_activity(self, raw_output: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse Gemini's output into structured results.

        Gemini outputs action/observation/error patterns. This method filters
        lines containing these keywords and extracts meaningful activity.

        Args:
            raw_output (str): Raw output from Gemini CLI

        Returns:
            Tuple[str, Dict[str, Any]]: (stdout_summary, auditor_details)
        """
        # Strip ANSI color codes
        clean_output = self._strip_ansi_colors(raw_output)

        # Filter log to focus on "Action", "Observation", and "Error" steps
        filtered_lines = [
            line for line in clean_output.split('\n')
            if re.search(r'\b(Action|Observation|Error):', line)
        ]
        filtered_output = '\n'.join(filtered_lines)

        # Parse activity patterns
        actions = [line for line in filtered_lines if re.search(r'\bAction:', line)]
        observations = [line for line in filtered_lines if re.search(r'\bObservation:', line)]
        errors = [line for line in filtered_lines if re.search(r'\bError:', line)]

        # Prepare auditor details
        auditor_details = {
            "executor_type": "gemini",
            "action_count": len(actions),
            "observation_count": len(observations),
            "error_count": len(errors),
            "actions": actions,
            "observations": observations,
            "errors": errors,
            "raw_output_length": len(raw_output)
        }

        return filtered_output, auditor_details

    def run_task(self, task: str) -> ExecutionResult:
        """
        Execute a task using Gemini CLI.

        Args:
            task (str): The task description to execute

        Returns:
            ExecutionResult: Detailed result of the task execution
        """
        try:
            # Use build_command to construct the command
            cmd = self.build_command(task)

            # Run the command with merged stdout/stderr
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Capture output
            output, _ = process.communicate()

            # Parse output using parse_streaming_activity
            filtered_output, auditor_details = self.parse_streaming_activity(output)

            # Determine success based on process return code and output
            success = process.returncode == 0 and "error" not in output.lower()
            error = None

            # If command failed, capture error as error
            if not success and output.strip():
                error = output.strip()

            return ExecutionResult(
                success=success,
                output=filtered_output,
                error=error,
                metadata={
                    'provider': 'gemini_cli',
                    'working_dir': self.working_dir,
                    'auditor_details': auditor_details
                }
            )

        except Exception as e:
            # Comprehensive error handling
            return ExecutionResult(
                success=False,
                output='',
                error=str(e),
                metadata={
                    'provider': 'gemini_cli',
                    'exception_type': type(e).__name__
                }
            )

    def __repr__(self) -> str:
        """
        Provide a string representation of the GeminiCLIExecutor.

        Returns:
            str: A descriptive string of the executor
        """
        return f"GeminiCLIExecutor(working_dir={self.working_dir})"