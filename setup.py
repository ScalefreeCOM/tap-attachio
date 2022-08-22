#!/usr/bin/env python
from setuptools import setup

setup(
    name="tap-attach_io",
    version="0.1.0",
    description="Singer.io tap for extracting data",
    author="Stitch",
    url="http://singer.io",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_attach_io"],
    install_requires=[
        # NB: Pin these to a more specific version for tap reliability
        "singer-python",
        "requests",
    ],
    entry_points="""
    [console_scripts]
    tap-attach_io=tap_attach_io:main
    """,
    packages=["tap_attach_io"],
    package_data = {
        "schemas": ["tap_attach_io/schemas/*.json"]
    },
    include_package_data=True,
)
