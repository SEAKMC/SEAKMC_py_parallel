"""Provenance record for a run.

A seed is only half of reproducibility: repeating a run also needs to know
which code, which settings, and which interatomic potential produced it.
This writes that record next to Seakmc_summary.csv as JSON, once per run.

Deliberately best-effort. A manifest that raised because git was missing, or
because a potential file sat on a filesystem it could not stat, would abort a
simulation over bookkeeping.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys


def _sha256(path, limit=None):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            read = 0
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
                read += len(chunk)
                if limit and read >= limit:
                    break
        return h.hexdigest()
    except Exception:
        return None


def _git_sha():
    try:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(["git", "-C", here, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            sha = out.stdout.strip()
            dirty = subprocess.run(["git", "-C", here, "status", "--porcelain"],
                                   capture_output=True, text=True, timeout=5)
            return sha + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:
        pass
    return None


def _versions():
    out = {}
    for name in ("numpy", "scipy", "pandas", "pymatgen", "monty", "mpi4py", "lammps"):
        try:
            out[name] = getattr(__import__(name), "__version__", "unknown")
        except Exception:
            out[name] = None
    return out


def build_manifest(sett, seed, nproc, extra=None):
    import seakmc
    pot = sett.potential.get("FileName") if isinstance(sett.potential, dict) else None
    potpath = pot if isinstance(pot, str) and os.path.isfile(pot) else None
    data = sett.data.get("FileName") if isinstance(sett.data, dict) else None
    datapath = data if isinstance(data, str) and os.path.isfile(data) else None

    manifest = {
        "seakmc_version": getattr(seakmc, "__version__", "unknown"),
        "git_sha": _git_sha(),
        "random_seed": seed,
        "nproc": nproc,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "dependencies": _versions(),
        "force_evaluator": {
            "style": sett.force_evaluator.get("Style"),
            "bin": sett.force_evaluator.get("Bin"),
        },
        "potential": {"file": pot, "sha256": _sha256(potpath) if potpath else None},
        "structure": {"file": data, "sha256": _sha256(datapath) if datapath else None},
        "kinetic_MC": {
            "NSteps": sett.kinetic_MC.get("NSteps"),
            "Temp": sett.kinetic_MC.get("Temp"),
            "AccStyle": sett.kinetic_MC.get("AccStyle"),
        },
        "spsearch": {
            "Method": sett.spsearch.get("Method"),
            "NSearch": sett.spsearch.get("NSearch"),
        },
    }
    if extra:
        manifest.update(extra)
    return manifest


def write_manifest(path, sett, seed, nproc, extra=None):
    """Write the manifest to ``path``. Never raises."""
    try:
        with open(path, "w") as f:
            json.dump(build_manifest(sett, seed, nproc, extra=extra), f, indent=2, default=str)
        return path
    except Exception:
        return None
