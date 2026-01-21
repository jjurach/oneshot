#!/usr/bin/env python3
"""
Provider abstraction layer for oneshot.

Exports executor implementations and related utilities. The legacy provider pattern
(ExecutorProvider, DirectProvider) has been retired in favor of direct use of the
BaseExecutor-based executors through the OnehotEngine orchestrator.
"""

from typing import Optional
from dataclasses import dataclass, field

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
# LEGACY PROVIDER API (Backwards Compatibility)
# ============================================================================

@dataclass
class ProviderConfig:
    """Legacy provider configuration for backwards compatibility."""
    provider_type: str = 'executor'
    executor: Optional[str] = None
    model: Optional[str] = None
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 30
    output_format: Optional[str] = None
    approval_mode: Optional[str] = None
    # Additional fields for flexibility
    kwargs: dict = field(default_factory=dict)


def create_provider(config: ProviderConfig):
    """
    Legacy provider factory for backwards compatibility.

    Creates an executor instance from a ProviderConfig.
    """
    if config.provider_type == 'executor':
        return create_executor(
            executor_type=config.executor,
            model=config.model,
            timeout=config.timeout,
            output_format=config.output_format,
            approval_mode=config.approval_mode,
            **config.kwargs
        )
    elif config.provider_type == 'direct':
        from .direct_executor import DirectExecutor
        return DirectExecutor(
            endpoint=config.endpoint,
            api_key=config.api_key,
            model=config.model,
            timeout=config.timeout
        )
    else:
        raise ValueError(f"Unknown provider type: {config.provider_type}")


# Legacy Provider classes for backwards compatibility
class Provider:
    """Legacy Provider base class for backwards compatibility."""
    def __init__(self, config: ProviderConfig = None):
        self.config = config or ProviderConfig()

    def execute(self, prompt: str, **kwargs):
        """Execute a prompt using the provider."""
        raise NotImplementedError()


class ExecutorProvider(Provider):
    """Legacy ExecutorProvider for backwards compatibility."""
    def __init__(self, executor_type: str = 'claude', model: Optional[str] = None):
        self.executor_type = executor_type
        self.model = model
        config = ProviderConfig(
            provider_type='executor',
            executor=executor_type,
            model=model
        )
        super().__init__(config)
        self.executor = create_executor(executor_type, model)

    def execute(self, prompt: str, **kwargs):
        """Execute a prompt using the executor."""
        try:
            if hasattr(self.executor, 'run_task'):
                result = self.executor.run_task(prompt, **kwargs)
            else:
                result = self.executor.execute(prompt, **kwargs)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}


class DirectProvider(Provider):
    """Legacy DirectProvider for backwards compatibility."""
    def __init__(self, endpoint: str, model: Optional[str] = None, api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        config = ProviderConfig(
            provider_type='direct',
            endpoint=endpoint,
            model=model,
            api_key=api_key
        )
        super().__init__(config)
        self.executor = DirectExecutor(
            endpoint=endpoint,
            model=model,
            api_key=api_key
        )

    def execute(self, prompt: str, **kwargs):
        """Execute a prompt using the direct API."""
        try:
            if hasattr(self.executor, 'run_task'):
                result = self.executor.run_task(prompt, **kwargs)
            else:
                result = self.executor.execute(prompt, **kwargs)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}


def create_executor_provider(executor_type: str = 'claude', model: Optional[str] = None) -> ExecutorProvider:
    """
    Legacy factory function to create an ExecutorProvider.
    """
    return ExecutorProvider(executor_type, model)


def create_direct_provider(endpoint: str, model: Optional[str] = None, api_key: Optional[str] = None) -> DirectProvider:
    """
    Legacy factory function to create a DirectProvider.
    """
    return DirectProvider(endpoint, model, api_key)


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
    'run_command',
    'map_api_keys',
    # Legacy provider API
    'ProviderConfig',
    'create_provider',
    'Provider',
    'ExecutorProvider',
    'DirectProvider',
    'create_executor_provider',
    'create_direct_provider'
]
