"""
Test suite for the unified executor framework.

Tests the base executor interface and all executor implementations
(Cline, Claude, Gemini, Aider, Direct).
"""

import pytest
from typing import List, Dict, Any
from oneshot.providers import (
    BaseExecutor,
    ClineExecutor,
    ClaudeExecutor,
    GeminiCLIExecutor,
    AiderExecutor,
    DirectExecutor,
    ExecutorRegistry,
    create_executor,
    get_available_executors,
    get_executor_info,
    get_all_executor_info
)


class TestBaseExecutorInterface:
    """Test that all executors implement the required interface."""

    def test_cline_executor_implements_interface(self):
        """Test ClineExecutor implements all abstract methods."""
        executor = ClineExecutor()

        # Check all abstract methods exist
        assert hasattr(executor, 'build_command')
        assert hasattr(executor, 'parse_streaming_activity')
        assert hasattr(executor, 'get_provider_name')
        assert hasattr(executor, 'get_provider_metadata')
        assert hasattr(executor, 'should_capture_git_commit')
        assert hasattr(executor, 'run_task')

        # Check methods are callable
        assert callable(executor.build_command)
        assert callable(executor.parse_streaming_activity)
        assert callable(executor.get_provider_metadata)
        assert callable(executor.should_capture_git_commit)

    def test_claude_executor_implements_interface(self):
        """Test ClaudeExecutor implements all abstract methods."""
        executor = ClaudeExecutor()

        assert hasattr(executor, 'build_command')
        assert hasattr(executor, 'parse_streaming_activity')
        assert hasattr(executor, 'get_provider_name')
        assert hasattr(executor, 'get_provider_metadata')
        assert hasattr(executor, 'should_capture_git_commit')

    def test_gemini_executor_implements_interface(self):
        """Test GeminiCLIExecutor implements all abstract methods."""
        executor = GeminiCLIExecutor()

        assert hasattr(executor, 'build_command')
        assert hasattr(executor, 'parse_streaming_activity')
        assert hasattr(executor, 'get_provider_name')
        assert hasattr(executor, 'get_provider_metadata')
        assert hasattr(executor, 'should_capture_git_commit')

    def test_aider_executor_implements_interface(self):
        """Test AiderExecutor implements all abstract methods."""
        executor = AiderExecutor()

        assert hasattr(executor, 'build_command')
        assert hasattr(executor, 'parse_streaming_activity')
        assert hasattr(executor, 'get_provider_name')
        assert hasattr(executor, 'get_provider_metadata')
        assert hasattr(executor, 'should_capture_git_commit')

    def test_direct_executor_implements_interface(self):
        """Test DirectExecutor implements all abstract methods."""
        executor = DirectExecutor()

        assert hasattr(executor, 'build_command')
        assert hasattr(executor, 'parse_streaming_activity')
        assert hasattr(executor, 'get_provider_name')
        assert hasattr(executor, 'get_provider_metadata')
        assert hasattr(executor, 'should_capture_git_commit')


class TestExecutorProviderNames:
    """Test that each executor has correct provider name."""

    def test_cline_provider_name(self):
        """Test Cline reports correct provider name."""
        executor = ClineExecutor()
        assert executor.get_provider_name() == "cline"

    def test_claude_provider_name(self):
        """Test Claude reports correct provider name."""
        executor = ClaudeExecutor()
        assert executor.get_provider_name() == "claude"

    def test_gemini_provider_name(self):
        """Test Gemini reports correct provider name."""
        executor = GeminiCLIExecutor()
        assert executor.get_provider_name() == "gemini"

    def test_aider_provider_name(self):
        """Test Aider reports correct provider name."""
        executor = AiderExecutor()
        assert executor.get_provider_name() == "aider"

    def test_direct_provider_name(self):
        """Test Direct reports correct provider name."""
        executor = DirectExecutor()
        assert executor.get_provider_name() == "direct"


