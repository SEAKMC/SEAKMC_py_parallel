#!/usr/bin/env python
"""Thin wrapper kept for existing job scripts.

The entry point now lives in the installed package. Equivalent invocations:

    mpirun -np <nprocs> seakmc
    mpirun -np <nprocs> python -m seakmc
"""

from seakmc.cli import main

if __name__ == '__main__':
    main()
