"""Optional SEAKMC timing diagnostics.

Timing output is disabled by default. Set SEAKMC_TIMING_DETAIL=1 to print
lightweight timing lines that help diagnose barrier-scan performance.
"""

import os


def timing_enabled():
    return os.environ.get("SEAKMC_TIMING_DETAIL", "").lower() in ("1", "true", "yes", "on")


def timing_print(message, rank=0):
    if timing_enabled() and rank == 0:
        print("SEAKMC_TIMING " + str(message), flush=True)
