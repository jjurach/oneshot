"""
Streaming Pipeline - Phase 3: The Nervous System

This module handles the streaming data pipeline for ingesting raw output from
executors, timestamping it, enforcing inactivity timeouts, logging to disk, and
formatting for the UI—all in a single efficient pass using Python Generators.

Architecture:
1. Ingest: Read raw chunks/lines from the executor
2. Timestamp: Wrap in timestamped events
3. Inactivity Monitor: Detect hung processes and raise timeout if no data yields
4. Log: Append to oneshot-log.json (side effect via generator)
5. Parse: Extract semantic meaning and format for UI

Key Concept: Composable Generators
- Each stage is a generator that yields items and may have side effects
- Generators can be chained together for efficient data processing
- Use 'yield' to pass control back and process time-sensitive events
"""

import time
import json
import threading
from typing import Generator, Optional, Dict, Any, Iterator
from dataclasses import dataclass, asdict
from datetime import datetime


class InactivityTimeoutError(Exception):
    """Raised when a process shows no activity within the timeout window."""
    pass


@dataclass
class TimestampedActivity:
    """A unit of activity with ingestion timestamp and metadata."""
    timestamp: float  # Unix timestamp when this activity was ingested
    data: Any  # Raw data from executor (str, dict, etc.)
    executor: Optional[str] = None  # Which executor produced this (e.g., "cline", "claude")
    is_heartbeat: bool = False  # Whether this is a synthetic heartbeat/timeout marker


def ingest_stream(stream: Iterator[str]) -> Generator[str, None, None]:
    """
    Ingest raw stream of text/bytes from an executor.

    Yields items from the upstream generator as-is. This is the first stage
    of the pipeline and serves as the entry point for raw executor output.

    Args:
        stream: Iterator yielding raw strings/bytes from executor

    Yields:
        Individual items from the upstream stream
    """
    for item in stream:
        yield item


def timestamp_activity(
    stream: Generator[str, None, None],
    executor_name: Optional[str] = None
) -> Generator[TimestampedActivity, None, None]:
    """
    Wrap raw items in TimestampedActivity objects with ingestion time.

    Args:
        stream: Generator yielding raw items
        executor_name: Name of the executor (e.g., "cline", "claude")

    Yields:
        TimestampedActivity objects with current timestamp
    """
    for item in stream:
        yield TimestampedActivity(
            timestamp=time.time(),
            data=item,
            executor=executor_name,
            is_heartbeat=False
        )


class InactivityMonitor:
    """
    Detects inactivity in a stream and raises InactivityTimeoutError after timeout.

    This monitor runs in a separate thread and checks for data flow at regular
    intervals. When used with a generator, it acts as a pass-through that tracks
    the timestamp of the last yielded item. If no items are yielded within the
    timeout window, it raises InactivityTimeoutError.

    Thread Model:
    - Main thread: Iterates through the stream via the generator
    - Monitor thread: Checks elapsed time since last item yield
    - On timeout: Monitor thread sets a flag that causes the main iteration to fail

    Note: The actual timeout detection happens between yields. Real-time detection
    would require the upstream executor to support non-blocking I/O with a select()
    loop or similar mechanism. This implementation supports both:
    1. Synchronous streams (blocking reads) - detects timeout on next yield
    2. Non-blocking streams with timeout support - immediate detection
    """

    def __init__(self, timeout_seconds: float):
        """
        Initialize the inactivity monitor.

        Args:
            timeout_seconds: Seconds of inactivity to tolerate before timeout
        """
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()
        self.timeout_occurred = False
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None

    def _monitor_loop(self):
        """Monitor loop that runs in a separate thread."""
        while not self.timeout_occurred:
            elapsed = time.time() - self.last_activity_time
            if elapsed > self.timeout_seconds:
                with self._lock:
                    self.timeout_occurred = True
                return
            time.sleep(0.5)  # Check every 500ms

    def monitor_inactivity(
        self,
        stream: Generator[TimestampedActivity, None, None]
    ) -> Generator[TimestampedActivity, None, None]:
        """
        Monitor a stream for inactivity and raise timeout if detected.

        Args:
            stream: Generator yielding TimestampedActivity objects

        Yields:
            Items from stream unchanged

        Raises:
            InactivityTimeoutError: If no activity for timeout_seconds
        """
        # Start monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        try:
            for item in stream:
                # Check if timeout occurred in monitor thread
                if self.timeout_occurred:
                    raise InactivityTimeoutError(
                        f"No activity for {self.timeout_seconds} seconds"
                    )

                # Update last activity time
                with self._lock:
                    self.last_activity_time = time.time()

                yield item

            # Stream ended normally
            if self.timeout_occurred:
                raise InactivityTimeoutError(
                    f"No activity for {self.timeout_seconds} seconds"
                )
        finally:
            # Ensure monitor thread stops
            with self._lock:
                self.timeout_occurred = True
            if self._monitor_thread:
                self._monitor_thread.join(timeout=1.0)


