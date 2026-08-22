"""Accelerator (GPU/KOKKOS) command-line arguments.

SEAKMC computes no forces itself; these flags are handed to LAMMPS verbatim.
The builder previously had an else-branch referencing a variable bound only in
the if-branch, so an unrecognised key raised NameError, and one appearing
after a valid key silently appended the previous key's value instead.
"""

import sys
import types

import pytest

from seakmc.exceptions import SeakmcError
from seakmc.runner.PyLammpsRunner import PyLammpsRunner, Valid_GPU_args


@pytest.fixture
def build(monkeypatch):
    """Return a function that yields the cmdargs init_binary would pass to LAMMPS.

    init_binary imports lammps inside the function body, so the stub has to be
    installed in sys.modules rather than patched onto the runner module.
    """
    captured = {}

    def fake_lammps(cmdargs=None, comm=None):
        captured["args"] = list(cmdargs or [])
        return object()

    stub = types.ModuleType("lammps")
    stub.lammps = fake_lammps
    monkeypatch.setitem(sys.modules, "lammps", stub)

    runner = PyLammpsRunner.__new__(PyLammpsRunner)   # skip __init__; needs settings

    def _build(**kwargs):
        captured.clear()
        runner.init_binary(**kwargs)
        return captured["args"]

    return _build


def test_valid_flags_are_passed_through(build):
    args = build(**{"-sf": "gpu", "-pk": "gpu, 1"})
    assert "-sf" in args and "-pk" in args
    assert args.count("gpu") == 2      # one per flag
    assert "1" in args                 # comma-separated value split and stripped


def test_unknown_flag_is_rejected_clearly(build):
    """Previously NameError; now a SeakmcError naming the offending key."""
    with pytest.raises(SeakmcError, match="-bogus"):
        build(**{"-bogus": "x"})


def test_unknown_flag_after_a_valid_one_does_not_silently_duplicate(build):
    """The old code appended the previous key's value here instead of failing."""
    with pytest.raises(SeakmcError):
        build(**{"-sf": "gpu", "-bogus": "zzz"})


def test_no_accelerator_flags_still_builds(build):
    args = build()
    assert args[:2] == ["-screen", "none"]
    assert not any(a in Valid_GPU_args for a in args)


def test_every_valid_flag_is_accepted(build):
    for flag in Valid_GPU_args:
        args = build(**{flag: "gpu"})
        assert flag in args
