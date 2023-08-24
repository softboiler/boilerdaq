"""Paths for this project."""

from boilercore.models import CreatePathsModel
from pydantic import DirectoryPath

from boilerdaq import DATA_DIR, PROJECT_DIR


class ProjectPaths(CreatePathsModel):
    """Paths associated with project requirements and code."""

    path: DirectoryPath = PROJECT_DIR
    """Path associated with project requirements and code."""


class DvcPaths(CreatePathsModel):
    """Data tracked by DVC."""

    data: DirectoryPath = DATA_DIR / "dvc"
    """Data tracked by DVC."""


class GitPaths(CreatePathsModel):
    """Data tracked by git."""

    data: DirectoryPath = DATA_DIR / "git"
    """Data tracked by git."""


class ImportedPaths(CreatePathsModel):
    """Paths imported from other DVC projects."""

    data: DirectoryPath = DATA_DIR / "imported"
    """Data imported from other DVC projects."""


class LocalPaths(CreatePathsModel):
    """Local data not tracked by git or DVC."""

    data: DirectoryPath = DATA_DIR / "local"
    """Local data, untracked by Git and DVC."""
