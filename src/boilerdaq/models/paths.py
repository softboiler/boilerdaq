"""Paths for this project."""

from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir
from pydantic import DirectoryPath, FilePath

import boilerdaq
from boilerdaq.models import CWD


class Paths(CreatePathsModel):
    """Paths associated with this project."""

    # * Roots
    # ! Project
    project: DirectoryPath = CWD
    # ! Package
    package: DirectoryPath = get_package_dir(boilerdaq)
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
    filt: FilePath = scripts / "filt.py"
    csl: FilePath = scripts / "international-journal-of-heat-and-mass-transfer.csl"
    template: FilePath = scripts / "template.dotx"

    # * DVC-Tracked Inputs
    # * Local Inputs
    config: DirectoryPath = data / "config"
    # * Local Results
    benchmarks: DirectoryPath = data / "benchmarks"
    results: DirectoryPath = data / "results"
    notes: DirectoryPath = data / "notes"
    # * DVC-Tracked Results
