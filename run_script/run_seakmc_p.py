#!/usr/bin/env python
"""Thin wrapper kept for existing job scripts.

The entry point now lives in the installed package. Equivalent invocations:

    mpirun -np <nprocs> seakmc_p
    mpirun -np <nprocs> python -m seakmc_p
"""

from seakmc_p.cli import main

if __name__ == '__main__':
    main()
