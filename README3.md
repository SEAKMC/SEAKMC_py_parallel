# SEAKMC

**Self-Evolving Atomistic Kinetic Monte Carlo (SEAKMC)** is a Python-based atomistic simulation framework for exploring long-timescale material evolution using kinetic Monte Carlo (KMC). SEAKMC constructs saddle-point/event catalogs on the fly and enables efficient sampling of the potential energy landscape through **spatial decomposition into localized active volumes (AVs)** and **MPI-based parallel saddle-point searches**.

## Key Features

* **Self-evolving atomistic KMC** for long-timescale atomistic simulations
* **Active Volume (AV) spatial decomposition** to localize saddle-point searches around defects
* **Dynamic Active Volume (DAV)** for automated identification of relevant atoms and reduction of the search dimensionality
* **Parallel saddle-point search (SPS)** using MPI
* **Task-level parallelization** over AVs and saddle-point-search attempts
* **Spatial decomposition of large atomistic systems** for efficient defect identification
* Optional **master–slave task scheduling** to reduce processor idle time for workloads with nonuniform computational costs
* **Dynamic defect identification** during the simulation
* **Scale Normal Coordinates (SNC)** for efficient saddle-point sampling
* Saddle-point recycling and external **defect-bank** support
* Point-group symmetry operations and harmonic-theory prefactor calculations
* Support for **low-energy-barrier (LEB)** KMC through the mean-rate method
* Python interface to **LAMMPS** through pyLAMMPS

## Why Spatial Decomposition?

In SEAKMC, saddle points are typically associated with localized atomic rearrangements around defects. Instead of performing saddle-point searches on the entire simulation cell, the system is decomposed into localized **active volumes**, each treated as an independent subsystem.

This decomposition substantially reduces the dimensionality of individual saddle-point searches and allows multiple AVs to be processed concurrently.

```text
                 Full Atomistic System
                         │
                  Defect Identification
                         │
             ┌───────────┴───────────┐
             │                       │
           Defect 1                Defect 2
             │                       │
          ┌──▼──┐                  ┌──▼──┐
          │ AV1 │                  │ AV2 │
          └──┬──┘                  └──┬──┘
             │                       │
       Saddle-point             Saddle-point
        searches                  searches
             │                       │
             └───────────┬───────────┘
                         │
                  Event / SP Catalog
                         │
                         ▼
                        KMC
```

The **Dynamic Active Volume (DAV)** further reduces the number of active degrees of freedom by deactivating atoms that are not important to the saddle-point search. This improves both computational efficiency and the ability to identify relevant saddle points.

## Parallelization

SEAKMC uses **MPI through `mpi4py`** to parallelize the computationally intensive stages of the workflow.

The parallelization strategy is designed around the workload structure rather than simply distributing the entire simulation across processors. Different stages use different communicator configurations depending on the number of tasks and atoms involved.

### 1. Spatial decomposition for defect identification

During defect identification, the atoms of the complete simulation system are distributed across processors.

```text
             Full Simulation Cell
        ┌─────────────────────────┐
        │                         │
        │   atoms distributed     │
        │   across processors     │
        │                         │
        └─────────────────────────┘

        P0        P1        P2       P3
       atoms     atoms     atoms    atoms
```

This provides a direct **spatial decomposition** of the atomistic system and allows defect identification to operate concurrently on different portions of the system.

### 2. Parallelization over Active Volumes

For saddle-point searching, each active volume can generate multiple independent search tasks.

If there are `nAV` active volumes and `nSPS` saddle-point-search attempts per AV:

```text
Total tasks = nAV × nSPS
```

These tasks can be distributed among processor groups, with the number of processors assigned to each task controlled through the force-evaluator configuration.

```text
                 MPI Processes
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      AV 1           AV 2           AV 3
        │              │              │
    ┌───┼───┐      ┌───┼───┐      ┌───┼───┐
    │   │   │      │   │   │      │   │   │
   SPS SPS SPS    SPS SPS SPS    SPS SPS SPS
```

