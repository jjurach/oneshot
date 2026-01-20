import os
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseExecutor, ExecutionResult

class AiderExecutor(BaseExecutor):
    """
    Executor for Aider, providing task execution through the Aider CLI.

    Aider is an AI-powered coding assistant that makes edits directly to files
    and creates git commits for its changes.
    """

    def __init__(self, git_dir: str = None, model: str = "ollama_chat/llama-pro"):
        """
        Initialize the AiderExecutor.

        Args:
            git_dir (str, optional): Directory for git operations.
                                     Defaults to current working directory.
            model (str, optional): Model specification for Aider.
                                   Defaults to "ollama_chat/llama-pro".
        """
        self.git_dir = git_dir or os.getcwd()
        self.model = model
        # Ensure aider can find the git directory
        os.chdir(self.git_dir)

    def get_provider_name(self) -> str:
        """
        Get the executor type identifier.

        Returns:
            str: "aider"
        """
        return "aider"

    def get_provider_metadata(self) -> Dict[str, Any]:
        """
        Get Aider-specific configuration metadata.

        Returns:
            Dict[str, Any]: Metadata including type, capabilities, constraints
        """
        return {
            "type": "aider",
            "name": "Aider",
            "description": "AI-powered coding assistant that edits code and creates commits",
            "output_format": "text",
            "supports_model_selection": True,
            "captures_git_commits": True,
            "requires_pty": False,
            "model": self.model,
            "timeout_seconds": 300,
            "flags": ["--message", "--model", "--editor-model", "--architect", "--edit-format", "--yes-always", "--no-stream", "--exit"]
        }

    def should_capture_git_commit(self) -> bool:
        """
        Aider creates git commits for its changes.

        Returns:
            bool: True
        """
        return True

    def build_command(self, prompt: str, model: Optional[str] = None) -> List[str]:
        """
        Build Aider CLI command for executing a task.

        Aider command format:
        aider --message "<prompt>" --model <model> --editor-model <model> --architect --edit-format whole --yes-always --no-stream --exit

        Args:
            prompt (str): The task prompt to send to Aider
            model (Optional[str]): Model specification (overrides instance model)

        Returns:
            List[str]: Command and arguments for subprocess execution
        """
        # Use provided model or fall back to instance model
        effective_model = model or self.model

        cmd = [
            "aider",
            "--message", prompt,
            "--model", effective_model,
            "--editor-model", effective_model,
            "--architect",  # Use architect mode for complex tasks
            "--edit-format", "whole",  # Edit entire files
            "--yes-always",  # Auto-approve all changes
            "--no-stream",  # Non-streaming mode for better output capture
            "--exit"  # Exit after completion
        ]
        return cmd

    def parse_streaming_activity(self, raw_output: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse Aider's output into structured results.

        Aider outputs its activity and creates git commits. This method extracts
        the commit hash and other meaningful information from the output.

        Args:
            raw_output (str): Raw output from Aider CLI

        Returns:
            Tuple[str, Dict[str, Any]]: (stdout_summary, auditor_details)
        """
        # Strip ANSI color codes
        clean_output = self._strip_ansi_colors(raw_output)

        # Extract git commit hash
        commit_hash_match = re.search(r'Committed: ([0-9a-f]{40})', clean_output)
        git_commit_hash = commit_hash_match.group(1) if commit_hash_match else None

        # Count file modifications mentioned in output
        file_edits = len(re.findall(r'(Edited|Created|Modified)', clean_output))

        # Prepare auditor details
        auditor_details = {
            "executor_type": "aider",
            "git_commit_hash": git_commit_hash,
            "file_edits": file_edits,
            "raw_output_length": len(raw_output)
        }

        return clean_output, auditor_details

    def run_task(self, task: str) -> ExecutionResult:
        """
        Execute a task using Aider CLI.

        Args:
            task (str): The task description to execute

        Returns:
            ExecutionResult: Detailed result of the task execution
        """
        try:
            # Use build_command to construct the command
            cmd = self.build_command(task)

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

            # Parse output using parse_streaming_activity
            clean_output, auditor_details = self.parse_streaming_activity(output)

            # Extract git commit hash from auditor details
            git_commit_hash = auditor_details.get('git_commit_hash')

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
                    'git_dir': self.git_dir,
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