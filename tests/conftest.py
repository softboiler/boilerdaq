"""Test fixtures."""

from pathlib import Path
from shutil import copytree

import pytest

PARAMS = Path("params.yaml")
DATA = Path("data")
TEST_DATA = Path("tests") / DATA


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Produce a temporary project directory."""
    copytree(TEST_DATA, tmp_path / DATA, dirs_exist_ok=True)
    return tmp_path
