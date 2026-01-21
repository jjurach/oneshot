"""
Tests for ExecutionContext - Atomic Persistence

Tests verify:
- Atomic file writes (no corruption on crash simulation)
- Data persistence across load/save cycles
- State transition recording
- Metadata and variable management
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from src.oneshot.context import ExecutionContext, StateHistoryEntry


class TestExecutionContextBasic:
    """Test basic ExecutionContext functionality."""

    def test_create_new_context(self, tmp_path):
        """Test creating a new context with a non-existent file."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        assert ctx.get_state() == "CREATED"
        assert ctx.get_iteration_count() == 0
        assert ctx.get_worker_result() is None
        assert ctx.get_auditor_result() is None

    def test_context_file_created_on_save(self, tmp_path):
        """Test that file is created when saving."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        assert not ctx_path.exists()
        ctx.save()
        assert ctx_path.exists()

    def test_load_existing_context(self, tmp_path):
        """Test loading an existing context from file."""
        ctx_path = tmp_path / "oneshot.json"

        # Create and save context
        ctx1 = ExecutionContext(str(ctx_path))
        ctx1.set_worker_result("test result")
        ctx1.save()

        # Load it again
        ctx2 = ExecutionContext(str(ctx_path))
        assert ctx2.get_worker_result() == "test result"

    def test_invalid_json_raises_error(self, tmp_path):
        """Test that invalid JSON file raises RuntimeError."""
        ctx_path = tmp_path / "oneshot.json"
        ctx_path.write_text("{invalid json")

        with pytest.raises(RuntimeError, match="Failed to load"):
            ExecutionContext(str(ctx_path))


class TestAtomicWrite:
    """Test atomic file writing patterns."""

    def test_atomic_write_no_corruption(self, tmp_path):
        """Test that atomic write prevents corruption on failure."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        # Make multiple writes
        for i in range(5):
            ctx.set_worker_result(f"result_{i}")

        # Verify final content
        with open(ctx_path) as f:
            data = json.load(f)
        assert data['worker_result'] == "result_4"

    def test_atomic_write_uses_temp_file(self, tmp_path):
        """Test that save uses temporary file."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        ctx.set_worker_result("test")

        # After save, only the target file should exist
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_concurrent_save_pattern(self, tmp_path):
        """Test that multiple saves don't corrupt data."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        # Simulate concurrent saves
        for i in range(10):
            ctx.set_worker_result(f"result_{i}")
            ctx.set_metadata(f"key_{i}", f"value_{i}")
            ctx.increment_iteration()

        # Verify consistency
        ctx_reload = ExecutionContext(str(ctx_path))
        assert ctx_reload.get_worker_result() == "result_9"
        assert ctx_reload.get_iteration_count() == 10
        assert ctx_reload.get_metadata("key_9") == "value_9"


