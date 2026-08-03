# PR description: fast barrier scan workflow for parallel SEAKMC

## Summary

This PR adds several optional features to improve the efficiency of SEAKMC calculations for fast migration-barrier scanning in the parallel `seakmc_p` workflow.

The target use case is scanning the anisotropic migration barriers of point defects, such as a single vacancy, placed at different positions around a microstructural feature. In this workflow, one usually starts from a relaxed atomic configuration without the target defect, then constructs the target defect at a selected position and searches for the corresponding migration barriers.

For the defect-containing structure, an initial relaxation is still needed. However, the previous workflow only supports global relaxation when `Relaxed: false`, which can be expensive for large systems. Since a single point defect usually affects only a local region, this PR adds an active-volume-only initial relaxation mode. This allows the initial relaxation to be limited to the active volume and reduces the cost of preparing each scan configuration.

In addition, when only migration barriers are needed, the final-state relaxation after the KMC step is unnecessary. This PR adds an option to skip that final relaxation. Optional timing diagnostics are also added to help identify performance bottlenecks.

Using these features, in a 9-core parallel run for single-vacancy migration-barrier calculations, the wall time was reduced from about 520 s to about 69 s.

## New features

### 1. `data.InitialRelaxActiveOnly`

A new input option:

```yaml
data:
    InitialRelaxActiveOnly: true
```

Default:

```yaml
data:
    InitialRelaxActiveOnly: false
```

When enabled, the initial global `DATAMD` / `DATAOPT` relaxation is skipped. SEAKMC first constructs active volumes and then performs local initial-state relaxation only within each active volume using the existing `SPSRELAX` pathway.

This mode is intended for cases where the input structure is already relaxed before inserting the target defect, and only the local environment around the inserted defect needs to be relaxed.

An optional input can use a different active radius only for this initial local relaxation:

```yaml
data:
    InitialRelaxActiveOnly: true
    DActive4InitialRelax: 45.0

active_volume:
    DActive: 15.0
```

When `DActive4InitialRelax` is set, the initial `SPSRELAX` active volume is built with that radius, then `active_volume.DActive` is restored and the formal active volumes are rebuilt before data output, saddle searches, and KMC. If `DActive4InitialRelax` is omitted or `false`, the workflow is unchanged and the initial local relaxation uses `active_volume.DActive`.

In the parallel implementation, all MPI ranks participate in the local `SPSRELAX` calculation through `MPI.COMM_WORLD`, following the mature workflow used in the previous fast-scan implementation.

For compatibility and safety, this mode is currently rejected when used together with:

```yaml
data:
    MoleDyn: true

saddle_point:
    CalBarrsInData: true

force_evaluator:
    TrialDisps2Basin:
        TrialDisps2Basin: true
```

These restrictions avoid silently mixing incompatible initial-relaxation and basin-preparation pathways.

### 2. `data.CropInputForActiveRelax`

A new optional input-cropping feature:

```yaml
data:
    InitialRelaxActiveOnly: true
    CropInputForActiveRelax:
        Enable: true
        OutputFile: data.cropped.dat
        Ranges:
            - [-80, 80]
            - [-80, 80]
            - [-80, 80]
        SummaryFile: scan_input_summary.json
```

Default:

```yaml
data:
    CropInputForActiveRelax:
        Enable: false
```

This option is only allowed when `InitialRelaxActiveOnly: true`.

When `DActive4InitialRelax` is used together with cropped input, the crop must include all atoms required by the initial active-volume relaxation, not only the formal saddle-search active volume. In practice the cropped structure should cover at least `DActive4InitialRelax + DBuffer + DFixed` around each relaxed defect center. The runtime log prints this required margin when cropping is enabled.

When enabled, SEAKMC crops the original LAMMPS data file using absolute x/y/z coordinate ranges, writes the cropped data file next to `input.yaml`, and then uses the cropped file as the input for the subsequent calculation.

This avoids reading and processing the full global atomic configuration when only local active-volume relaxation and barrier scanning are needed.

