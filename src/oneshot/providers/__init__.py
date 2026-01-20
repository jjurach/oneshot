#!/usr/bin/env python3
"""
Provider abstraction layer for oneshot.

Supports two provider types:
- executor: Subprocess-based executors (claude, cline, aider)
- direct: Direct HTTP API calls to OpenAI-compatible endpoints
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, List
import os

# Import executors from submodules
from .base import BaseExecutor, ExecutionResult
from .cline_executor import ClineExecutor
from .claude_executor import ClaudeExecutor
from .aider_executor import AiderExecutor
from .gemini_executor import GeminiCLIExecutor
from .direct_executor import DirectExecutor
from .executor_registry import ExecutorRegistry, create_executor, get_available_executors, get_executor_info, get_all_executor_info
from .ollama_client import OllamaClient
from .logging import ProviderLogger
from .utils import run_command, map_api_keys


# ============================================================================
# PROVIDER CONFIGURATION
# ============================================================================

@dataclass
class ProviderConfig:
    """Configuration for a provider with validation."""

    provider_type: str  # "executor" or "direct"
    executor: Optional[str] = None  # For executor provider: "claude", "cline", or "aider"
    model: Optional[str] = None
    endpoint: Optional[str] = None  # For direct provider
    api_key: Optional[str] = None  # Optional for local models
    timeout: int = 300
    output_format: Optional[str] = None  # "json" or "stream-json"
    approval_mode: Optional[str] = None  # "normal" or "yolo"

    def __post_init__(self):
        """Validate configuration."""
        if self.provider_type not in ["executor", "direct"]:
            raise ValueError(f"provider_type must be 'executor' or 'direct', got: {self.provider_type}")

        if self.provider_type == "executor":
            if not self.executor:
                raise ValueError("executor provider requires 'executor' field (claude, cline, aider, or gemini)")
            if self.executor not in ["claude", "cline", "aider", "gemini"]:
                raise ValueError(f"executor must be 'claude', 'cline', 'aider', or 'gemini', got: {self.executor}")
            # Claude and aider executors use their own default model selection
            # Model is optional - if not provided, executor will use its defaults

        elif self.provider_type == "direct":
            if not self.endpoint:
                raise ValueError("direct provider requires 'endpoint' field")
            if not self.model:
                raise ValueError("direct provider requires 'model' field")


# ============================================================================
# PROVIDER BASE CLASS
# ============================================================================

class Provider(ABC):
    """Base provider interface."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, activity_logger=None) -> Tuple[str, List[Any]]:
        """Generate a response synchronously."""
        pass

    @abstractmethod
    async def generate_async(self, prompt: str, activity_logger=None) -> Tuple[str, List[Any]]:
        """Generate a response asynchronously."""
        pass


# ============================================================================
# EXECUTOR PROVIDER
# ============================================================================

