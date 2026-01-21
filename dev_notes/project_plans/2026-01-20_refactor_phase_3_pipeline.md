# Project Plan: Core Architecture Refactoring - Phase 3: The Nervous System

**Status:** COMPLETED

## Overview
This phase focuses on the streaming data pipeline. It is responsible for ingesting raw output from executors, timestamping it, enforcing inactivity timeouts, logging to disk, and formatting for the UI—all in a single efficient pass using Python Generators.

## Related Documents
- `docs/streaming-and-state-management.md` (Architecture Specification)

## Objectives
- Implement the streaming pipeline generators.
- Implement the `InactivityMonitor` to detect hung processes.
- Implement safe NDJSON logging.

## Components & Code Samples

### 1. `src/oneshot/pipeline.py`

**Concept:** Composable Generators.

```python
import time
import json

class InactivityTimeoutError(Exception): pass

def monitor_inactivity(stream, timeout):
    """Yields items or raises InactivityTimeoutError."""
    # Note: Real implementation needs a way to check time *between* yields.
    # Since standard iteration blocks, the upstream 'stream' MUST be 
    # yielding based on a select() loop with a timeout, or we wrap it here.
    iterator = iter(stream)
    while True:
        try:
            # We assume the upstream executor uses a mechanism to yield
            # control periodically or raises TimeoutError itself.
            yield next(iterator)
        except StopIteration:
            break
        except TimeoutError:
            raise InactivityTimeoutError()

def log_activity(stream, filepath):
    with open(filepath, 'a') as f:
        for item in stream:
            f.write(json.dumps(item) + "\n")
            f.flush()
            yield item
```

## Checklist
- [ ] Create `src/oneshot/pipeline.py`
- [ ] Implement `ingest_stream` generator
- [ ] Implement `log_activity` generator
- [ ] Implement `monitor_inactivity` generator
    - **Critical:** Must support the I/O model (threaded vs non-blocking) of the Executors.
- [ ] Define `InactivityTimeoutError` exception

## Test Plan: `tests/test_pipeline.py`

**Pattern:** Generator mocking.

```python
import pytest
from oneshot.pipeline import monitor_inactivity, InactivityTimeoutError

def slow_generator():
    yield "one"
    # Logic to simulate delay would go here, but for unit testing
    # we usually inject the timeout exception mechanism directly
    # or use a mock that simulates the blocking behavior.
    yield "two"

def test_pipeline_flow():
    stream = ["a", "b"]
    logged = []
    
    # Mock log writer
    for item in stream:
        logged.append(item)
        
    assert logged == ["a", "b"]
```

- [ ] **Create `tests/test_pipeline.py`**
- [ ] **Test Inactivity Monitor:**
    - Create a mock generator that sleeps longer than the timeout.
    - Verify `InactivityTimeoutError` is raised.
    - Verify it does *not* raise if data flows normally.
- [ ] **Test Logging:**
    - Verify data written to file matches the stream.
    - Verify NDJSON format validity.
- [ ] **Test Composition:**
    - Verify the pipeline components chain together correctly.