class TestExecutorMetadata:
    """Test that metadata is correctly returned."""

    def test_cline_metadata(self):
        """Test Cline metadata includes required fields."""
        executor = ClineExecutor()
        metadata = executor.get_provider_metadata()

        assert metadata['type'] == 'cline'
        assert 'name' in metadata
        assert 'description' in metadata
        assert 'output_format' in metadata

    def test_claude_metadata(self):
        """Test Claude metadata includes required fields."""
        executor = ClaudeExecutor()
        metadata = executor.get_provider_metadata()

        assert metadata['type'] == 'claude'
        assert metadata['supports_model_selection'] is True

    def test_gemini_metadata(self):
        """Test Gemini metadata includes required fields."""
        executor = GeminiCLIExecutor()
        metadata = executor.get_provider_metadata()

        assert metadata['type'] == 'gemini'
        assert metadata['captures_git_commits'] is False

    def test_aider_metadata(self):
        """Test Aider metadata includes required fields."""
        executor = AiderExecutor()
        metadata = executor.get_provider_metadata()

        assert metadata['type'] == 'aider'
        assert metadata['captures_git_commits'] is True

    def test_direct_metadata(self):
        """Test Direct metadata includes required fields."""
        executor = DirectExecutor()
        metadata = executor.get_provider_metadata()

        assert metadata['type'] == 'direct'
        assert metadata['execution_method'] == 'http_api'


class TestExecutorCommitCaptures:
    """Test git commit capture indicators."""

    def test_cline_captures_commits(self):
        """Cline should capture git commits."""
        executor = ClineExecutor()
        assert executor.should_capture_git_commit() is True

    def test_claude_captures_commits(self):
        """Claude should capture git commits."""
        executor = ClaudeExecutor()
        assert executor.should_capture_git_commit() is True

    def test_gemini_does_not_capture_commits(self):
        """Gemini should not capture git commits."""
        executor = GeminiCLIExecutor()
        assert executor.should_capture_git_commit() is False

    def test_aider_captures_commits(self):
        """Aider should capture git commits."""
        executor = AiderExecutor()
        assert executor.should_capture_git_commit() is True

    def test_direct_does_not_capture_commits(self):
        """Direct should not capture git commits."""
        executor = DirectExecutor()
        assert executor.should_capture_git_commit() is False


class TestExecutorCommandConstruction:
    """Test command construction for each executor."""

    def test_cline_build_command(self):
        """Test Cline command construction."""
        executor = ClineExecutor()
        cmd = executor.build_command("fix the bug")

        assert isinstance(cmd, list)
        assert cmd[0] == 'cline'
        assert 'fix the bug' in cmd
        assert '--yolo' in cmd
        assert '--mode' in cmd
        assert 'act' in cmd

    def test_claude_build_command_with_model(self):
        """Test Claude command construction with model."""
        executor = ClaudeExecutor(model="claude-3-sonnet")
        cmd = executor.build_command("solve this problem", model="claude-3-sonnet")

        assert isinstance(cmd, list)
        assert cmd[0] == 'claude'
        assert 'solve this problem' in cmd
        assert '--model' in cmd
        assert 'claude-3-sonnet' in cmd

    def test_gemini_build_command(self):
        """Test Gemini command construction."""
        executor = GeminiCLIExecutor()
        cmd = executor.build_command("do this task")

        assert isinstance(cmd, list)
        assert cmd[0] == 'gemini'
        assert '--prompt' in cmd
        assert 'do this task' in cmd

    def test_aider_build_command(self):
        """Test Aider command construction."""
        executor = AiderExecutor()
        cmd = executor.build_command("implement feature")

        assert isinstance(cmd, list)
        assert cmd[0] == 'aider'
        assert '--message' in cmd
        assert 'implement feature' in cmd
        assert '--exit' in cmd

    def test_direct_build_command(self):
        """Test Direct command construction."""
        executor = DirectExecutor()
        cmd = executor.build_command("ask a question")

        assert isinstance(cmd, list)
        # Direct executor uses HTTP, not subprocess, so command is informational


