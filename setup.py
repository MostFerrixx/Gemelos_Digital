# -*- coding: utf-8 -*-
"""
Setup configuration for Digital Twin Warehouse Simulator
"""

from setuptools import setup, find_packages

setup(
    name="digital-twin-warehouse",
    version="11.0.0",
    description="Simulador de Gemelo Digital de Almacen con SimPy y Pygame",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Ferri",
    author_email="ferri@example.com",
    url="https://github.com/user/gemelos-digital-warehouse",

    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},

    # Dependencies
    install_requires=[
        "pygame>=2.5.0",
        "simpy>=4.0.0",
        "pytmx>=3.31",
        "PyQt6>=6.5.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "numpy>=1.24.0",
    ],

    # Python version requirement
    python_requires=">=3.9",

    # Entry points for command-line scripts
    entry_points={
        'console_scripts': [
            'warehouse-sim=entry_points.run_simulation:main',
            'warehouse-live=entry_points.run_live_simulation:main',
            'warehouse-replay=entry_points.run_replay_viewer:main',
            'warehouse-config=tools.configurator:main',
        ],
    },

    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],

    # Additional metadata
    keywords="simulation digital-twin warehouse logistics simpy pygame",
    project_urls={
        "Bug Reports": "https://github.com/user/gemelos-digital-warehouse/issues",
        "Source": "https://github.com/user/gemelos-digital-warehouse",
    },
)
