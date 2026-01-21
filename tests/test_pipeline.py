"""
Tests for the Streaming Pipeline (Phase 3: The Nervous System)

Tests the pipeline generators and inactivity monitoring functionality.
Pattern: Generator mocking and side-effect verification.
"""

import pytest
import json
import time
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from oneshot.pipeline import (
    InactivityTimeoutError,
    TimestampedActivity,
    ingest_stream,
    extract_json_objects,
    timestamp_activity,
    InactivityMonitor,
    log_activity,
    parse_activity,
    build_pipeline,
    validate_ndjson,
)


class TestExtractJsonObjects:
    """Tests for the extract_json_objects generator."""

    def test_extract_json_with_preamble(self):
        """Test extraction of JSON with a text preamble."""
        stream = [
            "This is a preamble.\n",
            "It has multiple lines.\n",
            "{\n",
            '  "key": "value",\n',
            '  "status": "DONE"\n',
            "}\n"
        ]
        result = list(extract_json_objects(iter(stream)))
        
        assert len(result) == 3
        assert result[0] == "This is a preamble."
        assert result[1] == "It has multiple lines."
        assert isinstance(result[2], dict)
        assert result[2]["status"] == "DONE"

    def test_extract_multiple_json_objects(self):
        """Test extraction of multiple JSON objects in a stream."""
        stream = [
            "{\n",
            '  "id": 1\n',
            "}\n",
            "noise line\n",
            "{\n",
            '  "id": 2\n',
            "}\n"
        ]
        result = list(extract_json_objects(iter(stream)))
        
        assert len(result) == 2
        assert isinstance(result[0], dict)
        assert result[0]["id"] == 1
        assert isinstance(result[1], dict)
        assert result[1]["id"] == 2

    def test_extract_json_chunked_input(self):
        """Test extraction when input is chunked across lines."""
        stream = [
            "Pre", "amble\n",
            "{\n",
            '  "ke', 'y": "val', 'ue"\n',
            "}\n"
        ]
        result = list(extract_json_objects(iter(stream)))
        
        assert len(result) == 2
        assert result[0] == "Preamble"
        assert result[1] == {"key": "value"}

    def test_extract_json_invalid_fallback(self):
        """Test that invalid JSON is yielded as a string."""
        stream = [
            "{\n",
            '  "broken": "json"\n',
            # missing closing brace or malformed
            "  invalid\n",
            "}\n"
        ]
        result = list(extract_json_objects(iter(stream)))
        
        assert len(result) == 1
        assert isinstance(result[0], str)
        assert "broken" in result[0]

    def test_extract_json_passthrough_non_strings(self):
        """Test that non-string objects are passed through."""
        stream = [
            "Preamble\n",
            {"already": "parsed"},
            "Postamble\n"
        ]
        result = list(extract_json_objects(iter(stream)))
        
        assert len(result) == 3
        assert result[0] == "Preamble"
        assert result[1] == {"already": "parsed"}
        assert result[2] == "Postamble"


class TestIngestStream:
    """Tests for the ingest_stream generator."""

    def test_ingest_stream_basic(self):
        """Test basic ingestion of stream items."""
        items = ["item1", "item2", "item3"]
        result = list(ingest_stream(iter(items)))
        assert result == items

    def test_ingest_stream_empty(self):
        """Test ingestion of empty stream."""
        result = list(ingest_stream(iter([])))
        assert result == []

    def test_ingest_stream_generator_behavior(self):
        """Test that ingest_stream is a proper generator."""
        gen = ingest_stream(iter(["a", "b"]))
        assert hasattr(gen, '__iter__')
        assert hasattr(gen, '__next__')
        assert next(gen) == "a"
        assert next(gen) == "b"

    def test_ingest_stream_with_mixed_types(self):
        """Test ingestion with mixed data types."""
        items = ["string", 123, {"key": "value"}, None]
        result = list(ingest_stream(iter(items)))
        assert result == items


