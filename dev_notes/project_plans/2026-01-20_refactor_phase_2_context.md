# Project Plan: Core Architecture Refactoring - Phase 2: The Context

## Overview
This phase focuses on managing the shared memory and data protocol between the Worker and Auditor. It handles the persistence of the session (`oneshot.json`) and the logic for extracting and scoring "Full Text" results from the activity stream.

## Related Documents
- `docs/streaming-and-state-management.md` (Architecture Specification)

## Objectives
- Implement `ExecutionContext` for atomic persistence.
- Implement `ResultExtractor` for parsing activity logs into "Full Text" summaries.
- Implement `PromptGenerator` for injecting context into prompts.

## Components & Code Samples

### 1. `src/oneshot/context.py`

**Concept:** Atomic persistence and typesafe access.

```python
import json
import tempfile
import os
from dataclasses import asdict

class ExecutionContext:
    def __init__(self, filepath):
        self.filepath = filepath
        self._data = self._load()

    def _load(self):
        # Load JSON, apply migrations
        pass

    def save(self):
        # Atomic write pattern
        dir_name = os.path.dirname(self.filepath)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
            json.dump(self._data, tf, indent=2)
            temp_name = tf.name
        os.replace(temp_name, self.filepath)

    def set_worker_result(self, summary: str):
        self._data['worker_result'] = summary
        self.save()
```

### 2. `src/oneshot/protocol.py`

**Concept:** Extracting "Truth" from a noisy log stream.

```python
class ResultExtractor:
    def extract_result(self, log_path: str) -> str:
        candidates = []
        with open(log_path) as f:
            for line in f:
                event = json.loads(line)
                text = self._format_event(event)
                score = self._score_text(text)
                if score > 0:
                    candidates.append((score, text))
        
        # Sort by score, pick best
        return sorted(candidates, reverse=True)[0][1]

    def _score_text(self, text: str) -> int:
        score = 0
        if "DONE" in text: score += 10
        if "{" in text and "}" in text: score += 5
        return score
```

## Checklist
- [ ] Create `src/oneshot/context.py`
- [ ] Implement `ExecutionContext` with atomic file writing
- [ ] Implement migration logic for old `oneshot.json` schemas (if needed)
- [ ] Create `src/oneshot/protocol.py`
- [ ] Implement `ResultExtractor` logic (scoring/formatting)
- [ ] Implement `PromptGenerator` class

## Test Plan: `tests/test_context.py` & `tests/test_protocol.py`

**Pattern:** File-based testing for logic.

```python
def test_atomic_write(tmp_path):
    ctx = ExecutionContext(tmp_path / "oneshot.json")
    ctx.set_worker_result("test")
    
    # Verify file exists and content is correct
    with open(tmp_path / "oneshot.json") as f:
        data = json.load(f)
    assert data['worker_result'] == "test"

def test_extractor_scoring():
    extractor = ResultExtractor()
    assert extractor._score_text("I am DONE") > extractor._score_text("Thinking...")
    assert extractor._score_text('{"status": "DONE"}') > extractor._score_text("DONE")
```

- [ ] **Create `tests/test_context.py`**
    - Verify atomic writes (no data corruption on crash).
    - Verify data persistence across load/save cycles.
- [ ] **Create `tests/test_protocol.py`**
    - **Result Extraction:**
        - Create mock `oneshot-log.json` files with various output patterns.
        - Verify Extractor picks the correct "DONE" message.
        - Verify context (leading/trailing lines) is captured.
    - **Prompt Generation:**
        - Verify Auditor prompt includes the extracted result.
        - Verify Reworker prompt includes the feedback.