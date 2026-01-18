"""Shared test configuration and fixtures."""

import os
import sys
from pathlib import Path

# Enable test mode to prevent blocking subprocess calls
os.environ['ONESHOT_TEST_MODE'] = '1'

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
