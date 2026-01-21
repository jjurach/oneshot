"""
Session Management Utilities for Oneshot CLI

Provides helper functions for finding, reading, and managing session files.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# Default session directory
DEFAULT_SESSION_DIR = Path.home() / '.oneshot' / 'sessions'


def find_latest_session(sessions_dir: Path = DEFAULT_SESSION_DIR) -> Optional[Path]:
    """
    Find the latest session file in the given directory.
    
    Supports both old (session_*.md) and new (oneshot_*.json) formats.
    
    Args:
        sessions_dir: Directory to search for sessions
        
    Returns:
        Path to the latest session file or None if none found
    """
    if not sessions_dir.exists():
        return None
        
    session_files = sorted(
        list(sessions_dir.glob("session_*.md")) +
        list(sessions_dir.glob("*oneshot*.json")),
        key=lambda p: p.name,
        reverse=True
    )
    return session_files[0] if session_files else None


def read_session_context(session_path: Path) -> Dict[str, Any]:
    """
    Read the context data from a session file.
    
    Args:
        session_path: Path to the session file
        
    Returns:
        Dictionary containing session context data
        
    Raises:
        ValueError: If file format is unsupported
        IOError: If file cannot be read
    """
    if session_path.suffix == '.json':
        with open(session_path, 'r') as f:
            return json.load(f)
    elif session_path.suffix == '.md':
        # Legacy support for markdown sessions
        # For now just return a skeleton as we migrate to JSON
        return {
            "state": "UNKNOWN",
            "version": 0,
            "filepath": str(session_path)
        }
    else:
        raise ValueError(f"Unsupported session file format: {session_path.suffix}")


def count_iterations(session_path: Path) -> int:
    """
    Count the number of iterations in a session.
    
    Args:
        session_path: Path to the session file
        
    Returns:
        Number of iterations found
    """
    try:
        data = read_session_context(session_path)
        return data.get('iteration_count', 0)
    except Exception:
        return 0


def validate_session_file(session_path: Path) -> bool:
    """
    Validate that a file is a valid session file.
    
    Args:
        session_path: Path to the session file
        
    Returns:
        True if valid, False otherwise
    """
    if not session_path.exists():
        return False
        
    try:
        data = read_session_context(session_path)
        return 'state' in data or session_path.suffix == '.md'
    except Exception:
        return False
