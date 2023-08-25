"""Project parameters."""

from boilercore.models import SynchronizedPathsYamlModel
from pydantic import Field

from boilerdaq import PARAMS_FILE
from boilerdaq.models.paths import Paths


class Params(SynchronizedPathsYamlModel):
    """Project parameters."""

    paths: Paths = Field(default_factory=Paths)
    """Project paths."""

    def __init__(self):
        """Initialize, propagate paths to the parameters file, and update the schema."""
        super().__init__(PARAMS_FILE)


PARAMS = Params()
"""All project parameters, including paths."""