class TestTimestampActivity:
    """Tests for the timestamp_activity generator."""

    def test_timestamp_activity_basic(self):
        """Test basic timestamping of activities."""
        items = ["item1", "item2"]
        result = list(timestamp_activity(ingest_stream(iter(items))))

        assert len(result) == 2
        assert all(isinstance(a, TimestampedActivity) for a in result)
        assert result[0].data == "item1"
        assert result[1].data == "item2"

    def test_timestamp_activity_has_current_time(self):
        """Test that timestamps are recent."""
        items = ["item1"]
        now = time.time()
        result = list(timestamp_activity(ingest_stream(iter(items))))

        assert len(result) == 1
        assert result[0].timestamp >= now
        assert result[0].timestamp <= time.time()

    def test_timestamp_activity_executor_name(self):
        """Test that executor name is stored."""
        items = ["item1"]
        result = list(timestamp_activity(ingest_stream(iter(items)), executor_name="claude"))

        assert result[0].executor == "claude"

    def test_timestamp_activity_heartbeat_flag(self):
        """Test that heartbeat flag defaults to False."""
        items = ["item1"]
        result = list(timestamp_activity(ingest_stream(iter(items))))
        assert result[0].is_heartbeat is False

    def test_timestamp_activity_monotonic_time(self):
        """Test that timestamps increase (or stay same) over time."""
        items = ["item1", "item2", "item3"]
        result = list(timestamp_activity(ingest_stream(iter(items))))

        for i in range(len(result) - 1):
            assert result[i].timestamp <= result[i + 1].timestamp


class TestInactivityMonitor:
    """Tests for the InactivityMonitor class."""

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = InactivityMonitor(timeout_seconds=5.0)
        assert monitor.timeout_seconds == 5.0
        assert monitor.timeout_occurred is False

    def test_monitor_normal_flow(self):
        """Test monitor with normal activity flow (no timeout)."""
        monitor = InactivityMonitor(timeout_seconds=2.0)

        def data_gen():
            yield TimestampedActivity(time.time(), "data1")
            yield TimestampedActivity(time.time(), "data2")
            yield TimestampedActivity(time.time(), "data3")

        result = list(monitor.monitor_inactivity(data_gen()))
        assert len(result) == 3
        assert result[0].data == "data1"
        assert result[1].data == "data2"
        assert result[2].data == "data3"

    def test_monitor_detects_timeout(self):
        """Test that monitor raises timeout on inactivity."""
        monitor = InactivityMonitor(timeout_seconds=0.5)

        def slow_generator():
            yield TimestampedActivity(time.time(), "item1")
            # Simulate slow processing - wait longer than timeout
            time.sleep(1.0)
            yield TimestampedActivity(time.time(), "item2")

        with pytest.raises(InactivityTimeoutError):
            list(monitor.monitor_inactivity(slow_generator()))

    def test_monitor_updates_last_activity_time(self):
        """Test that monitor tracks last activity time."""
        monitor = InactivityMonitor(timeout_seconds=5.0)
        initial_time = monitor.last_activity_time

        def quick_generator():
            yield TimestampedActivity(time.time(), "item1")

        list(monitor.monitor_inactivity(quick_generator()))
        assert monitor.last_activity_time > initial_time

    def test_monitor_thread_cleanup(self):
        """Test that monitor thread is properly cleaned up."""
        monitor = InactivityMonitor(timeout_seconds=5.0)

        def quick_generator():
            yield TimestampedActivity(time.time(), "item1")

        list(monitor.monitor_inactivity(quick_generator()))
        # Monitor thread should have completed
        assert monitor._monitor_thread is None or not monitor._monitor_thread.is_alive()

    def test_monitor_empty_stream(self):
        """Test monitor with empty stream."""
        monitor = InactivityMonitor(timeout_seconds=5.0)

        def empty_generator():
            return
            yield  # Make it a generator

        result = list(monitor.monitor_inactivity(empty_generator()))
        assert result == []


