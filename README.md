# SEAKMC_py_parallel

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD-green.svg)](LICENSE)

**Self-Evolving Atomistic Kinetic Monte Carlo (SEAKMC)** is a Python-based atomistic simulation framework for exploring long-timescale material evolution using kinetic Monte Carlo (KMC). SEAKMC constructs saddle-point/event catalogs on the fly and enables efficient sampling of the potential energy landscape through **spatial decomposition into localized active volumes (AVs)** and **MPI-based parallel saddle-point searches**. **SEAKMC** is designed for studying defect evolution, diffusion, irradiation effects, phase transformations, and microstructural evolution in materials.

SEAKMC is free to use. We welcome contributions to help improve this library, including new tools or modules, feature requests, bug reports, and other suggestions.

- [User Manual][SEAKMC Manual]
- Bug reports or feature requests: Please submit a [GitHub issue].
- Code contributions via [pull request] are welcome.

[SEAKMC Manual]: https://github.com/SEAKMC/SEAKMC_py_parallel/blob/main/SEAKMC_MANUAL.pdf
[pull request]: https://github.com/SEAKMC/SEAKMC_py_parallel/pulls
[github issue]: https://github.com/SEAKMC/SEAKMC_py_parallel/issues

---

## Key Features

- **On-the-fly saddle point discovery** — No predefined event catalog required.
- **Active Volume decomposition** — Computationally expensive searches are localized to spatial regions around defects (Active Volumes), enabling simulation of large bulk systems.
- **MPI-based parallelism** — Dynamic MPI communicator splitting distributes multiple saddle point searches concurrently across worker tasks.
- **Defect Bank recycling** — Previously discovered defect displacement patterns are cached and recycled across KMC steps to accelerate convergence.
- **Crystal symmetry exploitation** — Point group and space group symmetry operations reduce redundant saddle point searches.
- **Vineyard HTST prefactors** — Harmonic Transition State Theory rate prefactors are computed via dynamical matrix diagonalization (LAPACK).
- **SuperBasin acceleration** — Low-barrier flickering transitions are handled by grouping trapped states into SuperBasins and solving the transition matrix for mean residence times.
- **Multiple force evaluator backends** — Seamlessly switch between:
  - **LAMMPS** (standalone binary via system calls)
  - **PyLAMMPS** (in-process Python bindings, zero file I/O)
  - **VASP** (ab-initio DFT)
  - **JAX-MD** *(planned — not yet implemented)*
- **Checkpoint/restart support** — Full simulation state is serialized via `pickle` for fault-tolerant long-running simulations.

---

## Why Spatial Decomposition?

Saddle points are typically associated with localized atomic rearrangements around defects. Instead of performing saddle-point searches on the entire simulation cell, the system is decomposed into localized **active volumes**[1], each treated as an independent subsystem.

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

The **Dynamic Active Volume (DAV)**[2] further reduces the number of active degrees of freedom by deactivating atoms that are not important to the saddle-point search. This improves both computational efficiency and the ability to identify relevant saddle points.
1. H. Xu, Y. N. Osetsky, and R. E. Stoller, "Self-evolving atomistic kinetic Monte Carlo: fundamentals and applications", Journal of Physics: Condensed Matter 24, 375402 (2012). DOI: https://doi.org/10.1088/0953-8984/24/37/375402
2. T. Liang and H. Xu, "Saddle point search with dynamic active volume", Computational Materials Science 228, 112354 (2023). DOI: https://doi.org/10.1016/j.commatsci.2023.112354
---

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

---

## Energy and Force Evaluation

SEAKMC itself does **not** provide an energy or force evaluator. It provides a Python interface to **pyLAMMPS**, **LAMMPS**, and **VASP**. The interface to **JAX-MD** is under development.

The framework can also be extended to incorporate other energy and force evaluators.
---

## Requirements

