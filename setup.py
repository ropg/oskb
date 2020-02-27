import setuptools
import re
from distutils.core import setup

# read the contents of your README file
from os import path

this_directory = path.abspath(path.dirname(__file__))

setup(
<<<<<<< HEAD
    name="oskb",
    version="0.2.0",
    description="On-Screen KeyBoard",
    long_description="I disliked the on-screen keyboards for Linux I tried. So I wrote a new one. Brand new but maturing fast... Please check the website for screenshots and instructions",
    url="https://github.com/ropg/oskb",
    author="Rop Gonggrijp",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
=======
    name = 'oskb',
    version = '0.1.1',
    description = 'On-Screen KeyBoard',
    long_description = 'I disliked the on-screen keyboards for Linux I tried. So I wrote a new one. Brand new but maturing fast... Please check the website for screenshots and instructions',
    url = 'https://github.com/ropg/oskb',
    author = 'Rop Gonggrijp',
    license = 'MIT',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3'
>>>>>>> a45b92154336593000a3db884887d528c9636e36
    ],
    keywords="keyboard",
    project_urls={
        "Documentation": "https://github.com/ropg/oskb/README.md",
        "Source": "https://github.com/ropg/oskb",
        "Tracker": "https://github.com/ropg/oskb/issues",
    },
<<<<<<< HEAD
    packages=[
        "oskb",
        "oskb.im",
    ],
    python_requires=">=3",
    setup_requires=["wheel"],
    install_requires=[
        "pyqt5",
        "psutil",  # killing earlier keyboards in cli.py
        'evdev; platform_system == "Linux"',
=======
    packages = [
        'oskb',
        'oskb.im',
    ],
    python_requires = '>=3',
    setup_requires = ['wheel'],
    install_requires = [
        'pyqt5',
        'psutil',                               # killing earlier keyboards in cli.py
        'evdev; platform_system == "Linux"'
>>>>>>> a45b92154336593000a3db884887d528c9636e36
    ],
    entry_points={
        "console_scripts": [
            # command = package.module:function
            "oskb = oskb.cli:main",
            "oskbedit = oskb.oskbedit:main",
        ],
    },
    package_data={
        "oskb": [
            "keyboards/*",
            "*.css",
        ]
<<<<<<< HEAD
    },
=======
    }
>>>>>>> a45b92154336593000a3db884887d528c9636e36
)
