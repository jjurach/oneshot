"""Tests for core oneshot functionality (run_oneshot and async variants)."""

import pytest
import asyncio
from unittest.mock import patch, mock_open
from pathlib import Path
import tempfile
from oneshot.oneshot import run_oneshot


class TestRunOneshot:
    """Test synchronous oneshot execution."""

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.count_iterations')
    def test_run_oneshot_success_on_first_iteration(self, mock_count, mock_call):
        """Test successful completion on first iteration."""
        mock_count.return_value = 0
        mock_call.side_effect = [
            "worker output",
            '{"verdict": "DONE", "reason": "Success"}'
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            success = run_oneshot(
                "test task",
                max_iterations=3,
                working_directory=tmpdir
            )
            assert success is True

    @patch('oneshot.oneshot.call_executor')
    @patch('oneshot.oneshot.count_iterations')
    def test_run_oneshot_max_iterations_reached(self, mock_count, mock_call):
        """Test max iterations reached."""
        mock_count.return_value = 0

        # Always return REITERATE verdict
        mock_call.side_effect = [
            "worker output 1",
            '{"verdict": "REITERATE", "reason": "Try again"}',
            "worker output 2",
            '{"verdict": "REITERATE", "reason": "Try again"}',
            "worker output 3",
            '{"verdict": "REITERATE", "reason": "Try again"}',
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            success = run_oneshot(
                "test task",
                max_iterations=3,
                working_directory=tmpdir
            )
            assert success is False


class TestAsyncOneshot:
    """Test async oneshot functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_run_oneshot_async_success(self):
        """Test successful async oneshot execution."""
        from oneshot.oneshot import run_oneshot_async

        with patch('oneshot.oneshot.call_executor_async') as mock_call:
            # Mock successful worker and auditor responses
            mock_call.side_effect = [
                "worker output",
                '{"verdict": "DONE", "reason": "Success"}'
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                success = await run_oneshot_async(
                    "test task",
                    max_iterations=3,
                    working_directory=tmpdir,
                    executor="cline"
                )

                assert success is True

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_run_oneshot_async_max_iterations(self):
        """Test async oneshot reaching max iterations."""
        from oneshot.oneshot import run_oneshot_async

        with patch('oneshot.oneshot.call_executor_async') as mock_call:
            # Mock responses that always reiterate
            responses = []
            for i in range(6):
                if i % 2 == 0:
                    responses.append(f"worker output {i//2 + 1}")
                else:
                    responses.append('{"verdict": "REITERATE", "reason": "Try again"}')

            mock_call.side_effect = responses

            with tempfile.TemporaryDirectory() as tmpdir:
                success = await run_oneshot_async(
                    "test task",
                    max_iterations=3,
                    working_directory=tmpdir,
                    executor="cline"
                )

                assert success is False