class ExecutorProvider(Provider):
    """Provider that wraps subprocess executor calls (claude, cline) and direct executors (aider, gemini)."""

    def generate(self, prompt: str, activity_logger=None) -> Tuple[str, List[Any]]:
        """Call executor subprocess synchronously."""
        from oneshot.oneshot import call_executor, log_debug

        if self.config.executor == "aider":
            log_debug(f"ExecutorProvider calling aider executor")
            return self._call_aider_executor(prompt), []
        elif self.config.executor == "gemini":
            log_debug(f"ExecutorProvider calling gemini executor")
            return self._call_gemini_executor(prompt), []
        else:
            log_debug(f"ExecutorProvider calling {self.config.executor} with model: {self.config.model}")
            return call_executor(
                prompt=prompt,
                model=self.config.model,
                executor=self.config.executor,
                initial_timeout=self.config.timeout,
                max_timeout=3600,  # Default max timeout
                activity_interval=30,  # Default activity interval
                activity_logger=activity_logger
            )

    async def generate_async(self, prompt: str, activity_logger=None) -> Tuple[str, List[Any]]:
        """Call executor subprocess asynchronously."""
        from oneshot.oneshot import call_executor_async, log_debug

        if self.config.executor == "aider":
            log_debug(f"ExecutorProvider async calling aider executor")
            return self._call_aider_executor(prompt), []
        elif self.config.executor == "gemini":
            log_debug(f"ExecutorProvider async calling gemini executor")
            return self._call_gemini_executor(prompt), []
        else:
            log_debug(f"ExecutorProvider async calling {self.config.executor} with model: {self.config.model}")
            return await call_executor_async(
                prompt=prompt,
                model=self.config.model,
                executor=self.config.executor,
                initial_timeout=self.config.timeout,
                max_timeout=3600,
                activity_interval=30,
                activity_logger=activity_logger
            )

    def _call_aider_executor(self, prompt: str) -> str:
        """Call the aider executor directly."""
        from oneshot.oneshot import log_debug

        try:
            # Use AiderExecutor from this package
            executor = AiderExecutor()
            result = executor.run_task(prompt)

            if result.success:
                return result.output
            else:
                error_msg = result.error or "Aider execution failed"
                return f"ERROR: {error_msg}\n\nOutput:\n{result.output}"
        except Exception as e:
            log_debug(f"Aider executor error: {e}")
            return f"ERROR: Failed to run aider executor: {e}"

    def _call_gemini_executor(self, prompt: str) -> str:
        """Call the gemini executor directly."""
        from oneshot.oneshot import log_debug

        try:
            # Use GeminiCLIExecutor from this package with config options
            executor = GeminiCLIExecutor(
                working_dir=None,  # Use default working directory
                output_format=self.config.output_format,
                approval_mode=self.config.approval_mode
            )
            result = executor.run_task(prompt)

            if result.success:
                return result.output
            else:
                error_msg = result.error or "Gemini execution failed"
                return f"ERROR: {error_msg}\n\nOutput:\n{result.output}"
        except Exception as e:
            log_debug(f"Gemini executor error: {e}")
            return f"ERROR: Failed to run gemini executor: {e}"


# ============================================================================
# DIRECT API PROVIDER
# ============================================================================

