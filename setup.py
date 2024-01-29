# setup.py

from setuptools import setup, find_packages

setup(
    name='depscleaner',
    version='1.0.0',
    author='Oleg Kron',
    description='A tool to clean up dependency folders in projects',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'depscleaner=depscleaner.__main__:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
