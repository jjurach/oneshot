"""
Direct executor that forwards prompts to Ollama via HTTP API.
"""

import os
from typing import Dict, Any
from .base import BaseExecutor, ExecutionResult
from .ollama_client import OllamaClient, OllamaResponse


class DirectExecutor(BaseExecutor):
    """
    Executor that forwards prompts directly to Ollama via HTTP API.

    This serves as a simple worker role executor that can answer basic queries
    and provides a foundation for future lang-graph experimentation.
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

    def run_task(self, task: str) -> ExecutionResult:
        """
        Execute a task by forwarding the prompt to Ollama.

        Args:
            task (str): The task description/prompt to execute

        Returns:
            ExecutionResult: Detailed result of the task execution
        """
        try:
            # Check connection to Ollama first
            if not self.client.check_connection():
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

            # Generate response from Ollama
            ollama_response: OllamaResponse = self.client.generate(
                model=self.model,
                prompt=task,
                stream=False  # Use non-streaming for simplicity
            )

            # Check if the response was successful
            if not ollama_response.done:
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