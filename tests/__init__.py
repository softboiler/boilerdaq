"""Tests."""

from pathlib import Path
from typing import Any

import pytest
from boilercore.paths import get_module_rel, walk_modules

BOILERDAQ = Path("src") / "boilerdaq"
STAGES: list[Any] = []
for module in walk_modules(BOILERDAQ / "stages", BOILERDAQ):
    rel_to_controlled = get_module_rel(module, "controlled")
    if rel_to_controlled in {"set_voltage"}:
        marks = [pytest.mark.skip]
    elif rel_to_controlled in {"flux_control"}:
        marks = [pytest.mark.xfail]
    else:
        marks = []
    STAGES.append(
        pytest.param(module, id=get_module_rel(module, "stages"), marks=marks)
    )
