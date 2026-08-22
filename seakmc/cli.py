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
from seakmc.mpiconf.context import mpi


def _teardown(code=1):
    """End the whole job, not just this rank."""
    try:
        if mpi.has_mpi and mpi.size > 1:
            sys.stderr.flush()
            mpi.comm.Abort(code)
    except Exception:
        # No MPI, or MPI already torn down: a plain exit is correct and enough.
        pass
    sys.exit(code)


def _rank_label():
    try:
        if mpi.has_mpi and mpi.size > 1:
            return f" [rank {mpi.rank}]"
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


def validate_only(inputf="input.yaml"):
    """Parse and check an input file without running anything."""
    from seakmc.input.Input import Settings
    sett = Settings.from_file(inputf)
    sett.validate_input()
    print(f"{inputf}: valid")
    return 0


def emit_schema(inputf="input.yaml", markdown=False, out=None):
    """Print the JSON Schema, or the reference document, for the settings."""
    from seakmc.input.Input import Settings
    from seakmc.input.schema import reference_markdown, schema_json
    sett = Settings.from_file(inputf)
    text = reference_markdown(sett) if markdown else schema_json(sett)
    if out:
        with open(out, "w") as f:
            f.write(text + "\n")
        print(f"written: {out}")
    else:
        print(text)
    return 0


def migrate(target="input.yaml", in_place=False):
    """Rewrite an older input file onto current key names."""
    from seakmc.input.migrate import migrate_file
    new, changes = migrate_file(target, in_place=in_place)
    if not changes:
        print(f"{target}: nothing to migrate")
        return 0
    for c in changes:
        print(f"  {c}")
    if in_place:
        print(f"{target}: {len(changes)} change(s) applied (original kept as {target}.bak)")
    else:
        print(f"\n{target}: {len(changes)} change(s) needed. "
              f"Re-run with --in-place to apply them.")
    return 0


USAGE = """usage: seakmc [command]

  (no command)          run the simulation described by input.yaml
  validate [FILE]       check an input file and report problems
  schema [FILE]         print the JSON Schema for the settings
    --markdown            print the reference document instead
    -o FILE               write to FILE instead of stdout
  migrate [FILE]        rewrite an older input file onto current key names
    --in-place            apply the changes (keeps FILE.bak)
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else None

    if cmd in ("-h", "--help", "help"):
        print(USAGE)
        return

    if cmd in ("validate", "schema", "migrate"):
        rest = argv[1:]
        flags = [a for a in rest if a.startswith("-")]
        files = [a for a in rest if not a.startswith("-")]
        target = files[0] if files else "input.yaml"
        try:
            if cmd == "validate":
                validate_only(target)
            elif cmd == "schema":
                out = None
                if "-o" in rest:
                    i = rest.index("-o")
                    out = rest[i + 1] if i + 1 < len(rest) else None
                    if out in files:
                        files.remove(out)
                        target = files[0] if files else "input.yaml"
                emit_schema(target, markdown="--markdown" in flags, out=out)
            else:
                migrate(target, in_place="--in-place" in flags)
        except SeakmcError as e:
            print(f"\n{e}", file=sys.stderr, flush=True)
            sys.exit(1)
        except FileNotFoundError:
            print(f"No such input file: {target}", file=sys.stderr, flush=True)
            sys.exit(1)
        return

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
