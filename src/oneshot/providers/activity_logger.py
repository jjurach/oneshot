"""
Pure NDJSON activity logging utility for diagnostic purposes.

This module provides ActivityLogger for creating diagnostic log files containing
pure NDJSON streams of raw executor activity data. Only valid JSON objects are
logged - corrupt/incomplete data is discarded with warning messages.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ActivityLogger:
    """
    Pure NDJSON logger for executor activity data.

    Creates diagnostic *-log.json files containing only valid JSON lines.
    Corrupt/incomplete data is discarded with warning messages to stderr.
    """

    def __init__(self, session_file_base: str):
        """
        Initialize activity logger.

        Args:
            session_file_base: Base path for session files (without extension)
                               Log file will be: {session_file_base}-log.json
        """
        self.session_file_base = session_file_base
        self.log_file_path = f"{session_file_base}-log.json"
        self.file_handle: Optional[object] = None
        self.has_valid_data = False

    def _ensure_file_open(self) -> bool:
        """Lazy initialization - open file on first valid activity."""
        if self.file_handle is None:
            try:
                # Create parent directories if needed
                log_path = Path(self.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                self.file_handle = open(self.log_file_path, 'w', encoding='utf-8')
                logger.debug(f"Opened activity log file: {self.log_file_path}")
                return True
            except (OSError, IOError) as e:
                logger.warning(f"Failed to open activity log file {self.log_file_path}: {e}")
                return False
        return True

    def log_json_line(self, json_str: str) -> bool:
        """
        Log a single JSON line if it's valid.

        Args:
            json_str: Raw JSON string to validate and log

        Returns:
            bool: True if logged successfully, False if validation failed or write error
        """
        # Strict JSON validation
        try:
            # Parse to ensure it's valid JSON
            json_obj = json.loads(json_str)
            # Re-serialize to ensure consistent formatting
            validated_json = json.dumps(json_obj, separators=(',', ':'))
        except (json.JSONDecodeError, TypeError) as e:
            # Log warning for discarded data
            logger.warning(f"Discarded malformed JSON: {json_str[:200]}{'...' if len(json_str) > 200 else ''} (error: {e})")
            return False

        # Ensure file is open (lazy initialization)
        if not self._ensure_file_open():
            return False

        try:
            # Write the validated JSON line
            self.file_handle.write(validated_json + '\n')
            self.file_handle.flush()  # Ensure immediate write
            self.has_valid_data = True
            return True
        except (OSError, IOError) as e:
            logger.warning(f"Failed to write to activity log file {self.log_file_path}: {e}")
            return False

    def finalize_log(self) -> None:
        """Finalize the log file and clean up resources."""
        if self.file_handle:
            try:
                self.file_handle.close()
                logger.debug(f"Closed activity log file: {self.log_file_path}")
            except (OSError, IOError) as e:
                logger.warning(f"Error closing activity log file {self.log_file_path}: {e}")
            finally:
                self.file_handle = None

        # Clean up empty log files
        if not self.has_valid_data and os.path.exists(self.log_file_path):
            try:
                os.remove(self.log_file_path)
                logger.debug(f"Removed empty activity log file: {self.log_file_path}")
            except OSError as e:
                logger.warning(f"Failed to remove empty log file {self.log_file_path}: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures proper cleanup."""
        self.finalize_log()