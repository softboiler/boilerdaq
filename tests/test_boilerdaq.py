"""Test hardware and experimental procedures."""

from importlib import import_module
from pathlib import Path

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from boilerdaq import Looper
from tests import EXAMPLES, EXPERIMENTS

pytestmark = pytest.mark.xdist_group(name="hardware")


@pytest.mark.parametrize("example", EXAMPLES)
def test_examples(example: str):
    """Test example procedures."""
    module = import_module(example)
    looper: Looper = module.looper if hasattr(module, "looper") else module.LOOPER
    app: QApplication = looper.app
    QTimer.singleShot(1000, app.closeAllWindows)
    looper.start()


@pytest.mark.parametrize("stage", EXPERIMENTS)
def test_experiments(stage: str, monkeypatch: pytest.MonkeyPatch, tmp_project: Path):
    """Test experimental procedures."""
    with monkeypatch.context() as m:
        m.chdir(tmp_project)
        import_module(stage).main()
