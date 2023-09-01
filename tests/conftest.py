"""Test fixtures."""

from importlib import import_module

import pytest
from boilercore import filter_certain_warnings
from boilercore.testing import get_session_path
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from pyvisa import ResourceManager
from pyvisa.resources import MessageBasedResource

import boilerdaq
from boilerdaq import Looper
from tests import INSTRUMENT_NAME, STAGES


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
        instrument: MessageBasedResource = ResourceManager().open_resource(  # type: ignore
            INSTRUMENT_NAME,
            read_termination="\n",
            write_termination="\n",
        )
        for instruction in ["output:state off", "source:current 0", "source:voltage 0"]:
            instrument.write(instruction)
        instrument.close()


# Can't be session scope
@pytest.fixture(autouse=True)
def _filter_certain_warnings():
    """Filter certain warnings."""
    filter_certain_warnings()


@pytest.fixture(params=STAGES)
def looper(request: pytest.FixtureRequest):
    """Test example procedures."""
    looper: Looper = import_module(request.param).main()
    app: QApplication = looper.app
    QTimer.singleShot(1000, app.closeAllWindows)
    return looper
