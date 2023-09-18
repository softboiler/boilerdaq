"""Paths for this project."""

from pathlib import Path

from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir, map_stages
from pydantic import DirectoryPath, FilePath

import boilerdaq
from boilerdaq import PROJECT_PATH


class Paths(CreatePathsModel):
    """Paths associated with this project."""

    # * Roots
    # ! Project
    project: DirectoryPath = PROJECT_PATH
    # ! Package
    package: DirectoryPath = get_package_dir(boilerdaq)
    stages: dict[str, FilePath] = map_stages(package / "stages", package)
    # ! Data
    data: DirectoryPath = project / "data"

    # * Git-Tracked Inputs
    # ! Plotting config
    plot_config: DirectoryPath = data / "plotting"
    mpl_base: FilePath = plot_config / "base.mplstyle"
    mpl_hide_title: FilePath = plot_config / "hide_title.mplstyle"
    # ! Scripts
    scripts: DirectoryPath = data / "scripts"
    # ? Files
    zotero: FilePath = scripts / "zotero.lua"
    csl: FilePath = scripts / "international-journal-of-heat-and-mass-transfer.csl"
    template: FilePath = scripts / "template.dotx"

    # * DVC imports from boilercore
    # ! Model Fit Function
    model: Path = data / "model.dillpickle"

    # * DVC-Tracked Inputs

    # * Local Inputs
    config: DirectoryPath = data / "config"
    sensors_path = config / "1_sensors.csv"
    scaled_params_path = config / "2_scaled_params.csv"
    flux_params_path = config / "3_flux_params.csv"
    extrap_params_path = config / "4_extrap_params.csv"
    power_supplies_path = config / "0_power_supplies.csv"

    # * Local Results
    benchmarks: DirectoryPath = data / "benchmarks"
    results: DirectoryPath = data / "results"
    notes: DirectoryPath = data / "notes"

    # * DVC-Tracked Results
