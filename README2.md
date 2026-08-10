# SEAKMC_py

SEAKMC_py is a Python package for **self-evolving atomistic kinetic Monte Carlo (SEAKMC)** simulations. It extends conventional kinetic Monte Carlo by discovering and evaluating transition events on the fly, enabling long-timescale simulations of defect evolution, activated processes, and microstructural kinetics without requiring a fully predefined event catalog.

## Overview

Conventional kinetic Monte Carlo (KMC) requires a catalog of transition barriers and prefactors before a simulation can begin. For complex defected materials, building a complete catalog is often impractical because relevant activated events depend strongly on the local atomic environment. SEAKMC_py addresses this limitation by partitioning the system into **active volumes (AVs)** around detected defects and performing saddle-point searches only within these localized regions.

For each KMC step, SEAKMC_py identifies defects, constructs active volumes, searches for nearby saddle points, removes duplicate or invalid events, calculates event prefactors, and updates an event catalog. A KMC event is then selected using the local-energy-barrier (LEB) approach, the system configuration is updated and relaxed, and the workflow repeats. Previously identified saddle points can be recycled through a defect database to improve efficiency during repeated sampling of similar local environments.

## Key Features

- On-the-fly construction of activated-event catalogs for atomistic KMC simulations
- Defect detection and automated construction of local active volumes
- Saddle-point searches based on the dimer method and related search workflows
- Dynamic active-volume support for more efficient sampling of defect-mediated transitions
- Saddle-point preprocessing, validation, classification, post-processing, and recycling
- Harmonic-theory prefactor calculations and low-energy-barrier KMC event selection
- Defect-bank and saddle-point database support for reusing previously sampled events
- Energy recalibration and full-system relaxation after KMC events
- Serial and MPI-parallel implementations using `mpi4py`
- LAMMPS/Python wrapper interface, with support for OpenKIM models

## Workflow

A typical SEAKMC_py cycle includes:

1. Load system inputs, restart data, and the defect/saddle-point database.
2. Perform optional molecular dynamics or structural relaxation.
3. Detect defects in the current atomic configuration.
4. Construct and characterize active volumes around the defects.
5. Preload compatible saddle points from the database or user-provided event files.
6. Search for additional saddle points within each active volume.
7. Relax and validate saddle points; remove duplicate or unsuitable events.
8. Classify events, calculate prefactors, and recycle validated events into the database.
9. Recalibrate event barriers when required.
10. Construct the KMC catalog, select an event, and update the atomic configuration.
11. Relax the full system and proceed to the next KMC step.

## Requirements

SEAKMC_py requires:

- Python 3.0 or later
- Anaconda/Conda
- `numpy`
- `pymatgen`
- `mpi4py` for parallel execution
- LAMMPS with Python support
- Recommended: OpenKIM models for interatomic-potential evaluation

SEAKMC_py does not include an energy or force evaluator. It uses the LAMMPS Python interface for energy and force calculations, making it adaptable to different LAMMPS-supported interatomic potentials.

## Installation

Create and activate a Conda environment, install the required packages, then install the serial or parallel SEAKMC_py package:

```bash
conda create -n seakmc_env
conda activate seakmc_env
conda install conda-forge::lammps=*=*mpich
conda install openkim-models
conda install --channel conda-forge pymatgen
python -m pip install mpi4py==3.1.6

# From the SEAKMC_py source directory
python setup.py install
```

For OpenMPI-based LAMMPS installations, replace the MPICH LAMMPS package with the appropriate OpenMPI variant.

## Running Simulations

SEAKMC_py uses a YAML input file, typically named `input.yaml`, to define system settings and simulation parameters.

Run the serial version:

```bash
python run_seakmc.py
```

Run the MPI-parallel version:

```bash
mpirun -np 4 python run_seakmc_p.py
```

Adjust the number of MPI processes and job-submission settings to match the workload, number of active volumes, and available computational resources.

## Outputs

Typical outputs include:

- `Seakmc.log` — simulation log
- `Seakmc_summary.csv` — KMC-step summary data
- Restart files — state required to resume a simulation
- `SPOut` — saddle-point information
- `DataOut` — atomic-structure information
- `DefectBank` — reusable defect and saddle-point data
- `AVOut` — active-volume information
- `Runner_<color>` directories — task-specific files generated during parallel runs

## Citation

If you use SEAKMC_py in published work, please cite:

> Tao Liang and Haixuan Xu, *Saddle point search with dynamic active volume*, Computational Materials Science **228**, 112354 (2023). https://doi.org/10.1016/j.commatsci.2023.112354

## Documentation

See the package manual and the `examples/` directory for detailed input settings, active-volume construction, saddle-point search options, database handling, and parallelization workflows.
