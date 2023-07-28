"""Utilities for root and DVC-tracked documentation."""

from collections.abc import Callable
from contextlib import contextmanager, nullcontext
from os import chdir
from pathlib import Path
from typing import Any
from warnings import catch_warnings, filterwarnings

import nbformat as nbf
import pandas as pd
import seaborn as sns
from IPython.display import display
from IPython.utils.capture import capture_output
from matplotlib import pyplot as plt

from boilerdaq.types import DfOrS

# * -------------------------------------------------------------------------------- * #
# * COMMON TO ROOT AND DVC-TRACKED DOCUMENTATION

FLOAT_SPEC = "#.4g"
"""The desired float specification for formatted output."""

HIDE = display()
"""Hide unsuppressed output. Can't use semicolon due to black autoformatter."""

DISPLAY_ROWS = 40
"""The number of rows to display in a dataframe."""


def init():
    """Initialize notebook formats."""

    # The triple curly braces in the f-string allows the format function to be
    # dynamically specified by a given float specification. The intent is clearer this
    # way, and may be extended in the future by making `float_spec` a parameter.
    pd.options.display.float_format = f"{{:{FLOAT_SPEC}}}".format
    pd.options.display.min_rows = pd.options.display.max_rows = DISPLAY_ROWS

    sns.set_theme(
        context="notebook",
        style="whitegrid",
        palette="bright",
        font="sans-serif",
    )
    sns.color_palette("deep")
    plt.style.use(style=Path("plotting/base.mplstyle"))


@contextmanager
def nowarn(capture: bool = False):
    """Don't raise any warnings. Optionally capture output for pesky warnings."""
    with catch_warnings(), capture_output() if capture else nullcontext():
        filterwarnings("ignore")
        yield


# * -------------------------------------------------------------------------------- * #
# * MAKE STYLED DATAFRAMES RESPECT PRECISION
# *
# * See: https://gist.github.com/blakeNaccarato/3c751f0a9f0f5143f3cffc525e5dd577


@contextmanager
def style_df(df: DfOrS, head: bool = False):
    """Style a dataframe."""
    df, truncated = truncate(df, head)
    styler = df.style
    yield styler
    display(styler.format(get_df_formatter(df, truncated)))  # type: ignore  # pyright 1.1.317


def display_dfs(*dfs: DfOrS, head: bool = False):
    """Display formatted DataFrames.

    When a mapping of column names to callables is given to the Pandas styler, the
    callable will be used internally by Pandas to produce formatted strings. This
    differs from elementwise formatting, in which Pandas expects the callable to
    actually process the value and return the formatted string.
    """
    for df in dfs:
        df, truncated = truncate(df, head)
        display(df.style.format(get_df_formatter(df, truncated)))  # type: ignore  # pyright 1.1.317


def get_df_formatter(
    df: pd.DataFrame, truncated: bool
) -> Callable[..., str] | dict[str, Callable[..., str]]:
    """Get formatter for the dataframe."""
    if truncated:
        return format_cell
    cols = df.columns
    types = {col: dtype.type for col, dtype in zip(cols, df.dtypes, strict=True)}
    return {col: get_formatter(types[col]()) for col in cols}


def format_cell(cell) -> str:
    """Format individual cells."""
    return get_formatter(cell)(cell)


def get_formatter(instance: Any) -> Callable[..., str]:
    """Get the formatter depending on the type of the instance."""
    match instance:
        case float():
            return lambda cell: f"{cell:{FLOAT_SPEC}}"
        case _:
            return lambda cell: f"{cell}"


def truncate(df: DfOrS, head: bool = False) -> tuple[pd.DataFrame, bool]:
    """Truncate long dataframes, showing only the head and tail."""
    if isinstance(df, pd.Series):
        df = df.to_frame()
    if len(df) <= pd.options.display.max_rows:
        return df, False  # type: ignore  # pyright 1.1.317
    if head:
        return df.head(pd.options.display.min_rows), True
    df = df.copy()
    # Resolves case when column names are not strings for latter assignment, e.g. when
    # the column axis is a RangeIndex.
    df.columns = [str(col) for col in df.columns]
    # Resolves ValueError: Length of names must match number of levels in MultiIndex.
    ellipsis_index = ("...",) * df.index.nlevels
    df = pd.concat(
        [
            df.head(pd.options.display.min_rows // 2),
            df.iloc[[0]]  # Resolves ValueError: cannot handle a non-unique multi-index!
            .reindex(
                pd.MultiIndex.from_tuples([ellipsis_index], names=df.index.names)
                if isinstance(df.index, pd.MultiIndex)
                else pd.Index(ellipsis_index, name=df.index.name)
            )
            .assign(**{col: "..." for col in df.columns}),
            df.tail(pd.options.display.min_rows // 2),
        ]
    )
    return df, True


# * -------------------------------------------------------------------------------- * #
# * ROOT DOCUMENTATION


def main():
    """Insert `hide-input` tag to all notebooks in `docs/examples`."""
    for notebook in Path("docs/examples").glob("*.ipynb"):
        insert_tags(notebook, ["hide-input"])


def patch():
    """Set the appropriate working directory if in documentation."""
    path = Path().cwd()
    while not (path / "conf.py").exists():
        path = path.parent
    chdir(path.parent)


def insert_tags(notebook: Path, tags_to_insert: list[str]):
    """Insert tags to all cells in a notebook.

    See: https://jupyterbook.org/en/stable/content/metadata.html?highlight=python#add-tags-using-python-code
    """
    contents = nbf.read(notebook, nbf.NO_CONVERT)
    for cell in contents.cells:  # type: ignore
        tags = cell.get("metadata", {}).get("tags", [])
        cell["metadata"]["tags"] = tags_to_insert + list(
            set(tags) - set(tags_to_insert)
        )
    nbf.write(contents, notebook)


if __name__ == "__main__":
    main()
