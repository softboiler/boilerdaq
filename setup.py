from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="boilerdaq",
    version="2019.12.19",
    long_description=long_description,
    url="https://github.com/blakeNaccarato/daqmcc",
    author="Blake Naccarato",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
    install_requires=["mcculw", "PyQt5", "pyqtgraph"],
    extras_require={  # pip install -e .[dev]
        "dev": ["black", "pylint", "rope"]
    },
    data_files=[
        ("config", ["config/flux_params.csv", "config/sensors.csv"])
    ],
)
