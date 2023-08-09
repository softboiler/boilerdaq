"""Tests."""

from importlib import import_module
from pathlib import Path

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from boilerdaq import Looper

SRC = Path("src")
EXAMPLES_DIR = SRC / "boilerdaq" / "examples"
EXAMPLES: list[str] = []
for directory in [EXAMPLES_DIR] + [
    path
    for path in EXAMPLES_DIR.iterdir()
    if path.is_dir() and "__" not in str(path.relative_to(SRC))
]:
    EXAMPLES.extend(
        [
            str(example.relative_to(SRC).with_suffix("")).replace("\\", ".")
            for example in sorted(directory.glob("[!__]*.py"))
        ]
    )


@pytest.mark.xdist_group(name="hardware")
@pytest.mark.parametrize(
    "example",
    (
        example
        for example in EXAMPLES
        if "boilerdaq.examples.controlled.set_voltage" not in example
    ),
)
def test_boilerdaq(example: str):
    """Test examples."""
    module = import_module(example)
    looper: Looper = module.looper if hasattr(module, "looper") else module.LOOPER
    app: QApplication = looper.app
    QTimer.singleShot(1000, app.closeAllWindows)
    looper.start()