class TestStateManagement:
    """Test state transition recording."""

    def test_set_state_records_history(self, tmp_path):
        """Test that set_state records transitions in history."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        ctx.set_state("WORKER_EXECUTING", pid=1234)
        ctx.set_state("AUDIT_PENDING", reason="worker_done")

        history = ctx.get_history()
        assert len(history) == 2
        assert history[0]['state'] == "WORKER_EXECUTING"
        assert history[0]['pid'] == 1234
        assert history[1]['state'] == "AUDIT_PENDING"
        assert history[1]['reason'] == "worker_done"

    def test_state_persistence(self, tmp_path):
        """Test that state changes persist across reloads."""
        ctx_path = tmp_path / "oneshot.json"

        ctx1 = ExecutionContext(str(ctx_path))
        ctx1.set_state("WORKER_EXECUTING", pid=999)
        ctx1.save()

        ctx2 = ExecutionContext(str(ctx_path))
        assert ctx2.get_state() == "WORKER_EXECUTING"
        history = ctx2.get_history()
        assert history[0]['pid'] == 999


class TestMetadataAndVariables:
    """Test metadata and variable storage."""

    def test_set_get_metadata(self, tmp_path):
        """Test metadata operations."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        ctx.set_metadata("executor", "cline")
        ctx.set_metadata("timeout", 300)

        assert ctx.get_metadata("executor") == "cline"
        assert ctx.get_metadata("timeout") == 300
        assert ctx.get_metadata("nonexistent", "default") == "default"

    def test_set_get_variables(self, tmp_path):
        """Test variable operations."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        ctx.set_variable("working_dir", "/home/user/project")
        ctx.set_variable("task_id", "task_123")

        assert ctx.get_variable("working_dir") == "/home/user/project"
        assert ctx.get_variable("task_id") == "task_123"
        assert ctx.get_variable("missing", None) is None

    def test_metadata_persistence(self, tmp_path):
        """Test that metadata persists across reloads."""
        ctx_path = tmp_path / "oneshot.json"

        ctx1 = ExecutionContext(str(ctx_path))
        ctx1.set_metadata("executor", "claude")
        ctx1.save()

        ctx2 = ExecutionContext(str(ctx_path))
        assert ctx2.get_metadata("executor") == "claude"


class TestWorkerAndAuditorResults:
    """Test worker and auditor result storage."""

    def test_set_get_worker_result(self, tmp_path):
        """Test worker result operations."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        worker_summary = "Completed task X by doing Y and Z"
        ctx.set_worker_result(worker_summary)

        assert ctx.get_worker_result() == worker_summary

    def test_set_get_auditor_result(self, tmp_path):
        """Test auditor result operations."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        auditor_summary = '{"verdict": "DONE", "feedback": null}'
        ctx.set_auditor_result(auditor_summary)

        assert ctx.get_auditor_result() == auditor_summary

    def test_results_persist(self, tmp_path):
        """Test that results persist across reloads."""
        ctx_path = tmp_path / "oneshot.json"

        ctx1 = ExecutionContext(str(ctx_path))
        ctx1.set_worker_result("Worker output")
        ctx1.set_auditor_result("Auditor output")
        ctx1.save()

        ctx2 = ExecutionContext(str(ctx_path))
        assert ctx2.get_worker_result() == "Worker output"
        assert ctx2.get_auditor_result() == "Auditor output"


class TestIterationCounter:
    """Test iteration counting."""

    def test_increment_iteration(self, tmp_path):
        """Test iteration counter increments."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))

        assert ctx.get_iteration_count() == 0
        ctx.increment_iteration()
        assert ctx.get_iteration_count() == 1
        ctx.increment_iteration()
        assert ctx.get_iteration_count() == 2

    def test_iteration_persistence(self, tmp_path):
        """Test iteration counter persists."""
        ctx_path = tmp_path / "oneshot.json"

        ctx1 = ExecutionContext(str(ctx_path))
        for _ in range(3):
            ctx1.increment_iteration()
        ctx1.save()

        ctx2 = ExecutionContext(str(ctx_path))
        assert ctx2.get_iteration_count() == 3


class TestToDict:
    """Test to_dict export."""

    def test_to_dict_returns_copy(self, tmp_path):
        """Test that to_dict returns a copy of the data."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        ctx.set_worker_result("test")
        ctx.set_metadata("key", "value")

        data = ctx.to_dict()

        # Verify it contains expected keys
        assert data['worker_result'] == "test"
        assert data['metadata']['key'] == "value"

        # Verify it's a copy (modification doesn't affect context)
        data['worker_result'] = "modified"
        assert ctx.get_worker_result() == "test"


class TestMigration:
    """Test schema migration."""

    def test_migration_adds_missing_fields(self, tmp_path):
        """Test that migration adds missing required fields."""
        ctx_path = tmp_path / "oneshot.json"

        # Create a minimal context file
        minimal_data = {"version": 1}
        with open(ctx_path, 'w') as f:
            json.dump(minimal_data, f)

        # Load it (should migrate)
        ctx = ExecutionContext(str(ctx_path))

        assert ctx.get_state() == "CREATED"
        assert ctx.get_iteration_count() == 0
        assert isinstance(ctx.get_history(), list)
        assert isinstance(ctx.to_dict()['metadata'], dict)
        assert isinstance(ctx.to_dict()['variables'], dict)
