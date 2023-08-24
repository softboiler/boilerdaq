"""Parameters for the data pipeline."""

from boilercore.models import SynchronizedPathsYamlModel
from pydantic import Field

from boilerdaq import PARAMS_FILE
from boilerdaq.models.paths import (
    DvcPaths,
    GitPaths,
    ImportedPaths,
    LocalPaths,
    ProjectPaths,
)


class Params(SynchronizedPathsYamlModel):
    """Project parameters."""

    project: ProjectPaths = Field(default_factory=ProjectPaths)
    """Paths associated with project requirements and code."""
    dvc: DvcPaths = Field(default_factory=DvcPaths)
    """Data tracked by DVC."""
    git: GitPaths = Field(default_factory=GitPaths)
    """Data tracked by git."""
    imported: ImportedPaths = Field(default_factory=ImportedPaths)
    """Paths imported from other DVC projects."""
    local: LocalPaths = Field(default_factory=LocalPaths)
    """Local data not tracked by git or DVC."""

    def __init__(self):
        """Initialize, propagate paths to the parameters file, and update the schema."""
        super().__init__(PARAMS_FILE)


PARAMS = Params()
"""All project parameters, including paths."""
