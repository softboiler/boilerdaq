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
)
