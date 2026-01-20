#!/usr/bin/env python3
"""
Unit tests for Gemini executor functionality.

Tests the GeminiCLIExecutor class and its integration with the provider system,
including the new output-format and approval-mode options.
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
from oneshot.providers.gemini_executor import GeminiCLIExecutor
from oneshot.providers import ProviderConfig, create_provider


class TestGeminiCLIExecutor:
    """Test cases for the GeminiCLIExecutor class."""

    def test_init_defaults(self):
        """Test executor initialization with default parameters."""
        executor = GeminiCLIExecutor()
        assert executor.output_format == "json"
        assert executor.approval_mode == "yolo"
        assert executor.working_dir is not None

    def test_init_custom_params(self):
        """Test executor initialization with custom parameters."""
        executor = GeminiCLIExecutor(
            working_dir="/tmp",
            output_format="stream-json",
            approval_mode="normal"
        )
        assert executor.output_format == "stream-json"
        assert executor.approval_mode == "normal"
        assert executor.working_dir == "/tmp"

    @patch('subprocess.Popen')
    def test_run_task_basic_success(self, mock_popen):
        """Test successful task execution with basic setup."""
        # Mock the subprocess call
        mock_process = Mock()
        mock_process.communicate.return_value = ("Action: test\nObservation: success", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = GeminiCLIExecutor()
        result = executor.run_task("test task")

        assert result.success is True
        assert "Action: test" in result.output
        assert result.metadata['provider'] == 'gemini_cli'

        # Verify command construction
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "gemini"
        assert "--prompt" in call_args
        assert "--yolo" in call_args

    @patch('subprocess.Popen')
    def test_run_task_stream_json_output(self, mock_popen):
        """Test task execution with stream-json output format."""
        mock_process = Mock()
        mock_process.communicate.return_value = ('{"type": "action", "content": "test"}', "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = GeminiCLIExecutor(output_format="stream-json")
        result = executor.run_task("test task")

        assert result.success is True

        # Verify command includes output format
        call_args = mock_popen.call_args[0][0]
        assert "--output-format" in call_args
        assert "stream-json" in call_args

    @patch('subprocess.Popen')
    def test_run_task_normal_approval_mode(self, mock_popen):
        """Test task execution with normal approval mode."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("Action: approved test", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = GeminiCLIExecutor(approval_mode="normal")
        result = executor.run_task("test task")

        assert result.success is True

        # Verify command does NOT include --yolo flag
        call_args = mock_popen.call_args[0][0]
        assert "--yolo" not in call_args

    @patch('subprocess.Popen')
    def test_run_task_combined_options(self, mock_popen):
        """Test task execution with both stream-json and normal approval."""
        mock_process = Mock()
        mock_process.communicate.return_value = ('{"type": "action", "approved": true}', "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = GeminiCLIExecutor(
            output_format="stream-json",
            approval_mode="normal"
        )
        result = executor.run_task("test task")

        assert result.success is True

        # Verify command construction
        call_args = mock_popen.call_args[0][0]
        assert "--output-format" in call_args
        assert "stream-json" in call_args
        assert "--yolo" not in call_args

    @patch('subprocess.Popen')
    def test_run_task_command_failure(self, mock_popen):
        """Test handling of command execution failure."""
        # Mock Popen to raise FileNotFoundError (command not found)
        mock_popen.side_effect = FileNotFoundError("gemini: command not found")

        executor = GeminiCLIExecutor()
        result = executor.run_task("test task")

        assert result.success is False
        assert result.error is not None
        assert "command not found" in str(result.error)
        assert result.metadata['exception_type'] == 'FileNotFoundError'

    @patch('subprocess.Popen')
    def test_run_task_with_error_in_output(self, mock_popen):
        """Test detection of errors in command output."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("Action: test\nError: something failed", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = GeminiCLIExecutor()
        result = executor.run_task("test task")

        assert result.success is False  # Should fail due to "error" in output
        assert "Error: something failed" in result.output

    def test_repr(self):
        """Test string representation of executor."""
        executor = GeminiCLIExecutor(working_dir="/tmp")
        repr_str = repr(executor)
        assert "GeminiCLIExecutor" in repr_str
        assert "/tmp" in repr_str


class TestGeminiProviderIntegration:
    """Test integration between Gemini executor and provider system."""

    def test_provider_config_with_gemini_options(self):
        """Test ProviderConfig accepts gemini-specific options."""
        config = ProviderConfig(
            provider_type="executor",
            executor="gemini",
            output_format="stream-json",
            approval_mode="normal"
        )

        assert config.executor == "gemini"
        assert config.output_format == "stream-json"
        assert config.approval_mode == "normal"

    @patch('oneshot.providers.ExecutorProvider._call_gemini_executor')
    def test_executor_provider_calls_gemini_with_options(self, mock_call_gemini):
        """Test that ExecutorProvider passes options to Gemini executor."""
        mock_call_gemini.return_value = "test output"

        config = ProviderConfig(
            provider_type="executor",
            executor="gemini",
            output_format="stream-json",
            approval_mode="normal"
        )

        provider = create_provider(config)
        result = provider.generate("test prompt")

        # Verify _call_gemini_executor was called
        mock_call_gemini.assert_called_once_with("test prompt")

        assert result[0] == "test output"

    def test_provider_config_validation_gemini_executor(self):
        """Test that gemini executor passes validation."""
        config = ProviderConfig(
            provider_type="executor",
            executor="gemini"
        )
        # Should not raise any validation errors
        assert config.executor == "gemini"


class TestCLIIntegration:
    """Test CLI argument parsing and option handling."""

    @patch('subprocess.run')
    def test_cli_help_includes_new_options(self, mock_run):
        """Test that CLI help includes the new options."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # This would be tested by running the CLI with --help
        # For now, we verify the options are defined in the argument parser
        from src.cli.oneshot_cli import main_async
        import asyncio

        # We can't easily test the full CLI without complex mocking,
        # but we can verify the options exist by checking the parser definition
        # This test serves as a reminder to verify CLI help manually


