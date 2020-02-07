from distutils.core import setup

setup(
    name='oskb',
    version='0.0.1dev',
    packages=['oskb'],
    install_requires=['pyqt5', 'psutil', 'evdev'],
    license='MIT licence',
	entry_points={
		'console_scripts': [
			'oskb=oskb.cli:main',  # command=package.module:function
			'oskbdaemon=oskb.oskbdaemon:main'
		],
	},
	package_data={'oskb': ['keyboards/*.kbd']}
)