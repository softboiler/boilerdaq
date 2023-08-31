"""Project parameters."""

from pathlib import Path

from boilercore.models import SynchronizedPathsYamlModel
from pydantic import Field

from boilerdaq import get_params_file
from boilerdaq.models.paths import Paths

PARAMS_FILE = get_params_file()


class Params(SynchronizedPathsYamlModel):
    """Project parameters."""

    paths: Paths = Field(default_factory=Paths)
    """Project paths."""

    def __init__(self, data_file: Path = PARAMS_FILE, **kwargs):
        """Initialize, propagate paths to the parameters file, and update the schema."""
        super().__init__(data_file, **kwargs)


PARAMS = Params()
"""All project parameters, including paths."""
