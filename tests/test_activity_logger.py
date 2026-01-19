"""
Tests for ActivityLogger - pure NDJSON activity logging utility.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from oneshot.providers.activity_logger import ActivityLogger


class TestActivityLogger:
    """Test suite for ActivityLogger functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_base = os.path.join(self.temp_dir, "test_session")
        self.log_file = f"{self.session_base}-log.json"

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up any created files
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test ActivityLogger initialization."""
        logger = ActivityLogger(self.session_base)

        assert logger.session_file_base == self.session_base
        assert logger.log_file_path == self.log_file
        assert logger.file_handle is None
        assert logger.has_valid_data is False

    def test_lazy_file_creation(self):
        """Test that log file is created only when first valid data is logged."""
        logger = ActivityLogger(self.session_base)

        # File should not exist initially
        assert not os.path.exists(self.log_file)

        # Log valid JSON - file should be created
        valid_json = '{"activity": "test", "type": "example"}'
        expected_compact = '{"activity":"test","type":"example"}'
        result = logger.log_json_line(valid_json)

        assert result is True
        assert os.path.exists(self.log_file)
        assert logger.has_valid_data is True

        # Verify file contents (should be compact format)
        with open(self.log_file, 'r') as f:
            content = f.read().strip()
            assert content == expected_compact

        logger.finalize_log()

    def test_valid_json_logging(self):
        """Test logging of valid JSON objects."""
        logger = ActivityLogger(self.session_base)

        test_cases = [
            ('{"activity": "file_edit", "file": "test.py"}', '{"activity":"file_edit","file":"test.py"}'),
            ('{"activity": "command", "cmd": "ls -la"}', '{"activity":"command","cmd":"ls -la"}'),
            ('{"activity": "completion", "status": "success"}', '{"activity":"completion","status":"success"}'),
            ('{"nested": {"object": {"deep": true}}, "array": [1, 2, 3]}', '{"nested":{"object":{"deep":true}},"array":[1,2,3]}')
        ]

        for input_json, expected_compact in test_cases:
            result = logger.log_json_line(input_json)
            assert result is True

        logger.finalize_log()

        # Verify all lines were written in compact format
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == len(test_cases)
            for i, (input_json, expected_compact) in enumerate(test_cases):
                assert lines[i].strip() == expected_compact

    def test_malformed_json_discarded(self):
        """Test that malformed JSON is discarded with warnings."""
        logger = ActivityLogger(self.session_base)

        malformed_cases = [
            '{"incomplete": "missing closing brace"',
            '{"trailing": "comma",}',
            '{"invalid": json}',
            'not json at all',
            '{"unclosed": ["array", "missing"]',
            '',
        ]

        with patch('oneshot.providers.activity_logger.logger') as mock_logger:
            for json_str in malformed_cases:
                result = logger.log_json_line(json_str)
                assert result is False
                # Should have logged a warning
                mock_logger.warning.assert_called()
                # Reset mock for next iteration
                mock_logger.reset_mock()

        logger.finalize_log()

        # File should not exist since no valid data was logged
        assert not os.path.exists(self.log_file)

    def test_valid_json_after_malformed(self):
        """Test that valid JSON is logged after malformed data."""
        logger = ActivityLogger(self.session_base)

        # First log some malformed data
        with patch('oneshot.providers.activity_logger.logger') as mock_logger:
            result = logger.log_json_line('{"incomplete": "malformed"')
            assert result is False
            mock_logger.warning.assert_called()

        # Then log valid data
        valid_json = '{"activity": "success", "type": "test"}'
        with patch('oneshot.providers.activity_logger.logger') as mock_logger:
            result = logger.log_json_line(valid_json)
            assert result is True
            # Should not have logged any warning for valid JSON
            mock_logger.warning.assert_not_called()

        logger.finalize_log()

        # File should exist with the valid data
        assert os.path.exists(self.log_file)
        with open(self.log_file, 'r') as f:
            content = f.read().strip()
            assert content == '{"activity":"success","type":"test"}'

    def test_file_write_error_handling(self):
        """Test handling of file write errors."""
        logger = ActivityLogger(self.session_base)

        # Force file creation first
        valid_json = '{"test": "data"}'
        logger.log_json_line(valid_json)

        # Mock file handle to raise error on write
        with patch.object(logger.file_handle, 'write', side_effect=OSError("Write failed")):
            with patch('oneshot.providers.activity_logger.logger') as mock_logger:
                result = logger.log_json_line('{"should": "fail"}')
                assert result is False
                mock_logger.warning.assert_called_with(
                    f"Failed to write to activity log file {self.log_file}: Write failed"
                )

        logger.finalize_log()

    def test_empty_log_cleanup(self):
        """Test that empty log files are cleaned up."""
        logger = ActivityLogger(self.session_base)

        # Log some valid data first
        logger.log_json_line('{"first": "entry"}')
        assert os.path.exists(self.log_file)

        # Manually reset has_valid_data to simulate no valid data
        logger.has_valid_data = False

        logger.finalize_log()

        # File should be removed since marked as having no valid data
        assert not os.path.exists(self.log_file)

    def test_context_manager(self):
        """Test context manager functionality."""
        with ActivityLogger(self.session_base) as logger:
            logger.log_json_line('{"test": "context"}')
            assert os.path.exists(self.log_file)

        # File should still exist after context exit (since it has valid data)
        assert os.path.exists(self.log_file)

        # Verify content (compact format)
        with open(self.log_file, 'r') as f:
            assert f.read().strip() == '{"test":"context"}'

        # Clean up
        os.remove(self.log_file)

    def test_context_manager_empty_cleanup(self):
        """Test context manager cleans up empty files."""
        with ActivityLogger(self.session_base) as logger:
            # Log invalid data only
            logger.log_json_line('invalid json')
            # File might be created but should be cleaned up

        # File should not exist since no valid data
        assert not os.path.exists(self.log_file)

    def test_directory_creation(self):
        """Test automatic creation of parent directories."""
        nested_path = os.path.join(self.temp_dir, "nested", "deep", "path", "session")
        logger = ActivityLogger(nested_path)

        logger.log_json_line('{"test": "nested"}')

        expected_log = os.path.join(self.temp_dir, "nested", "deep", "path", "session-log.json")
        assert os.path.exists(expected_log)

        # Clean up
        os.remove(expected_log)
        # Remove directories
        Path(os.path.dirname(expected_log)).rmdir()
        Path(os.path.dirname(os.path.dirname(expected_log))).rmdir()
        Path(os.path.dirname(os.path.dirname(os.path.dirname(expected_log)))).rmdir()

    def test_json_formatting_consistency(self):
        """Test that logged JSON has consistent formatting."""
        logger = ActivityLogger(self.session_base)

        # Input with extra whitespace
        input_json = '{  "activity"  :  "test"  ,  "data"  :  [1,  2,  3]  }'
        expected_output = '{"activity":"test","data":[1,2,3]}'  # Compact format

        logger.log_json_line(input_json)
        logger.finalize_log()

        with open(self.log_file, 'r') as f:
            actual_output = f.read().strip()
            assert actual_output == expected_output

    def test_large_json_warning_truncation(self):
        """Test that large malformed JSON strings are truncated in warnings."""
        logger = ActivityLogger(self.session_base)

        # Create a very large malformed JSON string
        large_malformed = '{"data": "' + 'x' * 300 + '", "incomplete": '  # Missing closing

        with patch('oneshot.providers.activity_logger.logger') as mock_logger:
            result = logger.log_json_line(large_malformed)
            assert result is False

            # Check that warning was called with truncated content
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]

            # Should contain truncation indicator
            assert '...' in warning_call
            # Should not contain the full long string
            assert len(warning_call) < len(large_malformed) + 50  # Allow some buffer for message text