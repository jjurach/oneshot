"""
Direct executor that forwards prompts to Ollama via HTTP API.
"""

import os
import time
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple, Generator
from .base import BaseExecutor, ExecutionResult, RecoveryResult
from .ollama_client import OllamaClient, OllamaResponse


class DirectExecutor(BaseExecutor):
    """
    Executor that forwards prompts directly to Ollama via HTTP API.

    This serves as a simple worker role executor that can answer basic queries
    and provides a foundation for future lang-graph experimentation.

    Note: This executor uses HTTP API instead of subprocess, so build_command
    is not applicable.
    """

    def __init__(self, model: str = "llama-pro:latest", base_url: str = "http://localhost:11434", timeout: int = 300):
        """
        Initialize the DirectExecutor.

        Args:
            model (str): Ollama model name (default: llama-pro:latest)
            base_url (str): Ollama API base URL (default: http://localhost:11434)
            timeout (int): Request timeout in seconds (default: 300)
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.client = OllamaClient(base_url=base_url, timeout=timeout)

    def get_provider_name(self) -> str:
        """
        Get the executor type identifier.

        Returns:
            str: "direct"
        """
        return "direct"

    def get_provider_metadata(self) -> Dict[str, Any]:
        """
        Get Direct-specific configuration metadata.

        Returns:
            Dict[str, Any]: Metadata including type, capabilities, constraints
        """
        return {
            "type": "direct",
            "name": "Direct (Ollama)",
            "description": "Direct HTTP API executor for Ollama models",
            "output_format": "json",
            "supports_model_selection": True,
            "captures_git_commits": False,
            "requires_pty": False,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout,
            "execution_method": "http_api",
            "note": "API-based executor, not subprocess-based"
        }

    def should_capture_git_commit(self) -> bool:
        """
        Direct executor does not capture git commits.

        Returns:
            bool: False
        """
        return False

    @contextmanager
    def execute(self, prompt: str) -> Generator[str, None, None]:
        """
        Execute a task via Ollama HTTP API and yield the response.

        Since DirectExecutor uses HTTP API (not subprocess), there's no process to manage.
        This context manager simply yields the complete response.

        Args:
            prompt (str): The task prompt to execute

        Yields:
            str: Complete response from Ollama

        Raises:
            Exception: If connection fails or API error occurs
        """
        if not self.client.check_connection():
            raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}")

        try:
            ollama_response: OllamaResponse = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False
            )
            yield ollama_response.response
        finally:
            # No cleanup needed for HTTP API
            pass

    def recover(self, task_id: str) -> RecoveryResult:
        """
        Recover from failed Direct execution.

        Direct executor uses HTTP API with no persistent state, so recovery is a no-op.

        Args:
            task_id (str): Task identifier (unused for Direct executor)

        Returns:
            RecoveryResult: Failed recovery (no state to recover from)
        """
        return RecoveryResult(
            success=False,
            recovered_activity=[],
            verdict="No persistent state (HTTP API executor)"
        )

    def build_command(self, prompt: str, model: Optional[str] = None) -> List[str]:
        """
        Build command for Direct executor.

        Note: Direct executor uses HTTP API instead of subprocess,
        so this method is not directly used in execution.

        Args:
            prompt (str): The task prompt (informational only)
            model (Optional[str]): Optional model override

        Returns:
            List[str]: Empty list (no subprocess command used)
        """
        # Direct executor doesn't use subprocess, so command is N/A
        # This is provided for interface compliance
        return ["ollama", "api", f"--model={model or self.model}"]

    def parse_streaming_activity(self, raw_output: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse Direct executor's output (Ollama API response).

        Direct executor returns structured JSON responses from the Ollama API.
        This method formats the response for consistent handling.

        Args:
            raw_output (str): Raw output from Ollama (or structured response)

        Returns:
            Tuple[str, Dict[str, Any]]: (stdout_summary, auditor_details)
        """
        # For Direct executor, the output is already structured
        # Just prepare auditor details
        auditor_details = {
            "executor_type": "direct",
            "model": self.model,
            "base_url": self.base_url,
            "output_length": len(raw_output)
        }

        return raw_output, auditor_details

    def run_task(self, task: str, activity_logger=None) -> ExecutionResult:
        """
        Execute a task by forwarding the prompt to Ollama.

        Args:
            task (str): The task description/prompt to execute
            activity_logger: Optional ActivityLogger for enhanced logging

        Returns:
            ExecutionResult: Detailed result of the task execution
        """
        try:
            # Log the prompt if logger is available
            if activity_logger:
                activity_logger.log_prompt(
                    prompt=task,
                    prompt_type="direct_executor_task",
                    target_executor="direct",
                    additional_metadata={
                        "model": self.model,
                        "base_url": self.base_url
                    }
                )

            # Check connection to Ollama first
            if not self.client.check_connection():
                if activity_logger:
                    activity_logger.log_executor_interaction(
                        interaction_type="connection_check",
                        executor_name="direct",
                        success=False,
                        additional_metadata={
                            "error": "Cannot connect to Ollama service",
                            "base_url": self.base_url
                        }
                    )
                return ExecutionResult(
                    success=False,
                    output='',
                    error="Cannot connect to Ollama service. Please ensure Ollama is running and accessible.",
                    metadata={
                        'provider': 'direct',
                        'model': self.model,
                        'base_url': self.base_url
                    }
                )

            # Log successful connection
            if activity_logger:
                activity_logger.log_executor_interaction(
                    interaction_type="connection_check",
                    executor_name="direct",
                    success=True,
                    additional_metadata={"base_url": self.base_url}
                )

            # Record start time for duration calculation
            start_time = time.time() if activity_logger else None

            # Generate response from Ollama
            ollama_response: OllamaResponse = self.client.generate(
                model=self.model,
                prompt=task,
                stream=False  # Use non-streaming for simplicity
            )

            # Calculate duration if logging
            duration_ms = (time.time() - start_time) * 1000 if start_time else None

            # Check if the response was successful
            if not ollama_response.done:
                if activity_logger:
                    activity_logger.log_executor_interaction(
                        interaction_type="api_request",
                        executor_name="direct",
                        request_data={"model": self.model, "prompt_length": len(task)},
                        success=False,
                        duration_ms=duration_ms,
                        additional_metadata={"error": "Ollama response was incomplete"}
                    )
                return ExecutionResult(
                    success=False,
                    output='',
                    error="Ollama response was incomplete or failed",
                    metadata={
                        'provider': 'direct',
                        'model': self.model,
                        'base_url': self.base_url
                    }
                )

            # Log successful response
            if activity_logger:
                activity_logger.log_executor_interaction(
                    interaction_type="api_request",
                    executor_name="direct",
                    request_data={"model": self.model, "prompt_length": len(task)},
                    response_data={
                        "response_length": len(ollama_response.response),
                        "eval_count": ollama_response.eval_count
                    },
                    success=True,
                    duration_ms=duration_ms
                )

            # Return successful result
            return ExecutionResult(
                success=True,
                output=ollama_response.response.strip(),
                error=None,
                metadata={
                    'provider': 'direct',
                    'model': self.model,
                    'base_url': self.base_url,
                    'total_duration': ollama_response.total_duration,
                    'load_duration': ollama_response.load_duration,
                    'prompt_eval_count': ollama_response.prompt_eval_count,
                    'eval_count': ollama_response.eval_count,
                    'eval_duration': ollama_response.eval_duration
                }
            )

        except Exception as e:
            # Handle any exceptions during execution
            error_msg = f"Direct executor failed: {str(e)}"
            if activity_logger:
                activity_logger.log_executor_interaction(
                    interaction_type="api_request",
                    executor_name="direct",
                    request_data={"model": self.model, "prompt_length": len(task)},
                    success=False,
                    additional_metadata={
                        "error": error_msg,
                        "exception_type": type(e).__name__
                    }
                )
            return ExecutionResult(
                success=False,
                output='',
                error=error_msg,
                metadata={
                    'provider': 'direct',
                    'model': self.model,
                    'base_url': self.base_url,
                    'exception_type': type(e).__name__
                }
            )

    def __repr__(self) -> str:
        """
        Provide a string representation of the DirectExecutor.

        Returns:
            str: A descriptive string of the executor
        """
        return f"DirectExecutor(model={self.model}, base_url={self.base_url}, timeout={self.timeout})"