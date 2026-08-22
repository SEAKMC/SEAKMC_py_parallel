"""Input validation: unknown keys, missing sections, and wrong types.

Settings.from_file copies whatever it finds in the YAML on top of a defaults
dict. Nothing checks the result, which produces three silent failures:

* A misspelled key is accepted and ignored. The project's own shipped template
  demonstrated this -- it set `Inteval4ShowProgress` while the code reads
  `Interval4ShowProgress`, so that option had never once taken effect.
* A missing required section raises a bare KeyError naming only the section,
  from inside a 689-line parser.
* A value of the wrong type is stored as-is. The reference template carries
  documentation strings in numeric slots (`DActive: cutdefectmax*2.7`), and
  because `str * int` is legal Python and repeats the string, several of these
  degrade quietly rather than raising.

This module is a validation pass over the parsed YAML, not a replacement for
the parser. It is a step toward a typed schema: the key registry here is
derived from the defaults the parser already establishes, so the two cannot
drift apart.
"""

import difflib

from seakmc.exceptions import SeakmcInputError

REQUIRED_SECTIONS = ("data", "potential", "kinetic_MC", "active_volume", "spsearch", "saddle_point")
OPTIONAL_SECTIONS = ("system", "force_evaluator", "dynamic_matrix", "defect_bank", "visual")
KNOWN_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS

# Keys whose value must be numeric. These are the ones the shipped template
# carried prose in, and the ones that fail silently rather than loudly.
# Keys a user must (or may) supply that deliberately have no default, so they
# never appear in the defaults snapshot. Verified against the code: each is
# read somewhere in the package.
REQUIRED_USER_KEYS = {
    "data": ("FileName", "atom_style"),
    "active_volume": ("NActive", "NBuffer", "NFixed", "TurnoffPBC"),
}

# Nested keys the parser reads but never seeds with a default, so they do not
# appear in the defaults snapshot. Verified present in the source.
NESTED_USER_KEYS = {
    ("active_volume", "FindDefects"): ("atom_style4Ref", "ReferenceData", "Defects"),
}

NUMERIC_KEYS = {
    "active_volume": ("DActive", "DBuffer", "DFixed", "DCut4PDR", "DCut4noOverlap",
                      "NMin4AV", "NMin_perproc", "R4RT_SetMolID"),
    "kinetic_MC": ("NSteps", "Temp", "EnCut4Transient", "Tol4Disp", "Tol4Barr"),
    "spsearch": ("NSearch", "DimerSep", "NMax4Rot", "NMax4Trans", "TrialStepsize",
                 "MaxStepsize", "MinStepsize", "FConv", "EnConv"),
    "saddle_point": ("Prefactor", "BarrierCut", "BarrierMin"),
    "system": ("Interval4ShowProgress",),
}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _suggest(name, candidates):
    match = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.75)
    return match[0] if match else None


def check_sections(parameters):
    """Missing required sections, and unknown top-level sections."""
    problems = []
    for sec in REQUIRED_SECTIONS:
        if sec not in parameters:
            problems.append(f"missing required section '{sec}'")
    for sec in parameters:
        if sec not in KNOWN_SECTIONS:
            hint = _suggest(sec, KNOWN_SECTIONS)
            problems.append(f"unknown section '{sec}'" + (f" (did you mean '{hint}'?)" if hint else ""))
    return problems


def check_unknown_keys(parameters, settings):
    """Keys present in the YAML that the parser never reads.

    The registry is the defaults snapshot taken inside from_file before user
    values were merged. Comparing against the finished settings object cannot
    work: the parser copies unrecognised keys straight in, so a misspelled key
    is indistinguishable from a real one afterwards.
    """
    defaults = getattr(settings, "_default_keys", None)
    if not defaults:
        return []
    problems = []
    for sec, given in parameters.items():
        if sec not in defaults or not isinstance(given, dict):
            continue
        known = set(defaults[sec]) | set(REQUIRED_USER_KEYS.get(sec, ()))
        merged = getattr(settings, sec, {})
        for key, value in given.items():
            if key in known:
                # One level of nesting, where the default is itself a mapping.
                sub_default = merged.get(key) if isinstance(merged, dict) else None
                if isinstance(value, dict) and isinstance(sub_default, dict):
                    allowed = set(sub_default) | set(NESTED_USER_KEYS.get((sec, key), ()))
                    for sub in value:
                        if sub not in allowed:
                            hint = _suggest(sub, sub_default)
                            problems.append(
                                f"{sec}.{key}.{sub} is not a recognised setting"
                                + (f" (did you mean '{hint}'?)" if hint else ""))
                continue
            hint = _suggest(key, known)
            problems.append(f"{sec}.{key} is not a recognised setting"
                            + (f" (did you mean '{hint}'?)" if hint else ""))
    return problems


def check_types(settings):
    """Numeric settings that ended up holding something else."""
    problems = []
    for sec, keys in NUMERIC_KEYS.items():
        values = getattr(settings, sec, None)
        if not isinstance(values, dict):
            continue
        for key in keys:
            if key not in values:
                continue
            v = values[key]
            if v is None or v is False or _is_number(v):
                continue
            problems.append(
                f"{sec}.{key} must be a number, got {type(v).__name__} {v!r}. "
                f"Template placeholders such as 'cutdefectmax*2.7' are documentation, "
                f"not expressions -- omit the key to take the computed default.")
    return problems


def validate(parameters, settings, strict=True):
    """Return the list of problems; raise SeakmcInputError if strict."""
    problems = check_sections(parameters)
    if not problems:
        problems += check_unknown_keys(parameters, settings)
    problems += check_types(settings)
    if problems and strict:
        raise SeakmcInputError(
            "Invalid input:\n" + "\n".join(f"  - {p}" for p in problems))
    return problems