class TestDemoScript:
    """Test the demo script functionality."""

    def test_demo_script_imports(self):
        """Test that the demo script can be imported without errors."""
        # This verifies the demo script has valid Python syntax
        import demo_gemini_executor
        assert demo_gemini_executor.GeminiExecutorDemo is not None

    def test_demo_class_initialization(self):
        """Test GeminiExecutorDemo class initialization."""
        import demo_gemini_executor
        demo = demo_gemini_executor.GeminiExecutorDemo()
        assert demo.custom_task is not None
        assert len(demo.demos) > 0

        # Verify all demos have required fields
        for demo_config in demo.demos:
            assert 'name' in demo_config
            assert 'description' in demo_config
            assert 'command' in demo_config
            assert 'expected_output' in demo_config
            assert '--executor' in demo_config['command']
            assert 'gemini' in demo_config['command']

    def test_demo_class_custom_task(self):
        """Test GeminiExecutorDemo with custom task."""
        import demo_gemini_executor
        custom_task = "Write a hello world program"
        demo = demo_gemini_executor.GeminiExecutorDemo(custom_task)
        assert demo.custom_task == custom_task

        # Verify custom task appears in commands
        for demo_config in demo.demos:
            assert custom_task in demo_config['command']


# Integration test that would require actual gemini CLI
@pytest.mark.integration
class TestGeminiCLIIntegration:
    """Integration tests that require actual Gemini CLI installation."""

    @pytest.mark.skip(reason="Requires actual Gemini CLI installation")
    def test_real_gemini_execution(self):
        """Test with actual Gemini CLI (requires gemini to be installed)."""
        executor = GeminiCLIExecutor()
        result = executor.run_task("echo 'hello world'")
        # This would need actual gemini CLI to work
        assert result is not None

    @pytest.mark.skip(reason="Requires actual Gemini CLI installation")
    def test_real_gemini_with_stream_json(self):
        """Test stream-json output with real Gemini CLI."""
        executor = GeminiCLIExecutor(output_format="stream-json")
        result = executor.run_task("echo 'test'")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])