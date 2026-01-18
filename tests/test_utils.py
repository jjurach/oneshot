"""Tests for utility functions and session management."""

import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
import tempfile
from oneshot.oneshot import (
    find_latest_session,
    read_session_context,
    strip_ansi,
    count_iterations
)


class TestSessionManagement:
    """Test session file management."""

    def test_find_latest_session(self):
        """Test finding latest session file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test session files
            Path(tmpdir, "session_2023-01-01_10-00-00.md").touch()
            Path(tmpdir, "session_2023-01-01_11-00-00.md").touch()
            Path(tmpdir, "session_2023-01-01_09-00-00.md").touch()

            latest = find_latest_session(tmpdir)
            assert latest == Path(tmpdir, "session_2023-01-01_11-00-00.md")

    def test_find_latest_session_no_files(self):
        """Test when no session files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            latest = find_latest_session(tmpdir)
            assert latest is None

    def test_read_session_context(self):
        """Test reading session context."""
        mock_content = "Session context content"
        with patch('builtins.open', mock_open(read_data=mock_content)):
            with patch('oneshot.oneshot.find_latest_session') as mock_find:
                mock_find.return_value = Path("/fake/session.md")
                context = read_session_context("/fake/dir")
                assert context == mock_content

    def test_read_session_context_error(self):
        """Test handling of read errors."""
        with patch('oneshot.oneshot.find_latest_session') as mock_find:
            mock_find.return_value = None
            context = read_session_context("/fake/dir")
            assert context is None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_strip_ansi(self):
        """Test ANSI escape code stripping."""
        text_with_ansi = "\033[31mRed text\033[0m"
        clean_text = strip_ansi(text_with_ansi)
        assert clean_text == "Red text"

    def test_count_iterations(self):
        """Test iteration counting from session file."""
        session_content = """## Iteration 1
Content
## Iteration 2
Content
## Iteration 3
Content
"""
        with patch('builtins.open', mock_open(read_data=session_content)):
            count = count_iterations(Path("/fake/session.md"))
            assert count == 3

    def test_count_iterations_empty_file(self):
        """Test iteration counting with no iterations."""
        with patch('builtins.open', mock_open(read_data="")):
            count = count_iterations(Path("/fake/session.md"))
            assert count == 0
