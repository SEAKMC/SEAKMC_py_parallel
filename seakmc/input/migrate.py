"""Rewrite an older input.yaml onto current key names.

Five keys in this project's shipped inputs were read by zero lines of code --
each a near-miss of a real setting, silently accepted and ignored because the
parser copied unknown keys straight into the settings dict. Anyone with an
input file from before that was found still has them.

Rewrites text rather than reparsing and dumping, so comments, ordering and
formatting survive. A migration that reformatted a user's annotated input file
would be its own kind of damage.
"""

import re

# (section, wrong, right, why). Section is advisory -- the keys are distinctive
# enough to rewrite on name alone, and a nested block makes section tracking
# unreliable.
RENAMES = [
    ("system", "Inteval4ShowProgress", "Interval4ShowProgress",
     "the code reads Interval4ShowProgress; the shipped template misspelled it"),
    ("data", "dimensions", "dimension",
     "the code reads dimension (singular)"),
    ("force_evaluator", "OutFileHeader", "OutFileHeaders",
     "the code reads OutFileHeaders (plural)"),
    ("system", "KMCstep4Restart", "KMCStep4Restart",
     "the code reads KMCStep4Restart (capital S)"),
    ("saddle_point", "Angcut4GSP", "AngCut4GSP",
     "the code reads AngCut4GSP (capital C)"),
    ("saddle_point", "R2Dmax4tol", "R2Dmax4Tol",
     "the code reads R2Dmax4Tol (capital T)"),
]

# Keys no code reads at all. Commented out rather than deleted, so a user can
# see what happened to a line they wrote deliberately.
DEAD_KEYS = [
    ("WorkWorkDir", "no code reads this key"),
    ("Input2color", "no code reads this key"),
]


def migrate_text(text):
    """Return (new_text, [changes]). Idempotent."""
    changes = []
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        stripped = line.strip()
        new = line
        for _sec, wrong, right, why in RENAMES:
            m = re.match(rf"^(\s*){re.escape(wrong)}(\s*:)(.*)$", line.rstrip("\n"))
            if m:
                new = f"{m.group(1)}{right}{m.group(2)}{m.group(3)}\n"
                changes.append(f"{wrong} -> {right} ({why})")
                break
        else:
            for dead, why in DEAD_KEYS:
                m = re.match(rf"^(\s*){re.escape(dead)}(\s*:)(.*)$", line.rstrip("\n"))
                if m and not stripped.startswith("#"):
                    new = f"{m.group(1)}# {dead}{m.group(2)}{m.group(3)}   # removed: {why}\n"
                    changes.append(f"{dead} commented out ({why})")
                    break
        out.append(new)
    return "".join(out), changes


def migrate_file(path, in_place=False):
    with open(path) as f:
        text = f.read()
    new, changes = migrate_text(text)
    if in_place and changes:
        with open(path + ".bak", "w") as f:
            f.write(text)
        with open(path, "w") as f:
            f.write(new)
    return new, changes
