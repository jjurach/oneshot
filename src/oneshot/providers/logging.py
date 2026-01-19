import logging
import sys
from typing import Optional, Dict, Any

class ProviderLogger:
    """
    A comprehensive logging system for autonomous executors.

    Provides structured, secure logging with error tracking and
    filtered sensitive information.
    """

    def __init__(
        self,
        name: str = 'ExecutorLogger',
        log_level: int = logging.INFO,
        log_file: Optional[str] = None
    ):
        """
        Initialize the logger.

        Args:
            name (str, optional): Logger name. Defaults to 'ExecutorLogger'.
            log_level (int, optional): Logging level. Defaults to INFO.
            log_file (str, optional): Path to log file. Defaults to None.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Optional file handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _sanitize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sanitize metadata to prevent logging of sensitive information.

        Args:
            metadata (Dict[str, Any], optional): Metadata dictionary

        Returns:
            Dict[str, Any]: Sanitized metadata
        """
        if not metadata:
            return {}

        # List of keys to remove or mask
        sensitive_keys = [
            'api_key', 'secret', 'token', 'password', 'credentials'
        ]

        return {
            k: '***REDACTED***' if any(sens in k.lower() for sens in sensitive_keys)
            else v
            for k, v in metadata.items()
        }

    def log_task_result(
        self,
        task: str,
        success: bool,
        output: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log the result of a task execution.

        Args:
            task (str): The task description
            success (bool): Whether the task was successful
            output (str): The task execution output
            error (str, optional): Error message if task failed
            metadata (Dict[str, Any], optional): Additional metadata
        """
        sanitized_metadata = self._sanitize_metadata(metadata)

        # Log the task result
        log_method = self.logger.info if success else self.logger.error
        log_method(
            f"Task Execution: {'Successful' if success else 'Failed'}\n"
            f"Task: {task}\n"
            f"Output: {output}\n"
            f"{'Error: ' + error if error else ''}\n"
            f"Metadata: {sanitized_metadata}"
        )

    def get_logger(self):
        """
        Get the underlying logging object.

        Returns:
            logging.Logger: The configured logger
        """
        return self.logger