"""Generate a JSON Schema and a reference document from the settings defaults.

The schema is derived, not hand-written. Its key registry is the defaults
snapshot that ``Settings.from_file`` records before merging user values, so the
schema cannot drift from the parser the way a maintained-by-hand list would.

It is deliberately **strict on key names and permissive on types**. Key typos
are the failure mode that actually bites -- five were found in this project's
own shipped inputs, each read by zero lines of code and silently ignored.
Types are not safely inferable from the defaults, because the codebase uses
sentinels heavily: 18 keys default to the string ``"NA"`` meaning "no limit",
four default to ``None``, and a default of ``False`` frequently means "unset --
supply a path or a number instead" (``Path2Pot``, ``RinputOpt``). A schema that
inferred ``type`` from those defaults would reject valid input, which is worse
than not constraining it. The numeric keys that *are* worth enforcing are
checked separately in :mod:`seakmc.input.validate`.
"""

import json

from seakmc.input.validate import (
    KNOWN_SECTIONS, NESTED_USER_KEYS, NUMERIC_KEYS, OPTIONAL_SECTIONS,
    REQUIRED_SECTIONS, REQUIRED_USER_KEYS,
)

SCHEMA_ID = "https://github.com/SEAKMC/SEAKMC_py_parallel/schema/input.schema.json"

#: Defaults computed from the interatomic potential rather than fixed in the
#: source: cutdefectmax comes from pymatgen's bond-length tables for the
#: species in use, and these are multiples of it (Input.py:543-550, 781).
#: Their numeric value depends on the input file AND on the installed pymatgen
#: version, so writing it into a committed artifact makes the file unstable --
#: the drift check would then fail on an unrelated dependency bump rather than
#: on a real change. The keys are still declared; only the value is withheld.
DERIVED_DEFAULTS = {
    ("active_volume", "cutdefectmax"),
    ("active_volume", "DActive"),
    ("active_volume", "DBuffer"),
    ("active_volume", "DFixed"),
    ("active_volume", "DCut4PDR"),
    ("active_volume", "DCut4noOverlap"),
    ("saddle_point", "DAtomCut"),
    ("potential", "cutneighmax"),
}


def _describe(value):
    """A short human note about a default, including what a sentinel means."""
    if value is None:
        return "default: not set"
    if value == "NA":
        return 'default: "NA" (no limit)'
    if value is False:
        return "default: False (unset; may also take a value)"
    if isinstance(value, dict):
        return f"mapping with {len(value)} key(s)"
    if isinstance(value, list):
        return f"list, default: {value!r}"
    return f"default: {value!r}"


def _properties_for(section, defaults, merged):
    props = {}
    for key in sorted(defaults):
        value = merged.get(key)
        if (section, key) in DERIVED_DEFAULTS:
            props[key] = {"description": "derived from the interatomic potential "
                                         "(a multiple of cutdefectmax); omit to accept it"}
            continue
        entry = {"description": _describe(value)}
        if isinstance(value, dict):
            entry["type"] = "object"
            entry["properties"] = {
                sub: {"description": _describe(subval)} for sub, subval in sorted(value.items())
            }
            for sub in NESTED_USER_KEYS.get((section, key), ()):
                entry["properties"].setdefault(
                    sub, {"description": "supplied by the user; no default"})
            entry["additionalProperties"] = False
        elif isinstance(value, bool):
            # A bool default often means "off, or supply a value".
            entry["default"] = value
        elif value is not None:
            entry["default"] = value
        if key in NUMERIC_KEYS.get(section, ()):
            entry["description"] += " -- must be a number"
        props[key] = entry
    for key in REQUIRED_USER_KEYS.get(section, ()):
        props.setdefault(key, {"description": "supplied by the user; no default"})
    return props


def build_schema(settings):
    """Build a JSON Schema from a parsed Settings object."""
    defaults = getattr(settings, "_default_keys", {}) or {}
    sections = {}
    for section in KNOWN_SECTIONS:
        merged = getattr(settings, section, None)
        if not isinstance(merged, dict):
            continue
        known = defaults.get(section)
        if known is None:
            # potential/ has no defaults dict; accept it without a key registry
            # rather than inventing one.
            sections[section] = {"type": "object",
                                 "description": "no defaults registry; keys are not checked"}
            continue
        sections[section] = {
            "type": "object",
            "properties": _properties_for(section, known, merged),
            "additionalProperties": False,
        }
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": SCHEMA_ID,
        "title": "SEAKMC input",
        "description": "Generated from the settings defaults; do not edit by hand.",
        "type": "object",
        "required": list(REQUIRED_SECTIONS),
        "properties": sections,
        "additionalProperties": False,
    }


def schema_json(settings, indent=2):
    return json.dumps(build_schema(settings), indent=indent, sort_keys=False, default=str)


def reference_markdown(settings):
    """A reference document for every recognised setting."""
    schema = build_schema(settings)
    out = ["# SEAKMC input reference", "",
           "Generated from the settings defaults by `seakmc schema --markdown`.",
           "Do not edit by hand.", ""]
    out += ["Required sections: " + ", ".join(f"`{s}`" for s in REQUIRED_SECTIONS), "",
            "Optional sections: " + ", ".join(f"`{s}`" for s in OPTIONAL_SECTIONS), ""]
    for section in KNOWN_SECTIONS:
        spec = schema["properties"].get(section)
        if not spec:
            continue
        tag = "required" if section in REQUIRED_SECTIONS else "optional"
        out += [f"## `{section}` ({tag})", ""]
        props = spec.get("properties")
        if not props:
            out += [spec.get("description", ""), ""]
            continue
        out += ["| setting | notes |", "|---|---|"]
        for key, entry in props.items():
            out.append(f"| `{key}` | {entry['description']} |")
            for sub, subentry in (entry.get("properties") or {}).items():
                out.append(f"| `{key}.{sub}` | {subentry['description']} |")
        out.append("")
    return "\n".join(out)
