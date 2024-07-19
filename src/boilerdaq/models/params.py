"""Project parameters."""

from pathlib import Path

from boilercore.fits import Fit
from boilercore.models import SynchronizedPathsYamlModel
from boilercore.models.geometry import Geometry
from pydantic.v1 import Field

from boilerdaq import get_params_file
from boilerdaq.models.paths import Paths

PARAMS_FILE = get_params_file()


class Params(SynchronizedPathsYamlModel):
    """Project parameters."""

    fit: Fit = Field(
        default=Fit(
            free_params=["T_s", "q_s", "h_a"],
            fixed_params=["h_w", "r", "T_infa", "T_infw", "x_s", "x_wa", "k"],
        ),
        description="Parameters for model fit.",
    )
    geometry: Geometry = Field(default_factory=Geometry, description="Geometry.")

    paths: Paths = Field(default_factory=Paths)
    """Project paths."""

    def __init__(self, data_file: Path = PARAMS_FILE, **kwargs):
        """Initialize, propagate paths to the parameters file, and update the schema."""
        super().__init__(data_file, **kwargs)


PARAMS = Params()
"""All project parameters, including paths."""
