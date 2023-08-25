"""Tests."""

from pathlib import Path
from typing import Any

import pytest

SRC = Path("src")
EXAMPLES_DIR = SRC / "boilerdaq" / "examples"

EXAMPLES: list[Any] = []
for directory in [
    EXAMPLES_DIR,
    *[
        path
        for path in EXAMPLES_DIR.iterdir()
        if path.is_dir() and "__" not in str(path.relative_to(SRC))
    ],
]:
    for example in sorted(directory.glob("[!__]*.py")):
        module = str(example.relative_to(SRC).with_suffix("")).replace("\\", ".")
        if module in {"boilerdaq.examples.controlled.set_voltage"}:
            marks = [pytest.mark.skip]
        elif module in {"boilerdaq.examples.controlled.flux_control"}:
            marks = [pytest.mark.xfail]
        else:
            marks = []
        EXAMPLES.append(pytest.param(module, marks=marks))

EXPERIMENTS_DIR = SRC / "boilerdaq" / "experiments"
EXPERIMENTS: list[str] = []
for directory in [
    EXPERIMENTS_DIR,
    *[
        path
        for path in sorted(EXPERIMENTS_DIR.iterdir())
        if path.is_dir() and "__" not in str(path.relative_to(SRC))
    ],
]:
    EXPERIMENTS.extend(
        [
            str(stage.relative_to(SRC).with_suffix(""))
            .replace("\\", ".")
            .replace("/", ".")
            for stage in sorted(directory.glob("[!__]*.py"))
        ]
    )
