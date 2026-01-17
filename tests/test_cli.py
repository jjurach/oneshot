"""Tests for CLI interface."""

import pytest
from unittest.mock import patch
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cli.oneshot_cli import main


class TestCLI:
    """Test CLI interface."""

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.time.sleep')
    def test_cli_calls_main_success(self, mock_sleep, mock_call):
        """Test that CLI calls the main function successfully."""
        # Mock successful responses
        worker_response = '''Output
{
  "status": "DONE",
  "result": "Success",
  "confidence": "high",
  "validation": "Good",
  "execution_proof": null
}'''
        auditor_response = '''Audit
{
  "verdict": "DONE",
  "reason": "Perfect"
}'''

        mock_call.side_effect = [worker_response, auditor_response]

        test_args = ['oneshot_cli.py', 'test prompt']
        with patch.object(sys, 'argv', test_args):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(0)

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.time.sleep')
    def test_cli_calls_main_failure(self, mock_sleep, mock_call):
        """Test that CLI exits when main fails."""
        # Mock failure responses
        worker_response = '''Output
{
  "status": "DONE"
}'''
        auditor_response = '''Audit
{
  "verdict": "REITERATE",
  "reason": "Try again"
}'''

        # Mock 5 iterations of failure (max_iterations=5)
        mock_call.side_effect = [worker_response, auditor_response] * 5

        test_args = ['oneshot_cli.py', '--max-iterations', '3', 'test prompt']
        with patch.object(sys, 'argv', test_args):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)