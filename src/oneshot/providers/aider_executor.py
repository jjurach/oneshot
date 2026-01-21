import os
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Generator
from .base import BaseExecutor, ExecutionResult, RecoveryResult

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
        self.process = None
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

    @contextmanager
    def execute(self, prompt: str) -> Generator[str, None, None]:
        """
        Execute a task via Aider as a subprocess and yield streaming output.

        This context manager starts the Aider process, yields a generator that
        produces streaming output, and ensures the process is terminated on exit.

        Args:
            prompt (str): The task prompt to execute

        Yields:
            Generator[str, None, None]: A generator yielding lines of output

        Raises:
            OSError: If Aider command is not found or cannot be executed
        """
        cmd = self.build_command(prompt)
        self.process = None

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                cwd=self.git_dir
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
        Recover activity from Aider's git history and logs.

        Aider creates git commits for its changes. This method examines the git log
        to recover execution information.

        Args:
            task_id (str): Task identifier (may be used for log file lookup)

        Returns:
            RecoveryResult: Result with recovered activities or failure info
        """
        try:
            # Try to get the latest git commit that Aider might have created
            try:
                git_log_result = subprocess.run(
                    ['git', 'log', '--oneline', '-20'],
                    cwd=self.git_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if git_log_result.returncode != 0:
                    return RecoveryResult(
                        success=False,
                        recovered_activity=[],
                        verdict="Git repository not accessible"
                    )

                commits = git_log_result.stdout.strip().split('\n')
                recovered = [
                    {"type": "git_commit", "hash": commit.split()[0], "message": ' '.join(commit.split()[1:])}
                    for commit in commits if commit
                ]

                # Also look for Aider log files
                log_locations = [
                    Path(self.git_dir) / ".aider.chat.history.md",
                    Path(self.git_dir) / ".aider.log",
                    Path.home() / ".aider" / "logs" / task_id / "log.txt",
                ]

                for log_path in log_locations:
                    if log_path.exists():
                        try:
                            with open(log_path, 'r') as f:
                                recovered.append({
                                    "type": "aider_log",
                                    "path": str(log_path),
                                    "content_preview": f.read(500)
                                })
                        except IOError:
                            pass

                final_verdict = "INCOMPLETE"
                if recovered:
                    final_verdict = "DONE" if any(
                        c.get('message', '').lower().find('done') != -1
                        for c in recovered
                        if isinstance(c, dict) and 'message' in c
                    ) else "INCOMPLETE"

                return RecoveryResult(
                    success=len(recovered) > 0,
                    recovered_activity=recovered,
                    verdict=final_verdict
                )

            except subprocess.TimeoutExpired:
                return RecoveryResult(
                    success=False,
                    recovered_activity=[],
                    verdict="Git command timed out"
                )

        except Exception as e:
            return RecoveryResult(
                success=False,
                recovered_activity=[],
                verdict=f"Recovery failed: {str(e)}"
            )

    def _stream_output(self, process: subprocess.Popen) -> Generator[str, None, None]:
        """
        Generator that yields lines from a subprocess stdout.

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