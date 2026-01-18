import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def suppress_logging():
    """Suppress logging from the application during tests."""
    with patch('oneshot.oneshot.VERBOSITY', -1):
        yield