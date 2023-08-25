"""Paths for this project."""

from boilercore.models import CreatePathsModel
from pydantic import DirectoryPath

from boilerdaq import DATA_DIR, PACKAGE_DIR, PROJECT_DIR


class Paths(CreatePathsModel):
    """Paths associated with this project."""

    project: DirectoryPath = PROJECT_DIR
    """Project directory."""
    package: DirectoryPath = PACKAGE_DIR
    """Package directory."""
    data: DirectoryPath = DATA_DIR
    """Project data."""
