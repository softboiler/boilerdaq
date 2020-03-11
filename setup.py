from setuptools import setup

setup(
    name="boilerdaq",
    version="0.3",
    url="https://github.com/blakeNaccarato/boilerdaq",
    author="Blake Naccarato",
    package_dir={"": "src"},
    py_modules=["boilerdaq"],  # use for building a single module
    python_requires=">=3.7",
    install_requires=[
        "mcculw",
        "PyQt5",
        "pyqtgraph",
        "pyvisa",
        "simple-pid",
        "scipy",
        "numpy",
    ],
    extras_require={  # pip install -e .[dev]
        "dev": [
            # build
            "setuptools",
            "wheel",
            "twine",
            # data science
            "dtale",
            "pandas",
            # document
            "doc8",
            # experiment
            "jupyter",
            # format
            "black",
            # lint
            "flake8",
            "mypy",
            "pylint",
            # matplotlib w/ backend
            "matplotlib",
            "PyQt5",
            # refactor
            "rope",
        ],
    },
)
