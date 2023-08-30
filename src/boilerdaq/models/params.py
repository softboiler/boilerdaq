"""Project parameters."""

from pathlib import Path

from boilercore.models import SynchronizedPathsYamlModel
from pydantic import Field

from boilerdaq.models import CWD
from boilerdaq.models.paths import Paths


class Params(SynchronizedPathsYamlModel):
    """Project parameters."""

    paths: Paths = Field(default_factory=Paths)
    """Project paths."""

    def __init__(self, data_file: Path = CWD / "params.yaml", **kwargs):
        """Initialize, propagate paths to the parameters file, and update the schema."""
        super().__init__(data_file, **kwargs)


PARAMS = Params()
"""All project parameters, including paths."""
