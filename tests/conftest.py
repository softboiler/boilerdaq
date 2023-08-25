"""Test fixtures."""

from pathlib import Path
from shutil import copytree

import pytest

from tests import DATA, TEST_DATA


@pytest.fixture()
def _tmp_project(tmp_path: Path):
    """Produce a temporary project directory."""
    copytree(TEST_DATA, tmp_path / DATA, dirs_exist_ok=True)
