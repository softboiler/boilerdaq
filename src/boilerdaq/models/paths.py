"""Paths for this project."""

from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir
from pydantic import DirectoryPath

import boilerdaq
from boilerdaq.models import CWD


class Paths(CreatePathsModel):
    """Paths associated with this project."""

    # * Roots
    # ! Project
    project: DirectoryPath = CWD
    # ! Package
    package: DirectoryPath = get_package_dir(boilerdaq)
    # ! Data
    data: DirectoryPath = project / "data"
    # * Git-Tracked Inputs
    # * DVC-Tracked Inputs
    # * Local Inputs
    # * DVC-Tracked Results
