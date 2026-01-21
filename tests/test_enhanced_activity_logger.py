"""
Tests for Enhanced ActivityLogger with source attribution and timestamp envelopes.
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest
from oneshot.providers.activity_logger import ActivityLogger


class TestEnhancedActivityLogger:
    """Test suite for enhanced ActivityLogger functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_base = os.path.join(self.temp_dir, "test-session")

    def teardown_method(self):
        """Clean up test environment."""
        # Remove all files in temp directory
        for file in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, file))
            except OSError:
                pass
        os.rmdir(self.temp_dir)

    def test_enhanced_activity_logging(self):
        """Test enhanced activity logging with source attribution."""
        logger = ActivityLogger(self.session_base)

        # Log agent activity
        success = logger.log_enhanced_activity(
            data={"type": "response", "text": "Test response"},
            activity_source="agent",
            executor="worker",
            additional_metadata={"test": "value"}
        )
        assert success

        # Log system activity
        success = logger.log_enhanced_activity(
            data={"type": "checkpoint", "message": "Task started"},
            activity_source="oneshot",
            executor="system",
            is_heartbeat=True
        )
        assert success

        logger.finalize_log()

        # Verify log file was created and contains expected content
        log_file = f"{self.session_base}-log.json"
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2

            # Parse first entry (agent activity)
            entry1 = json.loads(lines[0])
            assert entry1["activity_source"] == "agent"
            assert entry1["executor"] == "worker"
            assert entry1["data"]["type"] == "response"
            assert entry1["metadata"]["test"] == "value"
            assert "timestamp" in entry1

            # Parse second entry (system activity)
            entry2 = json.loads(lines[1])
            assert entry2["activity_source"] == "oneshot"
            assert entry2["executor"] == "system"
            assert entry2["is_heartbeat"] is True
            assert entry2["data"]["type"] == "checkpoint"

    def test_prompt_logging(self):
        """Test prompt logging functionality."""
        logger = ActivityLogger(self.session_base)

        prompt = "What is the capital of France?"
        success = logger.log_prompt(
            prompt=prompt,
            prompt_type="worker_prompt",
            target_executor="claude",
            additional_metadata={"iteration": 1}
        )
        assert success

        logger.finalize_log()

        # Verify log content
        log_file = f"{self.session_base}-log.json"
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1

            entry = json.loads(lines[0])
            assert entry["activity_source"] == "oneshot"
            assert entry["executor"] == "claude"
            assert entry["data"]["type"] == "prompt"
            assert entry["data"]["content"] == prompt
            assert entry["metadata"]["prompt_type"] == "worker_prompt"
            assert entry["metadata"]["target_executor"] == "claude"
            assert entry["metadata"]["prompt_length"] == len(prompt)
            assert entry["metadata"]["iteration"] == 1

    def test_executor_interaction_logging(self):
        """Test executor interaction logging."""
        logger = ActivityLogger(self.session_base)

        # Log request start
        success = logger.log_executor_interaction(
            interaction_type="request_start",
            executor_name="direct",
            request_data={"model": "llama", "prompt": "test"},
            duration_ms=150.5
        )
        assert success

        # Log request complete
        success = logger.log_executor_interaction(
            interaction_type="request_complete",
            executor_name="direct",
            response_data={"response": "Paris", "tokens": 10},
            success=True,
            duration_ms=250.0
        )
        assert success

        # Log failed request
        success = logger.log_executor_interaction(
            interaction_type="request_failed",
            executor_name="direct",
            success=False,
            additional_metadata={"error": "timeout"}
        )
        assert success

        logger.finalize_log()

        # Verify log content
        log_file = f"{self.session_base}-log.json"
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3

            # Check first entry (request_start)
            entry1 = json.loads(lines[0])
            assert entry1["activity_source"] == "oneshot"
            assert entry1["metadata"]["interaction_type"] == "request_start"
            assert entry1["metadata"]["executor_name"] == "direct"
            assert entry1["metadata"]["success"] is True
            assert entry1["metadata"]["duration_ms"] == 150.5

            # Check second entry (request_complete)
            entry2 = json.loads(lines[1])
            assert entry2["metadata"]["interaction_type"] == "request_complete"
            assert entry2["data"]["response"]["response"] == "Paris"
            assert entry2["data"]["response"]["tokens"] == 10

            # Check third entry (request_failed)
            entry3 = json.loads(lines[2])
            assert entry3["metadata"]["interaction_type"] == "request_failed"
            assert entry3["metadata"]["success"] is False
            assert entry3["metadata"]["error"] == "timeout"

    def test_auditor_analysis_logging(self):
        """Test auditor analysis logging."""
        logger = ActivityLogger(self.session_base)

        auditor_prompt = "Review this work and determine if it's complete."
        worker_output = "## Final Result\nThe capital is Paris."
        verdict = "done"

        success = logger.log_auditor_analysis(
            auditor_prompt=auditor_prompt,
            worker_output=worker_output,
            verdict=verdict,
            validation_criteria={"keywords": ["done", "retry"]}
        )
        assert success

        # Test with rejection
        success = logger.log_auditor_analysis(
            auditor_prompt="Review this incomplete work.",
            worker_output="Incomplete answer",
            verdict="retry",
            rejection_reason="Work was incomplete",
            validation_criteria={"analysis": "comprehensive"}
        )
        assert success

        logger.finalize_log()

        # Verify log content
        log_file = f"{self.session_base}-log.json"
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2

            # Check first entry (successful audit)
            entry1 = json.loads(lines[0])
            assert entry1["activity_source"] == "oneshot"
            assert entry1["executor"] == "auditor"
            assert entry1["data"]["type"] == "auditor_analysis"
            assert entry1["data"]["auditor_prompt"] == auditor_prompt
            assert entry1["data"]["worker_output"] == worker_output
            assert entry1["data"]["verdict"] == verdict
            assert entry1["metadata"]["verdict"] == verdict
            assert "rejection_reason" not in entry1["metadata"]  # Should not be present when None

            # Check second entry (rejection)
            entry2 = json.loads(lines[1])
            assert entry2["data"]["verdict"] == "retry"
            assert entry2["metadata"]["rejection_reason"] == "Work was incomplete"

    def test_backward_compatibility(self):
        """Test that enhanced logger maintains backward compatibility."""
        logger = ActivityLogger(self.session_base)

        # Test old log_json_line method still works
        json_str = '{"test": "data", "timestamp": 1234567890}'
        success = logger.log_json_line(json_str)
        assert success

        # Test enhanced logging works alongside old method
        success = logger.log_enhanced_activity(
            data={"type": "test"},
            activity_source="agent"
        )
        assert success

        logger.finalize_log()

        # Verify both entries exist
        log_file = f"{self.session_base}-log.json"
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2

    def test_malformed_enhanced_data_handling(self):
        """Test handling of malformed data in enhanced logging."""
        logger = ActivityLogger(self.session_base)

        # Test with non-serializable data (should fail gracefully)
        class NonSerializable:
            pass

        success = logger.log_enhanced_activity(
            data=NonSerializable(),
            activity_source="agent"
        )
        assert not success  # Should fail due to serialization error

        # Valid data should still work
        success = logger.log_enhanced_activity(
            data={"type": "valid"},
            activity_source="agent"
        )
        assert success

        logger.finalize_log()

        # Should only have the valid entry
        log_file = f"{self.session_base}-log.json"
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1

            entry = json.loads(lines[0])
            assert entry["data"]["type"] == "valid"

    def test_timestamp_envelope(self):
        """Test that timestamp envelopes are properly created."""
        logger = ActivityLogger(self.session_base)

        before_time = time.time()
        success = logger.log_enhanced_activity(
            data={"test": "data"},
            activity_source="agent",
            executor="worker"
        )
        after_time = time.time()

        assert success
        logger.finalize_log()

        # Verify timestamp is reasonable
        log_file = f"{self.session_base}-log.json"
        with open(log_file, 'r') as f:
            lines = f.readlines()
            entry = json.loads(lines[0])

            assert "timestamp" in entry
            timestamp = entry["timestamp"]
            assert isinstance(timestamp, (int, float))
            assert before_time <= timestamp <= after_time

    def test_source_attribution_accuracy(self):
        """Test that activity sources are correctly attributed."""
        logger = ActivityLogger(self.session_base)

        # Log various activity types with different sources
        activities = [
            ("agent", {"type": "response"}),
            ("oneshot", {"type": "system_message"}),
            ("agent", {"type": "tool_call"}),
            ("oneshot", {"type": "prompt_generation"}),
        ]

        for source, data in activities:
            success = logger.log_enhanced_activity(
                data=data,
                activity_source=source
            )
            assert success

        logger.finalize_log()

        # Verify sources
        log_file = f"{self.session_base}-log.json"
        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 4

            for i, line in enumerate(lines):
                entry = json.loads(line)
                expected_source = activities[i][0]
                assert entry["activity_source"] == expected_source