"""Make a local `pyrightconfig.json` that includes the specified paths."""

from collections.abc import Iterable
from json import dumps
from pathlib import Path
from tomllib import loads

PYPROJECT = Path("pyproject.toml")
"""Default `pyproject.toml`."""
PYRIGHTCONFIG = Path("pyrightconfig.json")
"""Default `pyrightconfig.json`."""
OTHERS = [Path("../boilercore/src")]
"""Default local paths to append."""


def make_local_pyrightconfig(
    pyproject: Path | str = PYPROJECT,
    pyrightconfig: Path = PYRIGHTCONFIG,
    others: Iterable[Path | str] = OTHERS,
):
    """Make a local `pyrightconfig.json` that includes the specified paths.

    Duplicates config from `pyproject.toml` to `pyrightconfig.json` and appends
    specified paths to `include`. Enables type checking and refactoring across project
    boundaries, for instance with editable local dependencies during development of
    related projects in a multi-repo workflow.

    Args:
        pyproject: Source `pyproject.toml`. Search project root by default.
        pyrightconfig: Destination `pyrightconfig.json`. Search project root by default.
        others: Local paths to append. Defaults to `[Path("../boilercore/src")]`.
    """
    config = loads(Path(pyproject).read_text("utf-8"))["tool"]["pyright"]
    config = {
        "include": [
            *config.pop("include", []),
            *[str(Path(other).as_posix()) for other in others],
        ],
        **config,
    }
    data = f"{dumps(indent=2, obj=config)}\n"
    Path(pyrightconfig).write_text(encoding="utf-8", data=data)


if __name__ == "__main__":
    make_local_pyrightconfig()