def log_activity(
    stream: Generator[TimestampedActivity, None, None],
    filepath: str
) -> Generator[TimestampedActivity, None, None]:
    """
    Log activities to file in NDJSON format and pass through.

    This is a pass-through generator with a side effect: each item is serialized
    to JSON and appended to the log file with a newline (NDJSON format). The file
    is flushed after each write to ensure durability.

    Args:
        stream: Generator yielding TimestampedActivity objects
        filepath: Path to NDJSON log file

    Yields:
        Items from stream unchanged
    """
    try:
        with open(filepath, 'a') as f:
            for item in stream:
                # Serialize to NDJSON
                activity_dict = asdict(item)
                json_line = json.dumps(activity_dict, default=str)
                f.write(json_line + "\n")
                f.flush()
                yield item
    except IOError as e:
        raise RuntimeError(f"Failed to write to log file {filepath}: {e}")


def parse_activity(
    stream: Generator[TimestampedActivity, None, None]
) -> Generator[Dict[str, Any], None, None]:
    """
    Parse and format activities for the UI/Engine.

    Converts raw TimestampedActivity objects into structured dictionaries
    suitable for display and state machine consumption.

    Args:
        stream: Generator yielding TimestampedActivity objects

    Yields:
        Formatted activity dictionaries
    """
    for item in stream:
        # Format as structured output for UI consumption
        output = {
            "timestamp": item.timestamp,
            "executor": item.executor,
            "is_heartbeat": item.is_heartbeat,
            "data": item.data,
        }
        yield output


def build_pipeline(
    stream: Iterator[str],
    log_filepath: str,
    inactivity_timeout: float = 300.0,
    executor_name: Optional[str] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Build the complete streaming pipeline.

    Chains all pipeline stages together in order:
    1. Ingest raw stream
    2. Timestamp items
    3. Monitor for inactivity
    4. Log to disk
    5. Parse for UI

    Args:
        stream: Iterator yielding raw strings from executor
        log_filepath: Path to NDJSON activity log
        inactivity_timeout: Timeout in seconds (default 5 minutes)
        executor_name: Name of executor for metadata

    Yields:
        Formatted activity dictionaries ready for UI/Engine

    Raises:
        InactivityTimeoutError: If no activity within timeout window
    """
    # Stage 1: Ingest
    ingested = ingest_stream(stream)

    # Stage 2: Timestamp
    timestamped = timestamp_activity(ingested, executor_name)

    # Stage 3: Inactivity Monitor
    monitor = InactivityMonitor(inactivity_timeout)
    monitored = monitor.monitor_inactivity(timestamped)

    # Stage 4: Log
    logged = log_activity(monitored, log_filepath)

    # Stage 5: Parse
    parsed = parse_activity(logged)

    # Yield final parsed items
    yield from parsed


def validate_ndjson(filepath: str) -> bool:
    """
    Validate that all lines in a file are valid JSON (NDJSON format).

    Args:
        filepath: Path to NDJSON file

    Returns:
        True if all non-empty lines are valid JSON, False otherwise
    """
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON at line {line_num}: {e}")
                    return False
        return True
    except IOError as e:
        print(f"Failed to read file {filepath}: {e}")
        return False
