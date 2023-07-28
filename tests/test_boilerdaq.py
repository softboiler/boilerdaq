"""Tests."""

from importlib import import_module
from pathlib import Path

import pytest
from PyQt5.QtCore import QTimer

EXAMPLES = sorted(Path("src/boilerdaq/examples").glob("[!__]*.py"))


@pytest.mark.parametrize("example", (example.stem for example in EXAMPLES))
def test_boilerdaq(example: str):
    """Test examples."""
    module = import_module(f"boilerdaq.examples.{example}")
    if example == "set_voltage":
        return
    QTimer.singleShot(1000, module.looper.app.exit)
    module.looper.start()
