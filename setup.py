#!/usr/bin/env python
"""Compatibility shim.

Project metadata lives in ``pyproject.toml``. This file is retained so that
tooling which expects a ``setup.py`` to be present keeps working -- notably
``integrated_installer.sh``, which uses it as the sentinel file when deciding
whether a source checkout already exists.
"""

from setuptools import setup

setup()
