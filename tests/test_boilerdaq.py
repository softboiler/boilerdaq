"""Tests."""

from importlib import import_module
from pathlib import Path

import pytest
from PyQt5.QtCore import QTimer

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


@pytest.mark.parametrize(
    "example",
    (
        example
        for example in EXAMPLES
        if "boilerdaq.examples.set_voltage" not in example
    ),
)
def test_boilerdaq(example: str):
    """Test examples."""
    module = import_module(example)
    if example == "set_voltage":
        return
    QTimer.singleShot(1000, module.LOOPER.app.exit)
    module.LOOPER.start()
