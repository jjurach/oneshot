"""Tests for CLI main function."""

import pytest
import sys
from unittest.mock import patch
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
    @patch('oneshot.oneshot.run_oneshot')
    def test_main_cline_without_model_succeeds(self, mock_run):
        """Test cline without model succeeds."""
        mock_run.return_value = True
        with pytest.raises(SystemExit) as e:
            oneshot_main()
        assert e.value.code == 0
        mock_run.assert_called_once()

    @patch('sys.argv', ['oneshot', 'task description', '--executor', 'claude', '--worker-model', 'some-model'])
    @patch('oneshot.oneshot.run_oneshot')
    def test_main_claude_with_model_succeeds(self, mock_run):
        """Test claude with model succeeds."""
        mock_run.return_value = True
        with pytest.raises(SystemExit) as e:
            oneshot_main()
        assert e.value.code == 0
        mock_run.assert_called_once()
