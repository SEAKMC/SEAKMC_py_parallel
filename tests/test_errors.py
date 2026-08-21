"""Error handling.

These tests are the reason step 1 of Phase 1 exists. Before ``error_exit``
raised, none of them could be written: it called ``MPI.COMM_WORLD.Abort``,
which terminated the interpreter and would have taken pytest down with it.
"""

import pytest

from seakmc.exceptions import SeakmcError, SeakmcInputError
from seakmc.mpiconf.error_exit import error_exit


def test_error_exit_raises_and_is_catchable():
    with pytest.raises(SeakmcError, match="something went wrong"):
        error_exit("something went wrong")


def test_process_survives_a_reported_error():
    """The whole point: reporting an error must not end the process."""
    try:
        error_exit("recoverable in a test")
    except SeakmcError:
        pass
    assert True, "reached only because the interpreter is still alive"


def test_input_error_is_a_seakmc_error():
    assert issubclass(SeakmcInputError, SeakmcError)
    with pytest.raises(SeakmcError):
        raise SeakmcInputError("bad setting")


def test_message_is_preserved():
    with pytest.raises(SeakmcError) as excinfo:
        error_exit("DCut4noOverlap must be larger than DActive!")
    assert "DCut4noOverlap" in str(excinfo.value)


def test_too_few_cores_is_reported_not_aborted():
    """MPIconf previously called MPI.Abort() directly for this condition."""
    from seakmc.mpiconf.MPIconf import get_ntask_time
    from mpi4py import MPI
    size = MPI.COMM_WORLD.Get_size()
    with pytest.raises(SeakmcError, match="number of cores"):
        get_ntask_time(size + 8)
