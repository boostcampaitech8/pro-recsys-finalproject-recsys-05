from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root for subprocess-based harness tests."""
    return Path(__file__).resolve().parents[3]