For the automatic workflow, the crop output is overwritten if it already exists, atom IDs are reindexed to `1..N`, and coordinates are written with four decimal places. These details are fixed internally to keep the input file simple.

The cropping utility is implemented as a separate script/module:

```bash
python -m seakmc_p.process.CropInput --input data.dat --output data.cropped.dat --ranges -80 80 -80 80 -80 80
```

It supports atom ID reindexing, coordinate precision control, and JSON summary output when used as a standalone utility.

### 3. `kinetic_MC.RelaxAfterKMC`

A new input option:

```yaml
kinetic_MC:
    RelaxAfterKMC: false
```

Default:

```yaml
kinetic_MC:
    RelaxAfterKMC: true
```

When set to `false`, SEAKMC still writes the KMC probability and saddle-point information, but skips the final coordinate update and subsequent `OPT` relaxation after the KMC step.

This is useful for fast barrier-scanning workflows where the goal is to collect migration barriers rather than advance a full KMC trajectory.

### 4. Optional timing diagnostics

A lightweight timing utility was added. Timing output is disabled by default and can be enabled with:

```bash
export SEAKMC_TIMING_DETAIL=1
```

or in PowerShell:

```powershell
$env:SEAKMC_TIMING_DETAIL="1"
```

This prints timing information for selected preprocessing, active-volume relaxation, data-dynamics, and fast-scan exit steps, which helps diagnose performance bottlenecks.

## Default behavior

All new features are disabled by default.

Existing input files should continue to follow the original SEAKMC parallel workflow unless the new options are explicitly enabled.

## Example fast barrier scan configuration

```yaml
data:
    Relaxed: true
    InitialRelaxActiveOnly: true
    CropInputForActiveRelax:
        Enable: true
        OutputFile: data.cropped.dat
        Ranges:
            - [-80, 80]
            - [-80, 80]
            - [-80, 80]
        SummaryFile: scan_input_summary.json

kinetic_MC:
    RelaxAfterKMC: false
```

## Main changed files

- `seakmc_p/input/Input.py`
  - Adds defaults and validation for `InitialRelaxActiveOnly`, `CropInputForActiveRelax`, and `RelaxAfterKMC`.

- `seakmc_p/process/Preprocess.py`
  - Adds optional input cropping before reading the LAMMPS data file.
  - Skips the initial global `DATAMD` / `DATAOPT` relaxation when `InitialRelaxActiveOnly` is enabled.

- `seakmc_p/process/Process.py`
  - Adds active-volume-only initial relaxation using the existing `SPSRELAX` pathway with all MPI ranks participating.
  - Adds the early return path for `RelaxAfterKMC: false` after saddle-point and probability outputs.

- `seakmc_p/process/CropInput.py`
  - Adds a standalone LAMMPS data cropping utility using absolute x/y/z ranges.

- `seakmc_p/process/DataDyn.py`
  - Adds optional timing output for data-dynamics calls.

- `seakmc_p/general/Timing.py`
  - Adds lightweight timing helpers controlled by `SEAKMC_TIMING_DETAIL`.

- `run_script/input.yaml` and `run_script/input.yaml.compact`
  - Adds example input options with default behavior disabled.

- `.gitignore`
  - Adds ignores for cache files, temporary files, and SEAKMC output directories.

## Tests

The following checks were performed:

```bash
python3 -m compileall -q seakmc_p
```

A manual crop test was performed on a large LAMMPS data file:

- input atom count: 1,997,108
- crop range: `[-80, 80]` Å in x/y/z
- output atom count: 357,917
- atom IDs were reindexed to `1..N`
- output data file format was checked manually

A 9-core parallel SEAKMC fast barrier scan test was also performed for single-vacancy migration-barrier calculations. With the new options enabled, the wall time decreased from about 520 s to about 69 s.

## Notes

The new features are intended for local barrier-scanning workflows. They are not intended to replace the default KMC trajectory workflow. For standard KMC simulations, the default settings should be kept unchanged:

```yaml
data:
    InitialRelaxActiveOnly: false
    CropInputForActiveRelax:
        Enable: false

kinetic_MC:
    RelaxAfterKMC: true
```
