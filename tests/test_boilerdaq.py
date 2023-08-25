"""Test hardware and experimental procedures."""

from importlib import import_module

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from boilerdaq import Looper
from tests import EXAMPLES

pytestmark = pytest.mark.xdist_group(name="hardware")


@pytest.mark.parametrize("example", EXAMPLES)
def test_examples(example: str):
    """Test example procedures."""
    looper: Looper = import_module(example).main()
    app: QApplication = looper.app
    QTimer.singleShot(1000, app.closeAllWindows)
    looper.start()
