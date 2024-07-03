"""Paths for this project."""

from pathlib import Path

from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir, map_stages
from pydantic.v1 import DirectoryPath, FilePath

import boilerdaq
from boilerdaq import PROJECT_PATH


class Paths(CreatePathsModel):
    """Paths associated with this project."""

    # * Roots
    project: DirectoryPath = PROJECT_PATH
    data: DirectoryPath = project / "data"

    # * Local results
    benchmarks: DirectoryPath = data / "benchmarks"
    results: DirectoryPath = data / "results"
    notes: DirectoryPath = data / "notes"

    # * Git-tracked inputs
    # ! Package
    package: DirectoryPath = get_package_dir(boilerdaq)
    stages: dict[str, FilePath] = map_stages(package / "stages")
    # ! Config
    # Careful, "Config" is a special member of BaseClass
    config: DirectoryPath = data / "config"
    sensors_path = config / "1_sensors.csv"
    scaled_params_path = config / "2_scaled_params.csv"
    flux_params_path = config / "3_flux_params.csv"
    extrap_params_path = config / "4_extrap_params.csv"
    power_supplies_path = config / "0_power_supplies.csv"
    # ! Plotting
    plot_config: DirectoryPath = data / "plotting"
    mpl_base: FilePath = plot_config / "base.mplstyle"
    mpl_hide_title: FilePath = plot_config / "hide_title.mplstyle"

    # * DVC-tracked imports
    models: Path = data / "models"
