"""Types relevant to array manipulation and image processing."""

from typing import TypeAlias

import pandas as pd

DF: TypeAlias = pd.DataFrame
DfOrS: TypeAlias = pd.DataFrame | pd.Series  # type: ignore  # pyright 1.1.317
