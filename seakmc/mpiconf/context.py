"""Lazily-resolved MPI world.

Twenty-two modules used to execute this at import time::

    from mpi4py import MPI
    comm_world = MPI.COMM_WORLD
    rank_world = comm_world.Get_rank()
    size_world = comm_world.Get_size()

which had three costs. The package could not be imported at all without an
MPI runtime, so a notebook could not so much as look at a structure. The
communicator's identity was frozen into module state before any code ran, so
no test could substitute a stub. And ``Input.py`` went further, deriving a
scheduling decision (``nproc_this``) from ``size_world`` at import.

This module replaces those bindings with a single object whose attributes
resolve on first use. When mpi4py is absent or MPI is unavailable, it reports
a world of one rank and provides the small set of collectives SEAKMC calls on
a single rank, where each is a no-op or an identity. That is enough to import
the package, run the unit tests, and drive a serial calculation.

Real MPI runs are unaffected: ``mpi.comm`` is ``MPI.COMM_WORLD``.
"""

import numpy as np


class _SerialComm:
    """Enough of an MPI communicator to run on one rank without mpi4py."""

    def Get_rank(self):
        return 0

    def Get_size(self):
        return 1

    def Barrier(self):
        return None

    def bcast(self, obj, root=0):
        return obj

    def Split(self, color, key=0):
        return self

    def allgather(self, obj):
        return [obj]

    def Allgather(self, sendbuf, recvbuf):
        recvbuf[...] = sendbuf
        return recvbuf

    def Allreduce(self, sendbuf, recvbuf, op=None):
        recvbuf[...] = sendbuf
        return recvbuf

    def gather(self, obj, root=0):
        return [obj]

    def send(self, obj, dest=0, tag=0):
        raise RuntimeError("point-to-point messaging requires a real MPI runtime")

    def recv(self, source=0, tag=0, status=None):
        raise RuntimeError("point-to-point messaging requires a real MPI runtime")

    def Abort(self, code=1):
        raise SystemExit(code)

    def Free(self):
        return None


class MPIContext:
    """The process's MPI world, resolved on first access."""

    def __init__(self):
        self._comm = None
        self._resolved = False
        self._has_mpi = None

    def _resolve(self):
        if self._resolved:
            return
        try:
            from mpi4py import MPI
            self._comm = MPI.COMM_WORLD
            self._has_mpi = True
        except Exception:
            self._comm = _SerialComm()
            self._has_mpi = False
        self._resolved = True

    @property
    def has_mpi(self):
        """True when a real MPI runtime backs this context."""
        self._resolve()
        return self._has_mpi

    @property
    def comm(self):
        self._resolve()
        return self._comm

    @property
    def rank(self):
        return self.comm.Get_rank()

    @property
    def size(self):
        return self.comm.Get_size()

    @property
    def is_root(self):
        return self.rank == 0

    def use(self, comm):
        """Substitute a communicator. For tests, and for embedding SEAKMC in a
        host application that owns its own communicator."""
        self._comm = comm
        self._has_mpi = not isinstance(comm, _SerialComm)
        self._resolved = True

    def reset(self):
        """Forget the resolved communicator; the next access re-resolves."""
        self._comm = None
        self._resolved = False
        self._has_mpi = None


mpi = MPIContext()


def default_nproc_task(size=None):
    """Largest useful power-of-two-ish task width for a world of ``size``.

    Previously computed at import time in ``Input.py`` from a module-level
    ``size_world``, which meant the value was fixed before any settings were
    read. Kept here, as a function, with the original arithmetic.
    """
    if size is None:
        size = mpi.size
    if size < 1:
        return 1
    n = int(np.log(size) / np.log(2)) if size > 1 else 0
    nleft = size - int(np.power(2, n))
    if n >= 4 and nleft >= np.power(2, n - 1):
        return int(np.power(2, n - 1) * 3)
    return int(np.power(2, n))