- Python ≥ 3.10
- [NumPy](https://numpy.org/) ≥ 1.26.0
- [SciPy](https://scipy.org/) ≥ 1.10.1
- [pandas](https://pandas.pydata.org/) ≥ 2.0.1
- [mpi4py](https://mpi4py.readthedocs.io/) ≤ 3.1.6
- [monty](https://github.com/materialsvirtuallab/monty) ≥ 2023.4.10
- [pymatgen](https://pymatgen.org/) ≥ 2023.11.12
- [PyYAML](https://pyyaml.org/) ≥ 6.0
- [setuptools](https://setuptools.pypa.io/) ≥ 67.7.2

Plus an energy/force evaluator, which SEAKMC does **not** provide — see
[Installation](#installation).

---

## Installation
Noting that SEAKMC itself does **not** provide an energy or force evaluator, the user must install a compatible energy/force evaluator package (e.g., `lammps`, `pylammps`, `vasp`, `jax-md`) before installing SEAKMC.
### From Source

```bash
git clone https://github.com/SEAKMC/SEAKMC_py_parallel.git
cd SEAKMC_py_parallel
pip install -e .
```

SEAKMC itself has no force evaluator. To pull in the LAMMPS Python module from
PyPI as well:

```bash
pip install -e ".[lammps]"
```

> **Note:** the PyPI `lammps` distribution is an unofficial third-party build.
> For production use, build LAMMPS as a shared library and install its own
> Python module — the integrated installer below does this for you.
### Integrated installer [Integrated installer]
The [Integrated installer] is an integrated bash script to install pyLAMMPS, Open-KIM force field, mpi4py, and SEAKMC.
```bash
bash integrated_installer.sh
```

[Integrated installer]: https://github.com/SEAKMC/SEAKMC_py_parallel/blob/main/integrated_installer.sh

> **Note:** `mpi4py` requires a working MPI installation (e.g., OpenMPI, MPICH). The `lammps` Python package requires LAMMPS to be compiled as a shared library.

---

## Quick Start

1. **Prepare your input files:**
   - An atomic structure data file (LAMMPS data format) 
   - An `input.yaml` configuration file (see [Input Configuration](#input-configuration))
   - The interatomic potential file(s) (e.g., `Fe-P.eam.fs`)
   - (Optional) A LAMMPS input script (e.g., `in.lammps`) with your interatomic potential
   
    > **Note:** The sample input files are available in each example in the [`examples/`](examples/) directory
2. **Run with MPI:**

```bash
mpirun -np <nprocs> python run_seakmc_p.py
```

Or, if installed as a console script:

```bash
mpirun -np <nprocs> seakmc_p
```
 > **Note:** run_seakmc_p.py is available in the [`run_script/`](run_script/) directory 

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


---

## History
SEAKMC was originally developed by Haixuan Xu in 2011 [1-4] and was subsequently advanced to incorporate angle-check methods for parallel saddle-point searches [5] and scaled normal-coordinate (SNC) [6]. Earlier versions of SEAKMC were written in Fortran, as shown in the [SEAKMC Legacy] project. In 2023, Tao Liang and Haixuan Xu introduced the concept of the dynamic active volume (DAV) [7] and rewrote SEAKMC in Python. The new implementation incorporates many advanced features, including dynamic and automatic active-volume characterization, parallel saddle-point searches, defect-bank recycling, superbasin acceleration based on the mean-rate method, user-defined spatial decomposition, and MPI-based parallelism.

[SEAKMC Legacy]: https://github.com/SEAKMC/SEAKMC_Legacy

1. H. Xu, Y. N. Osetsky, and R. E. Stoller, "Simulating complex atomistic processes: On-the-fly kinetic Monte Carlo scheme with selective active volumes", Physical Review B 84, 132103 (2011). DOI: https://doi.org/10.1088/0953-8984/24/37/375402
2. H. Xu, Y. N. Osetsky, and R. E. Stoller, "Self-evolving atomistic kinetic Monte Carlo: fundamentals and applications", Journal of Physics: Condensed Matter 24, 375402 (2012). DOI: https://doi.org/10.1088/0953-8984/24/37/375402
3. H. Xu, R. E. Stoller, L. K. Beland, and Y. N. Osetsky, "Self-Evolving Atomistic Kinetic Monte Carlo simulations of defects in materials", Computational Materials Science 100B (2015). DOI: https://doi.org/10.1016/j.commatsci.2014.12.026
4. A. Ervin and H. Xu, "Mesoscale simulations of radiation damage effects in Materials: A SEAKMC perspective", Computational Materials Science 150, 180 (2018). DOI: https://doi.org/10.1016/j.commatsci.2018.03.054
5. S. Hayakawa, J. Isaacs, H. R. Medal, and H. Xu, "Atomistic modeling of meso-timescale processes with SEAKMC: A perspective and recent developments", Computational Materials Science 194, 110390 (2021). DOI: https://doi.org/10.1016/j.commatsci.2021.110390
6. S. Hayakawa and H. Xu, "Saddle point sampling using scaled normal coordinates", Computational Materials Science 200, 110785 (2021). DOI: https://doi.org/10.1016/j.commatsci.2021.110785
7. T. Liang and H. Xu, "Saddle point search with dynamic active volume", Computational Materials Science 228, 112354 (2023). DOI: https://doi.org/10.1016/j.commatsci.2023.112354

---

## Citation

1. H. Xu, Y. N. Osetsky, and R. E. Stoller, "Self-evolving atomistic kinetic Monte Carlo: fundamentals and applications", Journal of Physics: Condensed Matter 24, 375402 (2012). DOI: https://doi.org/10.1088/0953-8984/24/37/375402

2. T. Liang and H. Xu, "Saddle point search with dynamic active volume", Computational Materials Science 228, 112354 (2023). DOI: https://doi.org/10.1016/j.commatsci.2023.112354

---

## License

This project is licensed under the **BSD-3-Clause** — see the [LICENSE](LICENSE) file for details.

---

## Contact
**Haixuan Xu**
- Email: xhx@utk.edu

**Tao Liang**
- GitHub: [@TaoLiang120](https://github.com/TaoLiang120)
- Email: xhtliang120@gmail.com
