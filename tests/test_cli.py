"""Tests for CLI main function."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from oneshot.oneshot import main as oneshot_main


class TestMain:
    """Test CLI entry point."""

    @patch('sys.argv', ['oneshot', 'task description', '--executor', 'cline', '--worker-model', 'some-model'])
    def test_main_cline_with_model_aborts(self):
        """Test that cline with model parameter aborts."""
        with pytest.raises(SystemExit) as exc_info:
            oneshot_main()
        assert exc_info.value.code == 1

    @patch('sys.argv', ['oneshot', 'task description', '--executor', 'cline'])
    @patch('oneshot.engine.OnehotEngine.run')
    @patch('oneshot.oneshot._create_executor_instance')
    @patch('oneshot.oneshot._load_or_create_context')
    def test_main_cline_without_model_succeeds(self, mock_context, mock_executor, mock_engine_run):
        """Test cline without model succeeds."""
        # Mock the engine run to return success
        mock_engine_run.return_value = True

        # Mock executor factory
        mock_exec = MagicMock()
        mock_executor.return_value = mock_exec

        # Mock context
        mock_ctx = MagicMock()
        mock_context.return_value = mock_ctx

        with pytest.raises(SystemExit) as e:
            oneshot_main()
        assert e.value.code == 0
        mock_engine_run.assert_called_once()

    @patch('sys.argv', ['oneshot', 'task description', '--executor', 'claude', '--worker-model', 'some-model'])
    @patch('oneshot.engine.OnehotEngine.run')
    @patch('oneshot.oneshot._create_executor_instance')
    @patch('oneshot.oneshot._load_or_create_context')
    def test_main_claude_with_model_succeeds(self, mock_context, mock_executor, mock_engine_run):
        """Test claude with model succeeds."""
        # Mock the engine run to return success
        mock_engine_run.return_value = True

        # Mock executor factory
        mock_exec = MagicMock()
        mock_executor.return_value = mock_exec

        # Mock context
        mock_ctx = MagicMock()
        mock_context.return_value = mock_ctx

        with pytest.raises(SystemExit) as e:
            oneshot_main()
        assert e.value.code == 0
        mock_engine_run.assert_called_once()
