from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="boilerdaq",
    version="2019.12.19",
    long_description=long_description,
    url="https://github.com/blakeNaccarato/boilerdaq",
    author="Blake Naccarato",
    package_dir={"": "src"},
    
    py_modules=["boilerdaq"],  # use for building a single module
    # packages=find_packages(where="src"),  # use for building packages
    
    python_requires=">=3.7",
    install_requires=["mcculw", "PyQt5", "pyqtgraph"],
    extras_require={  # pip install -e .[dev]
        "dev": ["black", "pylint", "rope", "doc8"]
    },
    data_files=[
        ("config", ["config/flux_params.csv", "config/sensors.csv", "config/unit_types.csv"])
    ],
)