class TestExecutorRegistry:
    """Test the executor registry functionality."""

    def test_registry_available_executors(self):
        """Test registry lists all available executors."""
        executors = get_available_executors()

        assert isinstance(executors, list)
        assert 'cline' in executors
        assert 'claude' in executors
        assert 'gemini' in executors
        assert 'aider' in executors
        assert 'direct' in executors

    def test_create_executor_from_registry(self):
        """Test creating executors through registry."""
        # Test each executor type
        cline = create_executor('cline')
        assert isinstance(cline, ClineExecutor)

        claude = create_executor('claude')
        assert isinstance(claude, ClaudeExecutor)

        gemini = create_executor('gemini')
        assert isinstance(gemini, GeminiCLIExecutor)

        aider = create_executor('aider')
        assert isinstance(aider, AiderExecutor)

        direct = create_executor('direct')
        assert isinstance(direct, DirectExecutor)

    def test_create_executor_with_kwargs(self):
        """Test creating executors with keyword arguments."""
        claude = create_executor('claude', model="claude-3-sonnet")
        assert claude.model == "claude-3-sonnet"

        direct = create_executor('direct', model="custom-model")
        assert direct.model == "custom-model"

    def test_get_executor_info(self):
        """Test retrieving executor metadata through registry."""
        info = get_executor_info('cline')

        assert isinstance(info, dict)
        assert info['type'] == 'cline'

    def test_get_all_executor_info(self):
        """Test retrieving all executor metadata."""
        all_info = get_all_executor_info()

        assert isinstance(all_info, dict)
        assert 'cline' in all_info
        assert 'claude' in all_info
        assert 'gemini' in all_info
        assert 'aider' in all_info
        assert 'direct' in all_info

    def test_registry_invalid_executor_type(self):
        """Test registry raises error for invalid executor type."""
        with pytest.raises(ValueError):
            create_executor('nonexistent')

    def test_registry_executor_registry_class(self):
        """Test ExecutorRegistry class directly."""
        # Get available executors
        executors = ExecutorRegistry.get_available_executors()
        assert len(executors) == 5

        # Create executor
        executor = ExecutorRegistry.create('cline')
        assert isinstance(executor, ClineExecutor)

        # Get executor class
        executor_class = ExecutorRegistry.get_executor_class('claude')
        assert executor_class == ClaudeExecutor


class TestExecutorActivityParsing:
    """Test activity parsing for each executor."""

    def test_cline_parse_activity(self):
        """Test Cline activity parsing."""
        executor = ClineExecutor()

        # Test with empty output
        output, details = executor.parse_streaming_activity("")
        assert isinstance(output, str)
        assert isinstance(details, dict)
        assert details['executor_type'] == 'cline'

    def test_claude_parse_activity(self):
        """Test Claude activity parsing."""
        executor = ClaudeExecutor()

        output, details = executor.parse_streaming_activity("")
        assert isinstance(output, str)
        assert isinstance(details, dict)
        assert details['executor_type'] == 'claude'

    def test_gemini_parse_activity(self):
        """Test Gemini activity parsing."""
        executor = GeminiCLIExecutor()

        output, details = executor.parse_streaming_activity("")
        assert isinstance(output, str)
        assert isinstance(details, dict)
        assert details['executor_type'] == 'gemini'

    def test_aider_parse_activity(self):
        """Test Aider activity parsing."""
        executor = AiderExecutor()

        output, details = executor.parse_streaming_activity("")
        assert isinstance(output, str)
        assert isinstance(details, dict)
        assert details['executor_type'] == 'aider'

    def test_direct_parse_activity(self):
        """Test Direct activity parsing."""
        executor = DirectExecutor()

        output, details = executor.parse_streaming_activity("")
        assert isinstance(output, str)
        assert isinstance(details, dict)
        assert details['executor_type'] == 'direct'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
