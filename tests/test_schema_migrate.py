"""Generated schema and the input migrator.

The schema's key registry is derived from the defaults snapshot rather than
maintained by hand, so it cannot drift from the parser. It is strict on key
names and permissive on types: key typos are the failure mode that actually
occurs -- eight were found in this project's own shipped inputs, each read by
zero lines of code -- while types are not safely inferable, since 18 settings
default to the sentinel string "NA" and a default of False often means "unset,
or supply a path".
"""

import glob
import io
import contextlib
import os

import pytest
import yaml

from seakmc.input.Input import Settings
from seakmc.input.migrate import DEAD_KEYS, RENAMES, migrate_text
from seakmc.input.schema import build_schema, reference_markdown

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def schema():
    cwd = os.getcwd()
    try:
        os.chdir(os.path.join(REPO, "examples", "Fe_vacancy"))
        with contextlib.redirect_stdout(io.StringIO()):
            return build_schema(Settings.from_file("input.yaml"))
    finally:
        os.chdir(cwd)


def test_schema_is_valid_draft7(schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft7Validator.check_schema(schema)


def test_every_shipped_input_satisfies_the_schema(schema):
    jsonschema = pytest.importorskip("jsonschema")
    targets = sorted(glob.glob(os.path.join(REPO, "examples", "**", "input.yaml"), recursive=True))
    targets.append(os.path.join(REPO, "run_script", "input.yaml"))
    assert len(targets) >= 6
    validator = jsonschema.Draft7Validator(schema)
    for f in targets:
        errs = list(validator.iter_errors(yaml.safe_load(open(f))))
        assert not errs, f"{f}: " + "; ".join(e.message for e in errs[:3])


def test_schema_rejects_an_unknown_key(schema):
    jsonschema = pytest.importorskip("jsonschema")
    doc = yaml.safe_load(open(os.path.join(REPO, "examples", "Fe_vacancy", "input.yaml")))
    doc.setdefault("kinetic_MC", {})["NoSuchSetting"] = 1
    errs = list(jsonschema.Draft7Validator(schema).iter_errors(doc))
    assert any("NoSuchSetting" in e.message for e in errs)


def test_schema_marks_the_required_sections(schema):
    for sec in ("data", "potential", "kinetic_MC", "active_volume", "spsearch", "saddle_point"):
        assert sec in schema["required"]


def test_reference_document_covers_every_section(schema):
    cwd = os.getcwd()
    try:
        os.chdir(os.path.join(REPO, "examples", "Fe_vacancy"))
        with contextlib.redirect_stdout(io.StringIO()):
            md = reference_markdown(Settings.from_file("input.yaml"))
    finally:
        os.chdir(cwd)
    for sec in schema["properties"]:
        assert f"## `{sec}`" in md


# --- migrator -------------------------------------------------------------

def test_migrator_renames_every_known_typo():
    src = "".join(f"    {wrong}: 1\n" for _s, wrong, _r, _w in RENAMES)
    out, changes = migrate_text(src)
    assert len(changes) == len(RENAMES)
    for _s, wrong, right, _w in RENAMES:
        assert f"    {right}: 1" in out
        assert f"    {wrong}:" not in out


def test_migrator_comments_out_dead_keys():
    src = "".join(f"    {k}: True\n" for k, _w in DEAD_KEYS)
    out, changes = migrate_text(src)
    assert len(changes) == len(DEAD_KEYS)
    for k, _w in DEAD_KEYS:
        assert f"# {k}: True" in out


def test_migrator_is_idempotent():
    src = "    Inteval4ShowProgress: 10\n    WorkWorkDir: True\n"
    once, c1 = migrate_text(src)
    twice, c2 = migrate_text(once)
    assert once == twice
    assert c1 and not c2


def test_migrator_preserves_comments_and_indentation():
    src = "system:\n    # keep me\n        Inteval4ShowProgress: 10   # trailing\n"
    out, _ = migrate_text(src)
    assert "# keep me" in out
    assert "        Interval4ShowProgress: 10   # trailing" in out


def test_migrator_leaves_a_clean_file_alone():
    for f in sorted(glob.glob(os.path.join(REPO, "examples", "**", "input.yaml"), recursive=True)):
        _out, changes = migrate_text(open(f).read())
        assert not changes, f"{f} still needs migration: {changes}"
