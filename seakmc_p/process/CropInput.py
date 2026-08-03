"""Crop a LAMMPS data file before InitialRelaxActiveOnly scans.

This module is intentionally independent from the SEAKMC data object so it can
be used as a small preprocessing script before the main calculation reads the
cropped file. Only absolute x/y/z ranges are supported.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass
class LammpsDataFile:
    header: List[str]
    masses: List[str]
    atoms_header: str
    atoms: List[List[str]]
    atom_style: str
    box_lines: List[str]
    tilt_line: Optional[str]


def _is_section(line: str) -> bool:
    name = line.strip().split("#", 1)[0].strip()
    return name in {"Masses", "Atoms", "Velocities", "Bonds", "Angles", "Dihedrals", "Impropers"}


def _parse_atom_style(atoms_header: str, default: str) -> str:
    if "#" in atoms_header:
        style = atoms_header.split("#", 1)[1].strip().split()
        if style:
            return style[0]
    return default


def _coord_indices(atom_style: str) -> Tuple[int, int, int]:
    style = atom_style.lower()
    if style == "atomic":
        return 2, 3, 4
    if style == "molecular":
        return 3, 4, 5
    if style == "charge":
        return 3, 4, 5
    if style == "full":
        return 4, 5, 6
    raise ValueError(f"Unsupported atom_style for cropping: {atom_style!r}")


def read_lammps_data(path: os.PathLike[str] | str, atom_style: str = "atomic") -> LammpsDataFile:
    lines = Path(path).read_text().splitlines()
    header: List[str] = []
    masses: List[str] = []
    atoms: List[List[str]] = []
    atoms_header = "Atoms"
    box_lines: List[str] = []
    tilt_line: Optional[str] = None

    section: Optional[str] = None
    in_atoms = False
    in_masses = False
    saw_atoms = False

    for raw in lines:
        stripped = raw.strip()
        if not saw_atoms:
            if stripped.endswith("xlo xhi") or stripped.endswith("ylo yhi") or stripped.endswith("zlo zhi"):
                box_lines.append(stripped)
            elif stripped.endswith("xy xz yz"):
                tilt_line = stripped

        if stripped.startswith("Masses"):
            section = "Masses"
            in_masses = True
            in_atoms = False
            saw_atoms = saw_atoms or False
            continue
        if stripped.startswith("Atoms"):
            atoms_header = stripped
            section = "Atoms"
            in_atoms = True
            in_masses = False
            saw_atoms = True
            continue
        if _is_section(raw) and section not in {None, "Masses", "Atoms"}:
            section = stripped.split()[0]
            in_atoms = False
            in_masses = False
            continue
        if _is_section(raw) and section in {"Masses", "Atoms"} and not stripped.startswith(("Masses", "Atoms")):
            in_atoms = False
            in_masses = False
            section = stripped.split()[0]
            continue

        if in_masses:
            if stripped == "":
                continue
            if _is_section(raw):
                in_masses = False
                continue
            masses.append(stripped)
            continue

        if in_atoms:
            if stripped == "":
                continue
            if _is_section(raw):
                in_atoms = False
                continue
            atoms.append(stripped.split())
            continue

        if not saw_atoms:
            header.append(raw)

    style = _parse_atom_style(atoms_header, atom_style)
    if not atoms:
        raise ValueError(f"No Atoms section found in {path}")
    return LammpsDataFile(header, masses, atoms_header, atoms, style, box_lines, tilt_line)


def _normalize_ranges(ranges: Sequence[Sequence[float]]) -> List[Tuple[float, float]]:
    if len(ranges) != 3:
        raise ValueError("CropInputForActiveRelax.Ranges must contain three [lo, hi] pairs.")
    out: List[Tuple[float, float]] = []
    for pair in ranges:
        if len(pair) != 2:
            raise ValueError("Each crop range must be [lo, hi].")
        lo, hi = float(pair[0]), float(pair[1])
        if hi <= lo:
            raise ValueError(f"Invalid crop range [{lo}, {hi}]; hi must be larger than lo.")
        out.append((lo, hi))
    return out


def crop_atoms(data: LammpsDataFile, ranges: Sequence[Sequence[float]], reindex: bool = True,
               decimals: int = 4) -> Tuple[List[List[str]], List[Tuple[float, float]]]:
    bounds = _normalize_ranges(ranges)
    ix, iy, iz = _coord_indices(data.atom_style)
    cropped: List[List[str]] = []
    fmt = f"{{:.{int(decimals)}f}}"

    for atom in data.atoms:
        x, y, z = float(atom[ix]), float(atom[iy]), float(atom[iz])
        keep = bounds[0][0] <= x < bounds[0][1] and bounds[1][0] <= y < bounds[1][1] and bounds[2][0] <= z < bounds[2][1]
        if not keep:
            continue
        new_atom = list(atom)
        new_atom[ix] = fmt.format(x)
        new_atom[iy] = fmt.format(y)
        new_atom[iz] = fmt.format(z)
        cropped.append(new_atom)

    if reindex:
        for idx, atom in enumerate(cropped, start=1):
            atom[0] = str(idx)
    return cropped, bounds


def _format_box(bounds: Sequence[Tuple[float, float]]) -> List[str]:
    labels = ["xlo xhi", "ylo yhi", "zlo zhi"]
    return [f"{lo:.10f} {hi:.10f} {label}" for (lo, hi), label in zip(bounds, labels)]


def write_lammps_data(path: os.PathLike[str] | str, data: LammpsDataFile, atoms: List[List[str]],
                      bounds: Sequence[Tuple[float, float]]) -> None:
    output: List[str] = []
    wrote_atoms = False
    for raw in data.header:
        stripped = raw.strip()
        if stripped.endswith("atoms"):
            output.append(f"{len(atoms)} atoms")
        elif stripped.endswith("xlo xhi"):
            output.append(_format_box(bounds)[0])
        elif stripped.endswith("ylo yhi"):
            output.append(_format_box(bounds)[1])
        elif stripped.endswith("zlo zhi"):
            output.append(_format_box(bounds)[2])
        elif stripped.endswith("xy xz yz"):
            if data.tilt_line:
                output.append(raw)
        else:
            output.append(raw)

    if data.masses:
        if output and output[-1].strip() != "":
            output.append("")
        output.append("Masses")
        output.append("")
        output.extend(data.masses)

    if output and output[-1].strip() != "":
        output.append("")
    output.append(data.atoms_header)
    output.append("")
    for atom in atoms:
        output.append(" ".join(atom))
        wrote_atoms = True
    if not wrote_atoms:
        raise ValueError("Cropping produced zero atoms; refusing to write an empty data file.")
    Path(path).write_text("\n".join(output) + "\n")


def crop_lammps_data(input_file: os.PathLike[str] | str, output_file: os.PathLike[str] | str,
                     ranges: Sequence[Sequence[float]], atom_style: str = "atomic",
                     overwrite: bool = True, reindex: bool = True, coord_decimals: int = 4,
                     summary_file: Optional[os.PathLike[str] | str] = None) -> dict:
    input_path = Path(input_file)
    output_path = Path(output_file)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Crop output already exists: {output_path}")
    data = read_lammps_data(input_path, atom_style=atom_style)
    cropped, bounds = crop_atoms(data, ranges, reindex=reindex, decimals=coord_decimals)
    write_lammps_data(output_path, data, cropped, bounds)
    summary = {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "input_atom_count": len(data.atoms),
        "output_atom_count": len(cropped),
        "atom_style": data.atom_style,
        "bounds_A": {"x": list(bounds[0]), "y": list(bounds[1]), "z": list(bounds[2])},
        "atom_ids_reindexed": bool(reindex),
    }
    if summary_file:
        Path(summary_file).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def normalize_crop_settings(settings_dict: Optional[dict]) -> dict:
    defaults = {
        "Enable": False,
        "OutputFile": "data.cropped.dat",
        "Ranges": [[-80.0, 80.0], [-80.0, 80.0], [-80.0, 80.0]],
        "SummaryFile": "scan_input_summary.json",
    }
    if settings_dict is None:
        return defaults
    if isinstance(settings_dict, bool):
        defaults["Enable"] = bool(settings_dict)
        return defaults
    for key, value in settings_dict.items():
        defaults[key] = value
    defaults["Ranges"] = [list(pair) for pair in _normalize_ranges(defaults["Ranges"])]
    return defaults


def maybe_crop_input_for_active_relax(settings, input_yaml: os.PathLike[str] | str,
                                      rank_world: int = 0, comm_world=None, log_writer=None):
    crop_settings = normalize_crop_settings(settings.data.get("CropInputForActiveRelax"))
    settings.data["CropInputForActiveRelax"] = crop_settings
    if not crop_settings.get("Enable", False):
        return None
    if not settings.data.get("InitialRelaxActiveOnly", False):
        raise ValueError("data.CropInputForActiveRelax can only be enabled when data.InitialRelaxActiveOnly is true.")

    dactive_initial = settings.data.get("DActive4InitialRelax", False) or settings.active_volume["DActive"]
    required_margin = float(dactive_initial) + float(settings.active_volume["DBuffer"]) + float(settings.active_volume["DFixed"])
    if rank_world == 0 and log_writer is not None:
        log_writer.write_data(
            "CropInputForActiveRelax notice: with InitialRelaxActiveOnly, the cropped input must include all atoms "
            f"needed by the initial active-volume relaxation radius, i.e. at least DActive_initial + DBuffer + DFixed = "
            f"{required_margin} A around each relaxed defect center."
        )

    run_dir = Path(input_yaml).resolve().parent
    original_file = Path(settings.data["FileName"])
    if not original_file.is_absolute():
        original_file = run_dir / original_file
    output_file = Path(crop_settings["OutputFile"])
    if not output_file.is_absolute():
        output_file = run_dir / output_file
    summary_file = crop_settings.get("SummaryFile")
    if summary_file:
        summary_file = Path(summary_file)
        if not summary_file.is_absolute():
            summary_file = run_dir / summary_file

    summary = None
    if rank_world == 0:
        summary = crop_lammps_data(
            original_file,
            output_file,
            crop_settings["Ranges"],
            atom_style=settings.data.get("atom_style", "atomic"),
            overwrite=True,
            reindex=True,
            coord_decimals=4,
            summary_file=summary_file,
        )
        if log_writer is not None:
            log_writer.write_data(
                "CropInputForActiveRelax: wrote cropped input "
                f"{output_file.name} with {summary['output_atom_count']} atoms "
                f"from {summary['input_atom_count']} atoms."
            )
    if comm_world is not None:
        comm_world.Barrier()
        summary = comm_world.bcast(summary, root=0)
    settings.data["FileName"] = str(output_file)
    return summary


def _main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Crop a LAMMPS data file with absolute x/y/z ranges.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ranges", nargs=6, type=float, metavar=("XLO", "XHI", "YLO", "YHI", "ZLO", "ZHI"), required=True)
    parser.add_argument("--atom-style", default="atomic")
    parser.add_argument("--no-reindex", action="store_true")
    parser.add_argument("--coord-decimals", type=int, default=4)
    parser.add_argument("--summary-json", default=None)
    args = parser.parse_args(argv)
    ranges = [[args.ranges[0], args.ranges[1]], [args.ranges[2], args.ranges[3]], [args.ranges[4], args.ranges[5]]]
    summary = crop_lammps_data(args.input, args.output, ranges, atom_style=args.atom_style,
                               reindex=not args.no_reindex, coord_decimals=args.coord_decimals,
                               summary_file=args.summary_json)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
