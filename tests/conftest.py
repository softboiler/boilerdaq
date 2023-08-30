"""Test fixtures."""

from pathlib import Path

import pytest
from boilercore import catch_certain_warnings

with catch_certain_warnings():
    from boilercore.testing import tmp_workdir


@pytest.fixture(autouse=True)
def _catch_certain_warnings():
    """Filter certain warnings."""
    with catch_certain_warnings():
        yield


@pytest.fixture()
def _tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Produce a temporary project directory."""
    tmp_workdir(tmp_path, monkeypatch)
