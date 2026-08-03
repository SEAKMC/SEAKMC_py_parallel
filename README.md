# SEAKMC_py_parallel

**Self-Evolving Atomistic Kinetic Monte Carlo — Parallel Python Implementation**

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: BSD](https://img.shields.io/badge/License-BSD-green.svg)](LICENSE)

SEAKMC_py_parallel (`seakmc_p`) is a massively parallel Python implementation of the **Self-Evolving Atomistic Kinetic Monte Carlo (SEAKMC)** method for simulating long-timescale atomistic kinetic processes in materials — such as defect migration, clustering, and microstructural evolution — *without* predefined event catalogs.

---

## Table of Contents

- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Input Configuration](#input-configuration)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Citation](#citation)
- [License](#license)
- [Contact](#contact)

---

## Key Features

- **On-the-fly saddle point discovery** — No predefined event catalog required. Transition states are found dynamically using the **Dimer method**.
- **Active Volume decomposition** — Computationally expensive searches are localized to spatial regions around defects (Active Volumes), enabling simulation of large bulk systems.
- **MPI-based parallelism** — Dynamic MPI communicator splitting distributes multiple Active Volume searches and Dimer runs concurrently across worker tasks.
- **Defect Bank recycling** — Previously discovered defect displacement patterns are cached and recycled across KMC steps to accelerate convergence.
- **Crystal symmetry exploitation** — Point group and space group symmetry operations reduce redundant saddle point searches.
- **Vineyard HTST prefactors** — Harmonic Transition State Theory rate prefactors are computed via dynamical matrix diagonalization (LAPACK).
- **SuperBasin acceleration** — Low-barrier flickering transitions are handled by grouping trapped states into SuperBasins and solving the transition matrix for mean residence times.
- **Multiple force evaluator backends** — Seamlessly switch between:
  - **LAMMPS** (standalone binary via system calls)
  - **PyLAMMPS** (in-process Python bindings, zero file I/O)
  - **VASP** (ab-initio DFT)
- **Checkpoint/restart support** — Full simulation state is serialized via `pickle` for fault-tolerant long-running simulations.

---

## How It Works

SEAKMC evolves an atomistic system through four main stages at each KMC step:

```
┌─────────────────────────────────────────────────────────┐
│  1. PREPROCESS                                          │
│     • Read input.yaml & atomic structure                │
│     • Initialize MPI communicators & working folders    │
│     • Perform initial relaxation or MD                  │
│     • Check for restart files                           │
├─────────────────────────────────────────────────────────┤
│  2. DEFECT IDENTIFICATION & ACTIVE VOLUME CONSTRUCTION  │
│     • Detect point defects / interstitials / vacancies  │
│     • Build Active Volumes around defect centers        │
│     • Partition atoms into active, buffer, and fixed    │
├─────────────────────────────────────────────────────────┤
│  3. PARALLEL SADDLE POINT SEARCH                        │
│     • Dispatch AV searches across MPI sub-communicators │
│     • Load seed displacements from DefectBank           │
│     • Run Dimer searches to locate saddle points        │
│     • Apply symmetry operations & screen results        │
│     • Calculate Vineyard HTST prefactors                │
├─────────────────────────────────────────────────────────┤
│  4. KMC EVENT SELECTION & STATE UPDATE                  │
│     • Calculate escape rates: k = ν₀·exp(−Eₐ/kᵦT)     │
│     • Form SuperBasin if trapped states detected        │
│     • Select event via stochastic sampling              │
│     • Advance simulation time                           │
│     • Apply displacement & relax to new minimum         │
│     • Write outputs & restart checkpoint                │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture

```
seakmc_p/
├── core/           # Atomistic data structures, box geometry, Active Volumes, symmetry
├── datasps/        # Master/worker parallel SPS scheduler, pre/post-processing, recalibration
├── dynmat/         # Dynamical matrix, Hessian, vibrational frequencies, HTST prefactors
├── general/        # Logging, CSV summary writers, output formatting, object factory
├── input/          # YAML input parser, settings validation, global parameters
├── kmc/            # Basin & SuperBasin rate calculation, KMC event selection engine
├── mpiconf/        # MPI communicator splitting, task partitioning, error handling
├── process/        # High-level controllers: preprocess, main KMC loop, postprocess
├── restart/        # Checkpoint serialization & deserialization
├── runner/         # Force evaluator interfaces: LAMMPS, PyLAMMPS, VASP
└── spsearch/       # Dimer method, SaddlePoint objects, DefectBank storage
```

### Key Classes

| Class | Module | Description |
|---|---|---|
| `SeakmcData` | `core.data` | Full atomistic system representation (atoms, masses, velocities, defects) |
| `ActiveVolume` | `core.data` | Localized region around a defect with active/buffer/fixed atoms |
| `Dimer` | `spsearch.SPSearch` | Dimer method implementation for saddle point location |
| `SaddlePoint` | `spsearch.SaddlePoints` | Single saddle point with barriers, prefactor, and connectivity |
| `DefectBank` | `spsearch.SaddlePoints` | Database of reusable defect displacement patterns |
| `DynMat` / `VibMats` | `dynmat.Dynmat` | Dynamical matrix and Vineyard prefactor computation |
| `Basin` / `SuperBasin` | `kmc.KMC` | KMC rate calculation and trapped-state acceleration |
| `Settings` | `input.Input` | Configuration container loaded from `input.yaml` |
| `RESTART` | `restart.Restart` | Simulation state checkpoint for fault tolerance |
| `LammpsRunner` | `runner` | Standalone LAMMPS force evaluator |
| `PyLammpsRunner` | `runner` | In-process PyLAMMPS force evaluator |
| `VaspRunner` | `runner` | VASP DFT force evaluator |

---

## Requirements

- Python ≥ 3.8
- [NumPy](https://numpy.org/) ≥ 1.26.0
- [SciPy](https://scipy.org/) ≥ 1.10.1
- [pandas](https://pandas.pydata.org/) ≥ 2.0.1
- [mpi4py](https://mpi4py.readthedocs.io/) ≤ 3.1.6
- [monty](https://github.com/materialsvirtuallab/monty) ≥ 2023.4.10
- [pymatgen](https://pymatgen.org/) ≥ 2023.11.12
- [PyYAML](https://pyyaml.org/) ≥ 6.0
- [LAMMPS](https://www.lammps.org/) (Python package) ≥ 2023.03.28
- [setuptools](https://setuptools.pypa.io/) ≥ 67.7.2

---

## Installation

### From Source

```bash
git clone https://github.com/TaoLiang120/SEAKMC_py_parallel.git
cd SEAKMC_py_parallel
pip install -e .
```

### Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `mpi4py` requires a working MPI installation (e.g., OpenMPI, MPICH). The `lammps` Python package requires LAMMPS to be compiled as a shared library.

---

## Quick Start

1. **Prepare your input files:**
   - An atomic structure data file (LAMMPS data format)
   - A LAMMPS input script (e.g., `in.lammps`) with your interatomic potential
   - An `input.yaml` configuration file (see [Input Configuration](#input-configuration))

2. **Run with MPI:**

```bash
mpirun -np <nprocs> python run_seakmc_p.py
```

Or, if installed as a console script:

```bash
mpirun -np <nprocs> seakmc_p
```

### Minimal Run Script

```python
from seakmc_p.input.Input import Settings
from seakmc_p.process.Preprocess import preprocess
from seakmc_p.process.Process import run_seakmc
from seakmc_p.process.Postprocess import postprocess

if __name__ == "__main__":
    settings = Settings.from_file("input.yaml")
    preprocess(settings)
    run_seakmc(settings)
    postprocess(settings)
```

---

## Input Configuration

All simulation parameters are specified in a single `input.yaml` file. Key configuration sections include:

| Section | Description |
|---|---|
| **System** | Atomic structure file, atom style, species, and box dimensions |
| **ForceEvaluator** | Force evaluator backend (`lammps`, `pylammps`, or `vasp`), potential definition, and LAMMPS input script |
| **KMC** | Temperature, number of KMC steps, transient energy cuts |
| **ActiveVolume** | Cutoff radii for active/buffer regions, defect detection parameters |
| **DimerSearch** | Dimer method parameters (convergence, step sizes, max iterations) |
| **DynMat** | Dynamical matrix calculation settings, displacement magnitude |
| **DefectBank** | Defect pattern storage and recycling options |
| **SuperBasin** | SuperBasin detection and grouping criteria |
| **Output** | Visualization data, summary CSV, and restart checkpoint options |

A complete annotated example is provided at [`run_script/input.yaml`](run_script/input.yaml).

---

## Examples

The [`examples/`](examples/) directory contains ready-to-run demonstrations:

| Example | Description |
|---|---|
| [`Fe_vacancy`](examples/Fe_vacancy) | Iron vacancy defect migration with EAM potential — includes sample data, potential file, and expected outputs |
| [`GuidedSPS`](examples/GuidedSPS) | Guided saddle point search with pre-generated displacement seeds |
| [`ImportOutput`](examples/ImportOutput) | Importing existing relaxation/output configurations |
| [`SelectedDefects`](examples/SelectedDefects) | SEAKMC on selected defect complexes (e.g., dumbbell + vacancy) |
| [`Use_calllammps`](examples/Use_calllammps) | Using standalone LAMMPS/VASP via system call scripts |

Sample LAMMPS input scripts are also provided:
- [`examples/in.sample.lammps`](examples/in.sample.lammps) — Standalone LAMMPS mode
- [`examples/in.sample.pylammps`](examples/in.sample.pylammps) — PyLAMMPS in-process mode

---

## Project Structure

```
SEAKMC_py_parallel/
├── seakmc_p/                  # Main package
│   ├── __init__.py
│   ├── core/                  # Data structures, box, Active Volumes, symmetry
│   ├── datasps/               # Parallel SPS scheduling & data management
│   ├── dynmat/                # Dynamical matrix & HTST prefactors
│   ├── general/               # Logging, output writers, object factory
│   ├── input/                 # YAML input parsing & settings
│   ├── kmc/                   # KMC engine, Basin, SuperBasin
│   ├── mpiconf/               # MPI communicator management
│   ├── process/               # Preprocess, main loop, postprocess
│   ├── restart/               # Checkpoint/restart serialization
│   ├── runner/                # Force evaluator backends
│   └── spsearch/              # Dimer method, SaddlePoints, DefectBank
├── examples/                  # Example simulations & sample inputs
├── run_script/                # Run script & sample input.yaml
├── modify_molecule_id.py      # Utility to modify atom molecule-IDs
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── SEAKMC_MANUAL.pdf          # User manual
├── LICENSE                    # BSD License
└── README.md                  # This file
```

---

## Citation

If you use SEAKMC_py_parallel in your research, please cite the relevant publications describing the SEAKMC method. See the [`SEAKMC_MANUAL.pdf`](SEAKMC_MANUAL.pdf) for citation details and methodology references.

---

## License

This project is licensed under the **BSD License** — see the [LICENSE](LICENSE) file for details.

Copyright © 2019, Tao Liang. All rights reserved.

---

## Contact

**Tao Liang**
- GitHub: [@TaoLiang120](https://github.com/TaoLiang120)
- Email: xhtliang120@gmail.com
