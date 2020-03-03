import setuptools
import re
from distutils.core import setup

# read the contents of your README file
from os import path

this_directory = path.abspath(path.dirname(__file__))

setup(
    name="oskb",
    version="0.2.1",
    description="On-Screen KeyBoard",
    long_description="I disliked the on-screen keyboards for Linux I tried. So I wrote a new one. Brand new but maturing fast... Please check the website for screenshots and instructions",
    url="https://github.com/ropg/oskb",
    author="Rop Gonggrijp",
    license="MIT",
    classifiers=["Development Status :: 3 - Alpha", "Programming Language :: Python :: 3",],
    keywords="keyboard",
    project_urls={
        "Documentation": "https://github.com/ropg/oskb/README.md",
        "Source": "https://github.com/ropg/oskb",
        "Tracker": "https://github.com/ropg/oskb/issues",
    },
    packages=["oskb", "oskb.im",],
    python_requires=">=3",
    setup_requires=["wheel"],
    install_requires=[
        "pyqt5",
        "psutil",  # killing earlier keyboards in cli.py
        'evdev; platform_system == "Linux"',
    ],
    entry_points={
        "console_scripts": [
            # command = package.module:function
            "oskb = oskb.cli:main",
            "oskbedit = oskb.oskbedit:main",
        ],
    },
    package_data={"oskb": ["keyboards/*", "*.css", "ui/*",]},
)
