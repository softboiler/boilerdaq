"""Paths for this project."""

from pathlib import Path

from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir, map_stages
from pydantic import DirectoryPath, FilePath

import boilerdaq
from boilerdaq import PROJECT_PATH


class Paths(CreatePathsModel):
    """Paths associated with this project."""

    root: DirectoryPath = PROJECT_PATH / "data"

    # * Local results
    benchmarks: DirectoryPath = root / "benchmarks"
    results: DirectoryPath = root / "results"
    notes: DirectoryPath = root / "notes"

    # * Git-tracked inputs
    # ! Config
    # Careful, "Config" is a special member of BaseClass
    config: DirectoryPath = root / "config"
    sensors_path: FilePath = config / "1_sensors.csv"
    scaled_params_path: FilePath = config / "2_scaled_params.csv"
    flux_params_path: FilePath = config / "3_flux_params.csv"
    extrap_params_path: FilePath = config / "4_extrap_params.csv"
    power_supplies_path: FilePath = config / "0_power_supplies.csv"
    # ! Plotting
    plot_config: DirectoryPath = root / "plotting"
    mpl_base: FilePath = plot_config / "base.mplstyle"
    mpl_hide_title: FilePath = plot_config / "hide_title.mplstyle"

    # * DVC-tracked imports
    models: Path = root / "models"


class PackagePaths(CreatePathsModel):
    """Paths associated with this project."""

    root: DirectoryPath = get_package_dir(boilerdaq)
    # * Git-tracked inputs
    # ! Package
    stages: dict[str, FilePath] = map_stages(root / "stages")
