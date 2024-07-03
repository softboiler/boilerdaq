"""Data acquisition for a nucleate pool boiling experimental apparatus."""

from pathlib import Path

PROJECT_PATH = Path()
INSTRUMENT = "USB0::0x0957::0x0807::US25N3188G::0::INSTR"


def get_params_file():  # noqa: D103
    return PROJECT_PATH / "params.yaml"
