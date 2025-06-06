"""
Setup configuration for the vTAXI package.
"""

from setuptools import setup, find_packages

setup(
    name='vtaxi',
    version='0.1.0',
    description='AI Air Traffic Controller for Ground Operations at Paris-Orly Airport (LFPO)',
    author='Mathias',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'shapely>=2.0.0',
        'geojson>=3.0.0'
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'vtaxi=vtaxi.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering',
    ],
) 