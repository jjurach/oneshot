"""Tests for core oneshot functionality (run_oneshot and async variants)."""

import pytest
import asyncio
from unittest.mock import patch, mock_open
from pathlib import Path
import tempfile
from oneshot.oneshot import run_oneshot_legacy as run_oneshot


class TestRunOneshot:
    """Test synchronous oneshot execution."""

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.count_iterations')
    @patch('builtins.print')
    def test_run_oneshot_success_on_first_iteration(self, mock_print, mock_count, mock_call):
        """Test successful completion on first iteration."""
        mock_count.return_value = 0
        mock_call.side_effect = [
            "worker output",  # First worker call, no JSON
            '{"status": "DONE", "result": "Success"}',  # Second worker call, with JSON
            '{"verdict": "DONE", "reason": "Success"}'   # Auditor call
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            success = run_oneshot(
                "test task",
                worker_model="test_worker_model",
                auditor_model="test_auditor_model",
                max_iterations=3
            )
            assert success is True

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.count_iterations')
    @patch('builtins.print')
    def test_run_oneshot_max_iterations_reached(self, mock_print, mock_count, mock_call):
        """Test max iterations reached."""
        mock_count.return_value = 0

        # Always return REITERATE verdict
        mock_call.side_effect = [
            '{"status": "DONE", "result": "Success"}',
            '{"verdict": "REITERATE", "reason": "Try again"}',
            '{"status": "DONE", "result": "Success"}',
            '{"verdict": "REITERATE", "reason": "Try again"}',
            '{"status": "DONE", "result": "Success"}',
            '{"verdict": "REITERATE", "reason": "Try again"}',
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            success = run_oneshot(
                "test task",
                worker_model="test_worker_model",
                auditor_model="test_auditor_model",
                max_iterations=3
            )
            assert success is False


class TestAsyncOneshot:
    """Test async oneshot functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    @patch('builtins.print')
    async def test_run_oneshot_async_success(self, mock_print):
        """Test successful async oneshot execution."""
        from oneshot.oneshot import run_oneshot_async_legacy as run_oneshot_async

        with patch('oneshot.oneshot.call_executor_async') as mock_call:
            # Mock successful worker and auditor responses
            mock_call.side_effect = [
                "worker output",
                '{"status": "DONE", "result": "Success"}',
                '{"verdict": "DONE", "reason": "Success"}'
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                success = await run_oneshot_async(
                    "test task",
                    worker_model="test_worker_model",
                    auditor_model="test_auditor_model",
                    max_iterations=3,
                    executor="cline"
                )

                assert success is True

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    @patch('builtins.print')
    async def test_run_oneshot_async_max_iterations(self, mock_print):
        """Test async oneshot reaching max iterations."""
        from oneshot.oneshot import run_oneshot_async_legacy as run_oneshot_async

        with patch('oneshot.oneshot.call_executor_async') as mock_call:
            # Mock responses that always reiterate
            mock_call.side_effect = [
                '{"status": "DONE", "result": "Success"}',
                '{"verdict": "REITERATE", "reason": "Try again"}',
                '{"status": "DONE", "result": "Success"}',
                '{"verdict": "REITERATE", "reason": "Try again"}',
                '{"status": "DONE", "result": "Success"}',
                '{"verdict": "REITERATE", "reason": "Try again"}',
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                success = await run_oneshot_async(
                    "test task",
                    worker_model="test_worker_model",
                    auditor_model="test_auditor_model",
                    max_iterations=3,
                    executor="cline"
                )

                assert success is False
