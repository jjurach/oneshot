import os
import re
import subprocess
from typing import Dict, Any
from .base import BaseExecutor, ExecutionResult

class GeminiCLIExecutor(BaseExecutor):
    """
    Executor for Gemini CLI, providing task execution through the Gemini CLI.
    """

    def __init__(self, working_dir: str = None):
        """
        Initialize the GeminiCLIExecutor.

        Args:
            working_dir (str, optional): Working directory for task execution.
                                         Defaults to current working directory.
        """
        self.working_dir = working_dir or os.getcwd()
        # Ensure consistent working directory
        os.chdir(self.working_dir)

    def run_task(self, task: str) -> ExecutionResult:
        """
        Execute a task using Gemini CLI.

        Args:
            task (str): The task description to execute

        Returns:
            ExecutionResult: Detailed result of the task execution
        """
        try:
            # Construct Gemini CLI command with specified flags
            cmd = [
                "gemini",
                "--prompt", f'"{task}"',
                "--yolo"
            ]

            # Run the command with merged stdout/stderr
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Capture output
            output, _ = process.communicate()

            # Strip ANSI color codes
            clean_output = self._strip_ansi_colors(output)

            # Filter log to focus on "Action" and "Observation" steps
            filtered_output = '\n'.join([
                line for line in clean_output.split('\n')
                if re.search(r'\b(Action|Observation):', line)
            ])

            # Determine success based on process return code and output
            success = process.returncode == 0 and "error" not in clean_output.lower()

            return ExecutionResult(
                success=success,
                output=filtered_output,
                metadata={
                    'provider': 'gemini_cli',
                    'working_dir': self.working_dir
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