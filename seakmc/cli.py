"""Command-line entry point for SEAKMC.

This module owns the only process-level exit decision in the package. Errors
are raised as :class:`~seakmc.exceptions.SeakmcError` wherever they are
detected; here they are reported once and turned into a job teardown.

The teardown has to be ``MPI.Abort`` rather than ``sys.exit`` whenever the job
has more than one rank. A rank that raised and exited quietly would leave its
peers blocked inside a collective -- ``Barrier`` or ``recv`` -- for the
remainder of the wall-clock allocation, which is a worse failure than a crash
because it burns the reservation while producing nothing.
"""

import sys
import time
import traceback

from seakmc.exceptions import SeakmcError


def _teardown(code=1):
    """End the whole job, not just this rank."""
    try:
        from mpi4py import MPI
        if MPI.Is_initialized() and not MPI.Is_finalized() and MPI.COMM_WORLD.Get_size() > 1:
            sys.stderr.flush()
            MPI.COMM_WORLD.Abort(code)
    except Exception:
        # No MPI, or MPI already torn down: a plain exit is correct and enough.
        pass
    sys.exit(code)


def _rank_label():
    try:
        from mpi4py import MPI
        if MPI.Is_initialized() and MPI.COMM_WORLD.Get_size() > 1:
            return f" [rank {MPI.COMM_WORLD.Get_rank()}]"
    except Exception:
        pass
    return ""


def run(inputf="input.yaml"):
    """Run a SEAKMC simulation. Raises SeakmcError on bad input or state."""
    from seakmc.input.Input import Settings
    import seakmc.process.Preprocess as preseakmc
    import seakmc.process.Process as runseakmc
    import seakmc.process.Postprocess as postseakmc

    tic = time.time()
    thissett = Settings.from_file(inputf)
    thissett.validate_input()

    seakmcdata, object_dict, Eground, thisRestart = preseakmc.preprocess(thissett)
    simulation_time = runseakmc.run_seakmc(thissett, seakmcdata, object_dict, Eground, thisRestart)
    postseakmc.postprocess(tic, thissett, object_dict, simulation_time)
    return simulation_time


def main():
    try:
        run()
    except SeakmcError as e:
        print(f"\n=== SEAKMC error{_rank_label()} ===\n{e}\n=== end of error ===",
              file=sys.stderr, flush=True)
        _teardown(1)
    except KeyboardInterrupt:
        print(f"\nInterrupted{_rank_label()}.", file=sys.stderr, flush=True)
        _teardown(130)
    except Exception:
        print(f"\n=== Unexpected SEAKMC failure{_rank_label()} ===", file=sys.stderr, flush=True)
        traceback.print_exc()
        _teardown(1)


if __name__ == '__main__':
    main()
