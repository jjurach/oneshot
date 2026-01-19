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
from typing import Optional, Dict, Any
import os

# Import executors from submodules
from .base import BaseExecutor, ExecutionResult
from .aider_executor import AiderExecutor
from .gemini_executor import GeminiCLIExecutor
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

    def __post_init__(self):
        """Validate configuration."""
        if self.provider_type not in ["executor", "direct"]:
            raise ValueError(f"provider_type must be 'executor' or 'direct', got: {self.provider_type}")

        if self.provider_type == "executor":
            if not self.executor:
                raise ValueError("executor provider requires 'executor' field (claude, cline, or aider)")
            if self.executor not in ["claude", "cline", "aider"]:
                raise ValueError(f"executor must be 'claude', 'cline', or 'aider', got: {self.executor}")
            # For claude executor, model is required
            if self.executor == "claude" and not self.model:
                raise ValueError("claude executor requires 'model' field")
            # For aider executor, model is optional (aider has built-in default)
            if self.executor == "aider" and self.model:
                # Warn if model is provided, but don't error
                pass

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
    def generate(self, prompt: str) -> str:
        """Generate a response synchronously."""
        pass

    @abstractmethod
    async def generate_async(self, prompt: str) -> str:
        """Generate a response asynchronously."""
        pass


# ============================================================================
# EXECUTOR PROVIDER
# ============================================================================

class ExecutorProvider(Provider):
    """Provider that wraps subprocess executor calls (claude, cline) and aider executor."""

    def generate(self, prompt: str) -> str:
        """Call executor subprocess synchronously."""
        from oneshot.oneshot import call_executor, log_debug

        if self.config.executor == "aider":
            log_debug(f"ExecutorProvider calling aider executor")
            return self._call_aider_executor(prompt)
        else:
            log_debug(f"ExecutorProvider calling {self.config.executor} with model: {self.config.model}")
            return call_executor(
                prompt=prompt,
                model=self.config.model,
                executor=self.config.executor,
                initial_timeout=self.config.timeout,
                max_timeout=3600,  # Default max timeout
                activity_interval=30  # Default activity interval
            )

    async def generate_async(self, prompt: str) -> str:
        """Call executor subprocess asynchronously."""
        from oneshot.oneshot import call_executor_async, log_debug

        if self.config.executor == "aider":
            log_debug(f"ExecutorProvider async calling aider executor")
            return self._call_aider_executor(prompt)
        else:
            log_debug(f"ExecutorProvider async calling {self.config.executor} with model: {self.config.model}")
            return await call_executor_async(
                prompt=prompt,
                model=self.config.model,
                executor=self.config.executor,
                initial_timeout=self.config.timeout,
                max_timeout=3600,
                activity_interval=30
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

    def generate(self, prompt: str) -> str:
        """Make synchronous HTTP request to API endpoint."""
        from oneshot.oneshot import log_debug, log_verbose

        log_debug(f"DirectProvider calling {self.config.endpoint} with model: {self.config.model}")
        log_debug(f"Prompt length: {len(prompt)} chars")

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

            log_verbose(f"DirectProvider call completed, output length: {len(result)} chars")
            return result

        except self._requests.exceptions.Timeout:
            error_msg = f"Request timed out after {self.config.timeout}s"
            log_debug(f"ERROR: {error_msg}")
            return f"ERROR: {error_msg}"
        except self._requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {e}"
            log_debug(f"ERROR: {error_msg}")
            return f"ERROR: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            log_debug(f"ERROR: {error_msg}")
            return f"ERROR: {error_msg}"

    async def generate_async(self, prompt: str) -> str:
        """Make asynchronous HTTP request to API endpoint."""
        from oneshot.oneshot import log_debug, log_verbose

        log_debug(f"DirectProvider async calling {self.config.endpoint} with model: {self.config.model}")
        log_debug(f"Prompt length: {len(prompt)} chars")

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

                log_verbose(f"DirectProvider async call completed, output length: {len(result)} chars")
                return result

        except self._httpx.TimeoutException:
            error_msg = f"Request timed out after {self.config.timeout}s"
            log_debug(f"ERROR: {error_msg}")
            return f"ERROR: {error_msg}"
        except self._httpx.HTTPStatusError as e:
            error_msg = f"HTTP error: {e.response.status_code} {e.response.text}"
            log_debug(f"ERROR: {error_msg}")
            return f"ERROR: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            log_debug(f"ERROR: {error_msg}")
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
    'AiderExecutor',
    'GeminiCLIExecutor',
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