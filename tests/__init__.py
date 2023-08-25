"""Tests."""

from pathlib import Path
from typing import Any

import pytest
from boilercore.testing import get_module_rel, walk_modules

BOILERDAQ = Path("src") / "boilerdaq"
PARAMS = Path("params.yaml")
DATA = Path("data")
TEST_DATA = Path("tests") / DATA
EXAMPLES: list[Any] = []
for module in walk_modules(BOILERDAQ / "examples", BOILERDAQ):
    rel_to_controlled = get_module_rel(module, "controlled")
    if rel_to_controlled in {"set_voltage"}:
        marks = [pytest.mark.skip]
    elif rel_to_controlled in {"flux_control"}:
        marks = [pytest.mark.xfail]
    else:
        marks = []
    EXAMPLES.append(pytest.param(module, marks=marks))
