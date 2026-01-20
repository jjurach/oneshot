"""
Executor Registry - Factory and registry for all executor implementations.

This module provides a unified interface to create and manage executor instances
of all types (Cline, Claude, Gemini, Aider, Direct).
"""

from typing import Dict, Optional, List, Type
from .base import BaseExecutor
from .cline_executor import ClineExecutor
from .claude_executor import ClaudeExecutor
from .gemini_executor import GeminiCLIExecutor
from .aider_executor import AiderExecutor
from .direct_executor import DirectExecutor


class ExecutorRegistry:
    """Registry for managing executor implementations."""

    # Mapping of executor type strings to executor classes
    _REGISTRY: Dict[str, Type[BaseExecutor]] = {
        "cline": ClineExecutor,
        "claude": ClaudeExecutor,
        "gemini": GeminiCLIExecutor,
        "aider": AiderExecutor,
        "direct": DirectExecutor,
    }

    @classmethod
    def register(cls, executor_type: str, executor_class: Type[BaseExecutor]) -> None:
        """
        Register a new executor type.

        Args:
            executor_type (str): Type identifier (e.g., "cline", "claude")
            executor_class (Type[BaseExecutor]): Executor class to register

        Raises:
            ValueError: If executor_type is already registered
        """
        if executor_type in cls._REGISTRY:
            raise ValueError(f"Executor type '{executor_type}' is already registered")
        if not issubclass(executor_class, BaseExecutor):
            raise ValueError(f"Executor class must inherit from BaseExecutor")
        cls._REGISTRY[executor_type] = executor_class

    @classmethod
    def unregister(cls, executor_type: str) -> None:
        """
        Unregister an executor type.

        Args:
            executor_type (str): Type identifier to unregister

        Raises:
            ValueError: If executor_type is not registered
        """
        if executor_type not in cls._REGISTRY:
            raise ValueError(f"Executor type '{executor_type}' is not registered")
        del cls._REGISTRY[executor_type]

    @classmethod
    def create(cls, executor_type: str, **kwargs) -> BaseExecutor:
        """
        Create an executor instance.

        Args:
            executor_type (str): Type identifier (e.g., "cline", "claude")
            **kwargs: Arguments to pass to executor constructor

        Returns:
            BaseExecutor: Instance of the requested executor

        Raises:
            ValueError: If executor_type is not registered
        """
        if executor_type not in cls._REGISTRY:
            raise ValueError(
                f"Unknown executor type: '{executor_type}'. "
                f"Available executors: {', '.join(cls._REGISTRY.keys())}"
            )
        executor_class = cls._REGISTRY[executor_type]
        return executor_class(**kwargs)

    @classmethod
    def get_executor_class(cls, executor_type: str) -> Type[BaseExecutor]:
        """
        Get the executor class for a given type.

        Args:
            executor_type (str): Type identifier

        Returns:
            Type[BaseExecutor]: Executor class

        Raises:
            ValueError: If executor_type is not registered
        """
        if executor_type not in cls._REGISTRY:
            raise ValueError(f"Unknown executor type: '{executor_type}'")
        return cls._REGISTRY[executor_type]

    @classmethod
    def get_available_executors(cls) -> List[str]:
        """
        Get list of available executor types.

        Returns:
            List[str]: List of registered executor type identifiers
        """
        return list(cls._REGISTRY.keys())

    @classmethod
    def get_executor_info(cls, executor_type: str) -> Dict[str, any]:
        """
        Get metadata about an executor type.

        Args:
            executor_type (str): Type identifier

        Returns:
            Dict[str, any]: Executor metadata including name, description, capabilities

        Raises:
            ValueError: If executor_type is not registered
        """
        executor_class = cls.get_executor_class(executor_type)

        # Create a temporary instance to get metadata
        # For executors with required parameters, use defaults
        try:
            if executor_type == "claude":
                instance = executor_class(model=None)
            elif executor_type == "aider":
                instance = executor_class(git_dir=None, model="ollama_chat/llama-pro")
            elif executor_type == "direct":
                instance = executor_class()
            else:
                instance = executor_class()
        except Exception:
            # If we can't instantiate, just return basic info
            return {
                "type": executor_type,
                "class": executor_class.__name__,
                "description": executor_class.__doc__ or "No description available"
            }

        # Get metadata from instance
        try:
            metadata = instance.get_provider_metadata()
            metadata["executor_type"] = instance.get_provider_name()
            metadata["captures_git_commits"] = instance.should_capture_git_commit()
            return metadata
        except Exception:
            return {
                "type": executor_type,
                "class": executor_class.__name__,
                "description": executor_class.__doc__ or "No description available"
            }

    @classmethod
    def get_all_executor_info(cls) -> Dict[str, Dict[str, any]]:
        """
        Get metadata about all registered executors.

        Returns:
            Dict[str, Dict[str, any]]: Mapping of executor type to metadata
        """
        info = {}
        for executor_type in cls.get_available_executors():
            try:
                info[executor_type] = cls.get_executor_info(executor_type)
            except Exception as e:
                info[executor_type] = {
                    "error": str(e),
                    "type": executor_type
                }
        return info


# Convenience functions for quick access

def create_executor(executor_type: str, **kwargs) -> BaseExecutor:
    """
    Create an executor instance.

    Convenience function wrapping ExecutorRegistry.create().

    Args:
        executor_type (str): Type identifier (e.g., "cline", "claude")
        **kwargs: Arguments to pass to executor constructor

    Returns:
        BaseExecutor: Instance of the requested executor
    """
    return ExecutorRegistry.create(executor_type, **kwargs)


def get_available_executors() -> List[str]:
    """
    Get list of available executor types.

    Returns:
        List[str]: List of registered executor type identifiers
    """
    return ExecutorRegistry.get_available_executors()


def get_executor_info(executor_type: str) -> Dict[str, any]:
    """
    Get metadata about an executor type.

    Args:
        executor_type (str): Type identifier

    Returns:
        Dict[str, any]: Executor metadata
    """
    return ExecutorRegistry.get_executor_info(executor_type)


def get_all_executor_info() -> Dict[str, Dict[str, any]]:
    """
    Get metadata about all registered executors.

    Returns:
        Dict[str, Dict[str, any]]: Mapping of executor type to metadata
    """
    return ExecutorRegistry.get_all_executor_info()