This task decomposition is particularly effective because saddle-point searches on different AVs are largely independent.

### 3. Optional Master–Slave Scheduling

SEAKMC also supports an optional **master–slave parallelization scheme**.

Without dynamic scheduling, processors may have to wait for the slowest task in a batch:

```text
Task 1 ────────────────
Task 2 ───────
Task 3 ───────────────
Task 4 ───────────

              ↑
         idle processors
```

With the master–slave scheme, the master continuously assigns completed tasks to available slave groups:

```text
                     ┌── Task 1 ──► Group 1
                     │
Master ──────────────┼── Task 2 ──► Group 2
                     │
                     ├── Task 3 ──► Group 3
                     │
                     └── Task 4 ──► available group
```

This reduces processor idle time when individual saddle-point searches have substantially different computational costs.

## SEAKMC Workflow

A typical SEAKMC simulation follows the sequence:

```text
Input / Restart / Defect Bank
              │
              ▼
        MD / Relaxation
              │
              ▼
      Defect Identification
              │
              ▼
       Active Volume Setup
              │
              ▼
      Preload Existing SPs
              │
              ▼
       Scale Normal Coordinates
              │
              ▼
   Parallel Saddle-Point Search
              │
              ▼
         AV Relaxation
              │
              ▼
        Validate SPs
              │
              ▼
      Post-process SPs
              │
              ▼
        Recycle SPs
              │
              ▼
      Energy Recalibration
              │
              ▼
          KMC / LEB
              │
              ▼
       System Relaxation
              │
              └──────────────► Repeat
```

## Energy and Force Evaluation

SEAKMC itself does **not** provide an energy or force evaluator. It provides a Python interface to LAMMPS through **pyLAMMPS**, allowing LAMMPS-based interatomic potentials to be used with the SEAKMC framework.

The framework can also be extended to incorporate other energy and force evaluators.

## Installation

SEAKMC requires Python, `pymatgen`, `mpi4py`, and an energy/force evaluator such as LAMMPS.

A typical environment can be prepared with:

```bash
conda create -p path_to_seakmc_env/seakmc_env
conda activate path_to_seakmc_env/seakmc_env

conda install conda-forge::lammps=*=*openmpi*
conda install openkim-models
conda install --channel conda-forge pymatgen
python -m pip install mpi4py==3.1.6
```

Install SEAKMC with:

```bash
python setup.py install
```

For the parallel version, install the corresponding parallel package.

## Running SEAKMC

### Serial

```bash
python run_seakmc.py
```

### MPI Parallel

For example:

```bash
mpirun -np 4 python run_seakmc_p.py
```

For HPC systems, the MPI launch command should be adapted to the cluster's MPI and job-scheduling environment.

## Output

SEAKMC can generate:

* `Seakmc.log`
* `Seakmc_summary.csv`
* Restart files
* Saddle-point information in `SPOut`
* Structure information in `DataOut`
* Defect-bank information in `DefectBank`
* Active-volume structures in `AVOut`

## Code Availability

The SEAKMC code is available on GitHub:

* **Serial version:** [SEAKMC_py](https://github.com/TaoLiang120/SEAKMC_py)
* **Parallel version:** [SEAKMC_py_parallel](https://github.com/TaoLiang120/SEAKMC_py_parallel)

## Citation

If you use SEAKMC or its dynamic active-volume methodology in your research, please cite:

> Tao Liang and Haixuan Xu, *Saddle point search with dynamic active volume*, Computational Materials Science **228**, 112354 (2023).

DOI: https://doi.org/10.1016/j.commatsci.2023.112354

## License

SEAKMC is distributed under the **BSD-3-Clause License**.

See the [`LICENSE`](LICENSE) file for details.

## Authors

**Tao Liang**
**Haixuan Xu**
