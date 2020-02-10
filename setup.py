import setuptools
from distutils.core import setup

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = 'oskb',
    version = '0.0.3',
    description = 'On-Screen KeyBoard for Linux',
    long_description = long_description,
    url = 'https://github.com/ropg/oskb',
    author = 'Rop Gonggrijp',
    license = 'MIT',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3'
    ],
    keywords = 'keyboard',
    project_urls = {
        'Documentation': 'https://github.com/ropg/oskb/README.md',
        'Source': 'https://github.com/ropg/oskb',
        'Tracker': 'https://github.com/ropg/oskb/issues',
    },
    packages = ['oskb'],
    python_requires = '>=3',
    setup_requires = ['wheel'],
    install_requires = [
        'pyqt5',
        'psutil',
        'evdev'
    ],
    entry_points = {
        'console_scripts': [
            # command=package.module:function
            'oskb=oskb.cli:main',
        ],
    },
    package_data = {
        'oskb': [
            'keyboards/*'
        ]
    }
)