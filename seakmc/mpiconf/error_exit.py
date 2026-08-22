"""Report a fatal SEAKMC condition.

Historically this printed the message and called ``MPI.COMM_WORLD.Abort(1)``.
That terminated the interpreter outright, so no caller could recover and no
test could assert that a bad input was rejected -- the abort took the test
runner down too. It also meant a single bad setting ended a notebook kernel.

It now raises :class:`~seakmc.exceptions.SeakmcError`. Control flow at the 72
call sites is unchanged, since both forms stop execution at the same point.
The decision to tear down an MPI job moved to :func:`seakmc.cli.main`, which
still calls ``Abort`` -- necessary because a rank that dies quietly would
leave its peers blocked on a collective for the rest of the wall-clock
allocation.
"""

from seakmc.exceptions import SeakmcError


def error_exit(error_str):
    """Raise :class:`SeakmcError` with ``error_str``.

    Kept as a function, under its original name, so that all existing call
    sites continue to work unchanged.
    """
    raise SeakmcError(error_str)
