import setuptools
from distutils.core import setup

setup(
    name='oskb',
    version='0.0.1',
    description='On-Screen KeyBoard for Linux',
    url='https://github.com/ropg/oskb',
    author='Rop Gonggrijp',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3'
    ],
    keywords='keyboard',
    project_urls={
    'Documentation': 'https://github.com/ropg/oskb',
    'Source': 'https://github.com/ropg/oskb',
    'Tracker': 'https://github.com/ropg/oskb/issues',
},
    packages=['oskb'],
    python_requires='>=3',
    setup_requires=['wheel'],
    install_requires=['pyqt5', 'psutil', 'evdev'],
    entry_points={
        'console_scripts': [
            'oskb=oskb.cli:main',  # command=package.module:function
            'oskbdaemon=oskb.oskbdaemon:main'
        ],
    },
    package_data={'oskb': ['keyboards/*']}
)