class DirectProvider(Provider):
    """Provider that makes direct HTTP calls to OpenAI-compatible APIs."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Import here to avoid import errors if dependencies not installed
        try:
            import requests
            self._requests = requests
        except ImportError:
            raise ImportError(
                "requests library is required for DirectProvider. "
                "Install it with: pip install requests"
            )

        try:
            import httpx
            self._httpx = httpx
        except ImportError:
            raise ImportError(
                "httpx library is required for async DirectProvider. "
                "Install it with: pip install httpx"
            )

    def _prepare_request(self, prompt: str) -> Dict[str, Any]:
        """Prepare the request payload."""
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        headers = {
            "Content-Type": "application/json"
        }

        # Add API key if provided
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        return payload, headers

    def _extract_response(self, response_data: Dict[str, Any]) -> str:
        """Extract text from API response."""
        try:
            # OpenAI-compatible format
            return response_data['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid API response format: {e}\nResponse: {response_data}")

    def generate(self, prompt: str, activity_logger=None) -> Tuple[str, List[Any]]:
        """Make synchronous HTTP request to API endpoint."""
        from oneshot.oneshot import log_debug, log_verbose

        log_debug(f"DirectProvider calling {self.config.endpoint} with model: {self.config.model}")
        log_debug(f"Prompt length: {len(prompt)} chars")

        # Check if this is an Ollama endpoint (localhost:11434 or similar)
        if self._is_ollama_endpoint():
            return self._call_ollama(prompt), []
        else:
            # Use OpenAI-compatible API
            return self._call_openai_compatible(prompt), []

    def _is_ollama_endpoint(self) -> bool:
        """Check if the endpoint is likely an Ollama server."""
        return "localhost:11434" in self.config.endpoint or "127.0.0.1:11434" in self.config.endpoint

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API directly."""
        from oneshot.providers.ollama_client import OllamaClient

        try:
            # Extract base URL from endpoint
            if self.config.endpoint.endswith("/v1/chat/completions"):
                base_url = self.config.endpoint.replace("/v1/chat/completions", "")
            else:
                base_url = self.config.endpoint

            client = OllamaClient(base_url=base_url, timeout=self.config.timeout)

            # Generate response
            response = client.generate(
                model=self.config.model,
                prompt=prompt,
                stream=False
            )

            if response.done:
                return response.response
            else:
                return "ERROR: Ollama response incomplete"

        except Exception as e:
            return f"ERROR: Ollama call failed: {e}"

    def _call_openai_compatible(self, prompt: str) -> str:
        """Call OpenAI-compatible API."""
        payload, headers = self._prepare_request(prompt)

        try:
            response = self._requests.post(
                self.config.endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            response_data = response.json()
            result = self._extract_response(response_data)

            return result

        except self._requests.exceptions.Timeout:
            error_msg = f"Request timed out after {self.config.timeout}s"
            return f"ERROR: {error_msg}"
        except self._requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {e}"
            return f"ERROR: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            return f"ERROR: {error_msg}"

    async def generate_async(self, prompt: str, activity_logger=None) -> Tuple[str, List[Any]]:
        """Make asynchronous HTTP request to API endpoint."""
        from oneshot.oneshot import log_debug, log_verbose

        log_debug(f"DirectProvider async calling {self.config.endpoint} with model: {self.config.model}")
        log_debug(f"Prompt length: {len(prompt)} chars")

        # Check if this is an Ollama endpoint (localhost:11434 or similar)
        if self._is_ollama_endpoint():
            return self._call_ollama(prompt), []  # Ollama client is synchronous, so just call it
        else:
            # Use OpenAI-compatible API
            return await self._call_openai_compatible_async(prompt), []

    async def _call_openai_compatible_async(self, prompt: str) -> str:
        """Call OpenAI-compatible API asynchronously."""
        payload, headers = self._prepare_request(prompt)

        try:
            async with self._httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    self.config.endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                response_data = response.json()
                result = self._extract_response(response_data)

                return result

        except self._httpx.TimeoutException:
            error_msg = f"Request timed out after {self.config.timeout}s"
            return f"ERROR: {error_msg}"
        except self._httpx.HTTPStatusError as e:
            error_msg = f"HTTP error: {e.response.status_code} {e.response.text}"
            return f"ERROR: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            return f"ERROR: {error_msg}"


# ============================================================================
# PROVIDER FACTORY
# ============================================================================

def create_provider(config: ProviderConfig) -> Provider:
    """Factory function to create the appropriate provider."""
    if config.provider_type == "executor":
        return ExecutorProvider(config)
    elif config.provider_type == "direct":
        return DirectProvider(config)
    else:
        raise ValueError(f"Unknown provider type: {config.provider_type}")


# ============================================================================
# BACKWARD COMPATIBILITY HELPERS
# ============================================================================

def create_executor_provider(executor: str, model: Optional[str], timeout: int = 300) -> Provider:
    """Helper to create an executor provider (for backward compatibility)."""
    config = ProviderConfig(
        provider_type="executor",
        executor=executor,
        model=model,
        timeout=timeout
    )
    return create_provider(config)


def create_direct_provider(endpoint: str, model: str, api_key: Optional[str] = None, timeout: int = 300) -> Provider:
    """Helper to create a direct API provider."""
    config = ProviderConfig(
        provider_type="direct",
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        timeout=timeout
    )
    return create_provider(config)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'BaseExecutor',
    'ExecutionResult',
    'ClineExecutor',
    'ClaudeExecutor',
    'AiderExecutor',
    'GeminiCLIExecutor',
    'DirectExecutor',
    'ExecutorRegistry',
    'create_executor',
    'get_available_executors',
    'get_executor_info',
    'get_all_executor_info',
    'OllamaClient',
    'ProviderLogger',
    'ProviderConfig',
    'Provider',
    'ExecutorProvider',
    'DirectProvider',
    'create_provider',
    'create_executor_provider',
    'create_direct_provider',
    'run_command',
    'map_api_keys'
]