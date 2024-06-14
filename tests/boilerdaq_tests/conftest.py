"""Test fixtures."""

from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from boilercore import WarningFilter, filter_certain_warnings
from boilercore.paths import get_module_rel, walk_modules
from boilercore.testing import get_session_path
from debugpy import is_client_connected
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import boilerdaq
from boilerdaq import INSTRUMENT
from boilerdaq.daq import Looper, open_instrument

DEBUG = is_client_connected()


STAGES_DIR = Path("src") / "boilerdaq" / "stages"
STAGES: list[Any] = []
for module in (f"boilerdaq.{module}" for module in walk_modules(STAGES_DIR)):
    rel_to_stages = get_module_rel(module, "stages")
    marks = [pytest.mark.skip] if rel_to_stages == "controlled.set_voltage" else []
    STAGES.append(
        pytest.param(module, id=get_module_rel(module, "stages"), marks=marks)
    )


@pytest.fixture(scope="session", autouse=True)
def _project_session_path(tmp_path_factory: pytest.TempPathFactory):
    """Set the project directory."""
    get_session_path(tmp_path_factory, boilerdaq)


@pytest.fixture(scope="session", autouse=True)
def _disable_power_supply():
    """Disable the power supply after testing."""
    try:
        yield
    finally:
        instrument = open_instrument(INSTRUMENT)
        for instruction in ["output:state off", "source:current 0", "source:voltage 0"]:
            instrument.write(instruction)
        instrument.close()


# Can't be session scope
@pytest.fixture(autouse=True)
def _filter_certain_warnings():
    """Filter certain warnings."""
    filter_certain_warnings([
        WarningFilter(category=ResourceWarning, message=msg)
        for msg in (
            r"unclosed event loop <.+EventLoop running=False closed=False debug=False>",
            r"unclosed <socket\.socket fd=\d+, family=\d+, type=\d+, proto=\d+.*>",
        )
    ])


@pytest.fixture(params=STAGES)
def looper(request: pytest.FixtureRequest):
    """Test example procedures."""
    module = import_module(request.param)
    looper: Looper = getattr(module, "looper", lambda: None)() or module.main()
    if not DEBUG:
        app: QApplication = looper.app
        QTimer.singleShot(2000, app.closeAllWindows)
    return looper