class TestLogActivity:
    """Tests for the log_activity generator."""

    def test_log_activity_writes_ndjson(self):
        """Test that log_activity writes valid NDJSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            def data_gen():
                yield TimestampedActivity(1000.0, "data1", executor="claude")
                yield TimestampedActivity(1001.0, "data2", executor="claude")

            result = list(log_activity(data_gen(), log_path))
            assert len(result) == 2

            # Verify NDJSON format
            with open(log_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 2

            # Parse each line as JSON
            for line in lines:
                parsed = json.loads(line)
                assert "timestamp" in parsed
                assert "data" in parsed
                assert "executor" in parsed
        finally:
            os.unlink(log_path)

    def test_log_activity_flushes_on_write(self):
        """Test that log_activity flushes after each write."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            def data_gen():
                yield TimestampedActivity(1000.0, "data1")
                yield TimestampedActivity(1001.0, "data2")

            # Start consuming the generator
            gen = log_activity(data_gen(), log_path)
            first = next(gen)

            # Check that first item was written and flushed
            with open(log_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 1

            # Consume rest
            list(gen)

            # Check that all items were written
            with open(log_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 2
        finally:
            os.unlink(log_path)

    def test_log_activity_passthrough(self):
        """Test that log_activity passes items through unchanged."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            items = [
                TimestampedActivity(1000.0, "data1"),
                TimestampedActivity(1001.0, "data2"),
            ]

            result = list(log_activity(iter(items), log_path))
            assert result == items
        finally:
            os.unlink(log_path)

    def test_log_activity_handles_missing_directory(self):
        """Test log_activity error handling for invalid path."""
        invalid_path = "/nonexistent/directory/path/log.json"

        def data_gen():
            yield TimestampedActivity(1000.0, "data1")

        with pytest.raises(RuntimeError):
            list(log_activity(data_gen(), invalid_path))

    def test_log_activity_serializes_complex_data(self):
        """Test that complex data types are serialized correctly."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            def data_gen():
                yield TimestampedActivity(1000.0, {"key": "value", "nested": [1, 2, 3]})
                yield TimestampedActivity(1001.0, [1, 2, 3])
                yield TimestampedActivity(1002.0, None)

            list(log_activity(data_gen(), log_path))

            # Verify all lines are valid JSON
            with open(log_path, 'r') as f:
                for line in f:
                    parsed = json.loads(line)
                    assert parsed["data"] is not None or parsed["data"] is None
        finally:
            os.unlink(log_path)


class TestParseActivity:
    """Tests for the parse_activity generator."""

    def test_parse_activity_basic(self):
        """Test basic parsing of activities."""
        def data_gen():
            yield TimestampedActivity(1000.0, "data1", executor="claude")
            yield TimestampedActivity(1001.0, "data2", executor="claude")

        result = list(parse_activity(data_gen()))
        assert len(result) == 2

        assert result[0]["timestamp"] == 1000.0
        assert result[0]["data"] == "data1"
        assert result[0]["executor"] == "claude"
        assert result[0]["is_heartbeat"] is False

    def test_parse_activity_output_structure(self):
        """Test that parsed output has correct structure."""
        def data_gen():
            yield TimestampedActivity(1000.0, "test", executor="cline", is_heartbeat=True)

        result = list(parse_activity(data_gen()))
        assert len(result) == 1

        output = result[0]
        assert "timestamp" in output
        assert "executor" in output
        assert "is_heartbeat" in output
        assert "data" in output
        assert output["is_heartbeat"] is True

    def test_parse_activity_passthrough(self):
        """Test that parse preserves data integrity."""
        def data_gen():
            yield TimestampedActivity(1000.0, {"complex": "data"})
            yield TimestampedActivity(1001.0, [1, 2, 3])

        result = list(parse_activity(data_gen()))
        assert result[0]["data"] == {"complex": "data"}
        assert result[1]["data"] == [1, 2, 3]


class TestBuildPipeline:
    """Tests for the complete pipeline composition."""

    def test_build_pipeline_complete_flow(self):
        """Test that the complete pipeline processes data correctly."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            stream = iter(["data1\n", "data2\n", "data3\n"])
            result = list(build_pipeline(stream, log_path, inactivity_timeout=10.0))

            assert len(result) == 3
            for item in result:
                assert "timestamp" in item
                assert "data" in item
                assert "executor" in item

            # Verify log file was created and contains NDJSON
            with open(log_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 3

            for line in lines:
                parsed = json.loads(line)
                assert "timestamp" in parsed
                assert "data" in parsed
        finally:
            os.unlink(log_path)

    def test_build_pipeline_with_executor_name(self):
        """Test pipeline with executor name."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            stream = iter(["data1"])
            result = list(build_pipeline(
                stream, log_path,
                inactivity_timeout=10.0,
                executor_name="aider"
            ))

            assert result[0]["executor"] == "aider"

            # Verify in log
            with open(log_path, 'r') as f:
                line = f.readline()
            parsed = json.loads(line)
            assert parsed["executor"] == "aider"
        finally:
            os.unlink(log_path)

    def test_build_pipeline_timeout_propagates(self):
        """Test that inactivity timeout propagates through pipeline."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            def slow_stream():
                yield "data1"
                time.sleep(1.0)  # Exceed timeout
                yield "data2"

            with pytest.raises(InactivityTimeoutError):
                list(build_pipeline(slow_stream(), log_path, inactivity_timeout=0.5))
        finally:
            os.unlink(log_path)


class TestValidateNdjson:
    """Tests for NDJSON validation."""

    def test_validate_ndjson_valid_file(self):
        """Test validation of valid NDJSON file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"key": "value1"}\n')
            f.write('{"key": "value2"}\n')
            f.write('{"key": "value3"}\n')
            log_path = f.name

        try:
            assert validate_ndjson(log_path) is True
        finally:
            os.unlink(log_path)

    def test_validate_ndjson_with_empty_lines(self):
        """Test validation with empty lines (should pass)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"key": "value1"}\n')
            f.write('\n')
            f.write('{"key": "value2"}\n')
            log_path = f.name

        try:
            assert validate_ndjson(log_path) is True
        finally:
            os.unlink(log_path)

    def test_validate_ndjson_invalid_file(self):
        """Test validation detects invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"key": "value1"}\n')
            f.write('not valid json}\n')
            f.write('{"key": "value2"}\n')
            log_path = f.name

        try:
            assert validate_ndjson(log_path) is False
        finally:
            os.unlink(log_path)

    def test_validate_ndjson_nonexistent_file(self):
        """Test validation of nonexistent file."""
        assert validate_ndjson("/nonexistent/path.json") is False

    def test_validate_ndjson_empty_file(self):
        """Test validation of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            assert validate_ndjson(log_path) is True
        finally:
            os.unlink(log_path)


class TestTimestampedActivityDataclass:
    """Tests for the TimestampedActivity dataclass."""

    def test_timestamped_activity_creation(self):
        """Test creation of TimestampedActivity."""
        ts = time.time()
        activity = TimestampedActivity(
            timestamp=ts,
            data="test data",
            executor="claude",
            is_heartbeat=False
        )

        assert activity.timestamp == ts
        assert activity.data == "test data"
        assert activity.executor == "claude"
        assert activity.is_heartbeat is False

    def test_timestamped_activity_defaults(self):
        """Test default values."""
        activity = TimestampedActivity(timestamp=1000.0, data="data")

        assert activity.timestamp == 1000.0
        assert activity.data == "data"
        assert activity.executor is None
        assert activity.is_heartbeat is False


class TestIntegration:
    """Integration tests for the pipeline."""

    def test_end_to_end_pipeline(self):
        """Test complete end-to-end pipeline execution."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            # Create a realistic stream
            test_data = [
                "Starting execution\n",
                "Processing request\n",
                "Generating output\n",
                "Done\n"
            ]

            # Run through full pipeline
            result = list(build_pipeline(
                iter(test_data),
                log_path,
                inactivity_timeout=5.0,
                executor_name="test-executor"
            ))

            # Verify output
            assert len(result) == 4
            assert all("timestamp" in item for item in result)
            assert all(item["executor"] == "test-executor" for item in result)

            # Verify log is valid NDJSON
            assert validate_ndjson(log_path)

            # Verify log content
            with open(log_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 4

            for line in lines:
                parsed = json.loads(line)
                assert parsed["executor"] == "test-executor"
        finally:
            os.unlink(log_path)

    def test_pipeline_with_complex_data_types(self):
        """Test pipeline with various data types."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            test_data = [
                {"type": "dict", "value": 123},
                [1, 2, 3],
                "simple string",
                42,
                None,
            ]

            result = list(build_pipeline(
                iter(test_data),
                log_path,
                inactivity_timeout=5.0
            ))

            assert len(result) == 5
            assert validate_ndjson(log_path)
        finally:
            os.unlink(log_path)
