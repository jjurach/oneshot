#!/usr/bin/env python3
"""
Provider abstraction layer for oneshot.

Exports executor implementations and related utilities.
"""

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
]