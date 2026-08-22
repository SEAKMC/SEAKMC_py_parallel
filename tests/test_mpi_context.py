"""The lazily-resolved MPI context.

These tests exist because the package used to bind rank and size into module
globals at import, which made the communicator un-substitutable and the
package un-importable without an MPI runtime.
"""

import pkgutil
import importlib

import pytest

import seakmc
from seakmc.mpiconf.context import MPIContext, _SerialComm, mpi, default_nproc_task


def test_every_module_imports():
    """No module may require MPI (or a force evaluator) merely to be imported."""
    names = sorted(m.name for m in pkgutil.walk_packages(seakmc.__path__, "seakmc."))
    assert len(names) > 30
    for name in names:
        importlib.import_module(name)


def test_no_module_imports_mpi4py_at_module_scope():
    """Guard against the import-time binding creeping back in."""
    import ast, pathlib
    root = pathlib.Path(seakmc.__file__).parent
    offenders = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:                      # module scope only
            if isinstance(node, ast.ImportFrom) and node.module == "mpi4py":
                offenders.append(str(path.relative_to(root)))
    assert offenders == [], f"mpi4py imported at module scope in: {offenders}"


def test_serial_context_reports_one_rank():
    ctx = MPIContext()
    ctx.use(_SerialComm())
    assert ctx.has_mpi is False
    assert (ctx.rank, ctx.size) == (0, 1)
    assert ctx.is_root


def test_serial_collectives_are_identities():
    c = _SerialComm()
    assert c.bcast({"a": 1}) == {"a": 1}
    assert c.allgather(7) == [7]
    assert c.Barrier() is None
    assert c.Split(0) is c


def test_serial_point_to_point_is_refused_not_silently_wrong():
    """A serial stub must not pretend to deliver messages."""
    c = _SerialComm()
    with pytest.raises(RuntimeError):
        c.send(object(), dest=1)
    with pytest.raises(RuntimeError):
        c.recv(source=1)


def test_context_can_be_substituted_and_reset():
    ctx = MPIContext()
    ctx.use(_SerialComm())
    assert ctx.size == 1
    ctx.reset()
    assert ctx._resolved is False


def test_default_nproc_task_matches_the_original_arithmetic():
    """Previously computed at import time in Input.py from a module-level
    size_world. Same arithmetic, now resolved per call.

    Checked against an independent transcription of the original block rather
    than hand-computed values, so the test cannot drift from what it replaced.
    """
    import numpy as np

    def original(size_world):
        n = int(np.log(size_world) / np.log(2))
        nleft = size_world - int(np.power(2, n))
        if n >= 4 and nleft >= np.power(2, n - 1):
            return int(np.power(2, n - 1) * 3)
        return int(np.power(2, n))

    for size in range(1, 129):
        assert default_nproc_task(size) == original(size), size


def test_default_nproc_task_handles_a_single_rank():
    """log(1)/log(2) is 0, and the serial case must not raise."""
    assert default_nproc_task(1) == 1


def test_module_level_context_is_usable():
    assert isinstance(mpi.rank, int)
    assert mpi.size >= 1
