
import os
from pathlib import Path
from setuptools import setup

ROOT = Path(__file__).parent

with open(ROOT / "README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

with open(ROOT / "VERSION") as version_file:
    VERSION = version_file.read().strip()


setup(
    name="pyFAST",
    description="pyFAST",
    long_description=LONG_DESCRIPTION,
    version=VERSION,
    url="https://github.com/rafmudaf/pyFAST/",
    author="Rafael Mudafort",
    author_email="rafael.mudafort@nrel.gov",
    classifiers=[
        "Topic :: Utilities",
        "Topic :: Software Development :: Testing",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    packages=["pyFAST"],
    python_requires=">=3.6",
    install_requires=["numpy", "bokeh==2.4"],
    extras_require={
        "dev": ["pytest", "pytest-cov", "pytest-xdist"]
    },
    test_suite="pytest",
    tests_require=["pytest", "pytest-xdist", "pytest-cov"],
    entry_points={"console_scripts": ["pyFAST = pyFAST.__main__:main"]},
)
