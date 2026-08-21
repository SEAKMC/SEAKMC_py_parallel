"""Exception types raised by SEAKMC.

Errors are raised, not aborted on. The process-level decision -- whether to
tear down an MPI job -- belongs at the program boundary in :mod:`seakmc.cli`,
not at the point where a problem is detected. That separation is what makes
error paths testable and makes the package usable from a notebook, where an
``MPI_ABORT`` would take the kernel down with it.
"""


class SeakmcError(Exception):
    """Base class for every error SEAKMC raises deliberately.

    Catching this catches all of them, and nothing else.
    """


class SeakmcInputError(SeakmcError):
    """Invalid settings, input file, or structure data."""
