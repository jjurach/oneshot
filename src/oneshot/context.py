"""
Execution Context - Atomic Persistence and Type-Safe Access

This module handles the shared memory and data protocol between the Worker and Auditor.
It manages persistence of the session (oneshot.json) and provides atomic file writing
to prevent data corruption on crashes.
"""

import json
import tempfile
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class StateHistoryEntry:
    """A single entry in the state transition history."""
    state: str
    ts: float
    pid: Optional[int] = None
    reason: Optional[str] = None


@dataclass
class ExecutionContext:
    """
    Manages atomic persistence of the execution state (oneshot.json).

    Provides type-safe access to session metadata, history, and results while
    ensuring atomic writes to prevent corruption on process failure.
    """
    filepath: str
    _data: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, filepath: str):
        """Initialize the execution context, loading data if it exists."""
        self.filepath = filepath
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load JSON from file, apply migrations if needed, or create new."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                # Apply migrations if needed
                return self._migrate(data)
            except (json.JSONDecodeError, IOError) as e:
                raise RuntimeError(f"Failed to load {self.filepath}: {e}")
        else:
            # Create default new context
            return self._create_default()

    def _migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply schema migrations to loaded data if needed."""
        # Version 1: Ensure required fields exist
        version = data.get('version', 1)

        if version == 1:
            # Ensure all required fields are present
            if 'oneshot_id' not in data:
                data['oneshot_id'] = None
            if 'state' not in data:
                data['state'] = 'CREATED'
            if 'iteration_count' not in data:
                data['iteration_count'] = 0
            if 'max_iterations' not in data:
                data['max_iterations'] = 5
            if 'created_at' not in data:
                data['created_at'] = datetime.utcnow().isoformat()
            if 'updated_at' not in data:
                data['updated_at'] = datetime.utcnow().isoformat()
            if 'history' not in data:
                data['history'] = []
            if 'worker_result' not in data:
                data['worker_result'] = None
            if 'auditor_result' not in data:
                data['auditor_result'] = None
            if 'metadata' not in data:
                data['metadata'] = {}
            if 'variables' not in data:
                data['variables'] = {}

        return data

    def _create_default(self) -> Dict[str, Any]:
        """Create a new default execution context."""
        return {
            'version': 1,
            'oneshot_id': None,
            'state': 'CREATED',
            'iteration_count': 0,
            'max_iterations': 5,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'history': [],
            'worker_result': None,
            'auditor_result': None,
            'metadata': {},
            'variables': {},
        }

    def save(self) -> None:
        """
        Atomically write the current data to file.

        Uses a temporary file + rename pattern to ensure no corruption
        on process failure. This is safe across filesystems.
        """
        # Update the timestamp
        self._data['updated_at'] = datetime.utcnow().isoformat()

        # Get directory containing the target file
        dir_name = os.path.dirname(self.filepath) or '.'

        # Ensure directory exists
        os.makedirs(dir_name, exist_ok=True)

        # Write to temporary file in the same directory
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=dir_name,
                delete=False,
                suffix='.tmp',
                prefix='oneshot_'
            ) as tf:
                json.dump(self._data, tf, indent=2)
                temp_path = tf.name

            # Atomic rename (replaces target if it exists)
            os.replace(temp_path, self.filepath)
        except Exception as e:
            # Clean up temp file if rename failed
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(f"Failed to save {self.filepath}: {e}")

    def set_worker_result(self, summary: str) -> None:
        """Set the worker's result summary and persist."""
        self._data['worker_result'] = summary
        self.save()

    def get_worker_result(self) -> Optional[str]:
        """Get the stored worker result."""
        return self._data.get('worker_result')

    def set_auditor_result(self, summary: str) -> None:
        """Set the auditor's result summary and persist."""
        self._data['auditor_result'] = summary
        self.save()

    def get_auditor_result(self) -> Optional[str]:
        """Get the stored auditor result."""
        return self._data.get('auditor_result')

    def set_state(self, state: str, reason: Optional[str] = None, pid: Optional[int] = None) -> None:
        """Record a state transition with timestamp and persist."""
        self._data['state'] = state

        history_entry = {
            'state': state,
            'ts': datetime.utcnow().timestamp(),
        }
        if pid is not None:
            history_entry['pid'] = pid
        if reason is not None:
            history_entry['reason'] = reason

        self._data['history'].append(history_entry)
        self.save()

    def get_state(self) -> str:
        """Get the current state."""
        return self._data.get('state', 'CREATED')

    def get_history(self) -> List[Dict[str, Any]]:
        """Get the state transition history."""
        return self._data.get('history', [])

    def increment_iteration(self) -> None:
        """Increment the iteration counter and persist."""
        self._data['iteration_count'] = self._data.get('iteration_count', 0) + 1
        self.save()

    def get_iteration_count(self) -> int:
        """Get the current iteration count."""
        return self._data.get('iteration_count', 0)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value and persist."""
        if 'metadata' not in self._data:
            self._data['metadata'] = {}
        self._data['metadata'][key] = value
        self.save()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value."""
        return self._data.get('metadata', {}).get(key, default)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable and persist."""
        if 'variables' not in self._data:
            self._data['variables'] = {}
        self._data['variables'][key] = value
        self.save()

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable value."""
        return self._data.get('variables', {}).get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Get a copy of the entire context data."""
        return dict(self._data)
