import os
import re
import subprocess
from typing import Dict, Any
from .base import BaseExecutor, ExecutionResult

class AiderExecutor(BaseExecutor):
    """
    Executor for Aider, providing task execution through the Aider CLI.
    """

    def __init__(self, git_dir: str = None):
        """
        Initialize the AiderExecutor.

        Args:
            git_dir (str, optional): Directory for git operations.
                                     Defaults to current working directory.
        """
        self.git_dir = git_dir or os.getcwd()
        # Ensure aider can find the git directory
        os.chdir(self.git_dir)

    def run_task(self, task: str) -> ExecutionResult:
        """
        Execute a task using Aider CLI.

        Args:
            task (str): The task description to execute

        Returns:
            ExecutionResult: Detailed result of the task execution
        """
        try:
            # Construct Aider command with specified flags
            cmd = [
                "aider",
                "--message", task,
                "--yes-always",
                "--no-stream",
                "--exit"
            ]

            # Run the command with merged stdout/stderr
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                timeout=300
            )

            output = result.stdout
            process_returncode = result.returncode

            # Strip ANSI color codes
            clean_output = self._strip_ansi_colors(output)

            # Extract git commit hash
            commit_hash_match = re.search(r'Committed: ([0-9a-f]{40})', clean_output)
            git_commit_hash = commit_hash_match.group(1) if commit_hash_match else None

            # Clean up Aider chat history
            chat_history_path = os.path.join(self.git_dir, '.aider.chat.history.md')
            if os.path.exists(chat_history_path):
                os.remove(chat_history_path)

            # Determine success based on process return code and output
            success = process_returncode == 0 and "error" not in clean_output.lower()

            return ExecutionResult(
                success=success,
                output=clean_output,
                git_commit_hash=git_commit_hash,
                metadata={
                    'provider': 'aider',
                    'git_dir': self.git_dir
                }
            )

        except Exception as e:
            # Comprehensive error handling
            return ExecutionResult(
                success=False,
                output='',
                error=str(e),
                metadata={
                    'provider': 'aider',
                    'exception_type': type(e).__name__
                }
            )

    def __repr__(self) -> str:
        """
        Provide a string representation of the AiderExecutor.

        Returns:
            str: A descriptive string of the executor
        """
        return f"AiderExecutor(git_dir={self.git_dir})"