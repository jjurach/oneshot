"""
Enhanced NDJSON activity logging utility for diagnostic purposes.

This module provides ActivityLogger for creating diagnostic log files containing
enhanced NDJSON streams of raw executor activity data with source attribution.
Supports distinguishing between agent activities and oneshot system activities.
Only valid JSON objects are logged - corrupt/incomplete data is discarded with warning messages.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class ActivityLogger:
    """
    Enhanced NDJSON logger for executor activity data with source attribution.

    Creates diagnostic *-log.json files containing enhanced JSON lines with:
    - activity_source: "agent" for external AI activity, "oneshot" for internal system activity
    - timestamp envelope wrapping for parsed JSON data
    - Support for logging prompts and executor interactions

    Only valid JSON objects are logged - corrupt/incomplete data is discarded with warning messages.
    """

    def __init__(self, session_file_base: str):
        """
        Initialize enhanced activity logger.

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

    def log_enhanced_activity(self, data: Union[str, Dict[str, Any]], activity_source: str,
                             executor: Optional[str] = None, is_heartbeat: bool = False,
                             additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log enhanced activity with source attribution and timestamp envelope.

        Args:
            data: Activity data (string or dict)
            activity_source: "agent" for external AI activity, "oneshot" for internal system activity
            executor: Executor type (worker/auditor) if applicable
            is_heartbeat: Whether this is a heartbeat/keepalive message
            additional_metadata: Extra metadata to include

        Returns:
            bool: True if logged successfully, False if validation failed or write error
        """
        # Create timestamp envelope
        timestamp = time.time()

        # Build enhanced log entry
        log_entry = {
            "timestamp": timestamp,
            "activity_source": activity_source,
            "data": data
        }

        # Add optional fields
        if executor:
            log_entry["executor"] = executor
        if is_heartbeat:
            log_entry["is_heartbeat"] = is_heartbeat
        if additional_metadata:
            log_entry["metadata"] = additional_metadata

        # Serialize to JSON
        try:
            json_str = json.dumps(log_entry, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize enhanced log entry: {e}")
            return False

        # Use existing logging method
        return self.log_json_line(json_str)

    def log_prompt(self, prompt: str, prompt_type: str, target_executor: str,
                   additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log prompt generation and transmission.

        Args:
            prompt: The prompt text being sent
            prompt_type: Type of prompt (worker_prompt/auditor_prompt/system_prompt)
            target_executor: Which executor this prompt is for
            additional_metadata: Extra metadata about the prompt

        Returns:
            bool: True if logged successfully
        """
        metadata = {
            "prompt_type": prompt_type,
            "target_executor": target_executor,
            "prompt_length": len(prompt)
        }
        if additional_metadata:
            metadata.update(additional_metadata)

        return self.log_enhanced_activity(
            data={"type": "prompt", "content": prompt},
            activity_source="oneshot",
            executor=target_executor,
            additional_metadata=metadata
        )

    def log_executor_interaction(self, interaction_type: str, executor_name: str,
                                request_data: Optional[Dict[str, Any]] = None,
                                response_data: Optional[Dict[str, Any]] = None,
                                duration_ms: Optional[float] = None,
                                success: bool = True,
                                additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log executor interactions (requests/responses).

        Args:
            interaction_type: Type of interaction (request_start/request_complete/response/tool_call/etc)
            executor_name: Name of the executor
            request_data: Request payload data
            response_data: Response payload data
            duration_ms: Duration in milliseconds
            success: Whether the interaction was successful
            additional_metadata: Extra metadata to include

        Returns:
            bool: True if logged successfully
        """
        metadata = {
            "interaction_type": interaction_type,
            "executor_name": executor_name,
            "success": success
        }
        if duration_ms is not None:
            metadata["duration_ms"] = duration_ms
        if additional_metadata:
            metadata.update(additional_metadata)

        data = {"type": "executor_interaction"}
        if request_data:
            data["request"] = request_data
        if response_data:
            data["response"] = response_data

        return self.log_enhanced_activity(
            data=data,
            activity_source="oneshot",
            executor=executor_name,
            additional_metadata=metadata
        )

    def log_auditor_analysis(self, auditor_prompt: str, worker_output: str,
                           verdict: str, rejection_reason: Optional[str] = None,
                           validation_criteria: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log auditor decision-making process and validation.

        Args:
            auditor_prompt: The prompt sent to the auditor
            worker_output: The worker output being audited
            verdict: Auditor verdict (DONE/RETRY/IMPOSSIBLE)
            rejection_reason: If rejected, the reason why
            validation_criteria: Criteria used for validation

        Returns:
            bool: True if logged successfully
        """
        metadata = {
            "auditor_prompt_length": len(auditor_prompt),
            "worker_output_length": len(worker_output),
            "verdict": verdict
        }
        if rejection_reason:
            metadata["rejection_reason"] = rejection_reason
        if validation_criteria:
            metadata["validation_criteria"] = validation_criteria

        return self.log_enhanced_activity(
            data={
                "type": "auditor_analysis",
                "auditor_prompt": auditor_prompt,
                "worker_output": worker_output,
                "verdict": verdict
            },
            activity_source="oneshot",
            executor="auditor",
            additional_metadata=metadata
        )

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