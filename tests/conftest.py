"""Test fixtures."""

from importlib import import_module
from pathlib import Path
from shutil import copytree

import pytest
from boilercore import filter_certain_warnings
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

import boilerdaq
from boilerdaq import Looper
from tests import STAGES


@pytest.fixture(scope="session", autouse=True)
def _project_session_path(tmp_path_factory: pytest.TempPathFactory):
    """Set the project directory."""
    project_test_data = Path("tests") / "root"
    project_session_path = tmp_path_factory.getbasetemp() / "root"
    boilerdaq.PROJECT_PATH = project_session_path
    copytree(project_test_data, project_session_path, dirs_exist_ok=True)


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
