"""Project parameters."""

from boilercore.fits import Fit
from boilercore.models import SynchronizedPathsYamlModel
from boilercore.models.geometry import Geometry
from pydantic import Field, FilePath

from boilerdaq import get_params_file
from boilerdaq.models.paths import PackagePaths, Paths

PARAMS_FILE = get_params_file()


class Params(SynchronizedPathsYamlModel):
    """Project parameters."""

    source: FilePath = PARAMS_FILE
    fit: Fit = Field(default_factory=Fit, description="Parameters for model fit.")
    geometry: Geometry = Field(default_factory=Geometry, description="Geometry.")
    paths: Paths = Field(default_factory=Paths)
    """Project paths."""
    package_paths: PackagePaths = Field(default_factory=PackagePaths)
    """Package paths."""


PARAMS = Params()
"""All project parameters, including paths."""
