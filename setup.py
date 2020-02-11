from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="boilerdaq",
    version="0.3",
    long_description=long_description,
    url="https://github.com/blakeNaccarato/boilerdaq",
    author="Blake Naccarato",
    package_dir={"": "src"},
    py_modules=["boilerdaq"],  # use for building a single module
    python_requires=">=3.7",
    install_requires=["mcculw", "PyQt5", "pyqtgraph", "scipy", "numpy"],
    extras_require={  # pip install -e .[dev]
        "dev": [
            # lint
            "pylint",
            "mypy",
            "flake8",
            # refactor
            "rope",
            # format
            "black",
            # document
            "doc8",
            # experiment
            "jupyter",
        ],
    },
)
