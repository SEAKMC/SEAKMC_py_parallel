"""Input validation.

Each case here was silently accepted before: a misspelled key was copied into
the settings dict and ignored, a missing section raised a bare KeyError from
inside a 689-line parser, and documentation prose sat in numeric slots where
`str * int` repeats the string rather than raising.
"""

import glob
import io
import contextlib
import os

import pytest
import yaml

from seakmc.exceptions import SeakmcError
from seakmc.input.Input import Settings
from seakmc.input.validate import check_sections, check_types, check_unknown_keys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(tmp_path, doc):
    p = tmp_path / "input.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with contextlib.redirect_stdout(io.StringIO()):
            return Settings.from_file("input.yaml")
    finally:
        os.chdir(cwd)


@pytest.fixture
def base():
    with open(os.path.join(REPO, "examples", "Fe_vacancy", "input.yaml")) as f:
        return yaml.safe_load(f)


def test_every_shipped_input_validates():
    """The reference template included -- it did not, until its placeholder
    prose was moved into comments."""
    targets = sorted(glob.glob(os.path.join(REPO, "examples", "**", "input.yaml"), recursive=True))
    targets.append(os.path.join(REPO, "run_script", "input.yaml"))
    assert len(targets) >= 6
    cwd = os.getcwd()
    for f in targets:
        try:
            os.chdir(os.path.dirname(f))
            with contextlib.redirect_stdout(io.StringIO()):
                sett = Settings.from_file("input.yaml")
                sett.validate_input()
        except SeakmcError as e:
            pytest.fail(f"{f} failed validation:\n{e}")
        finally:
            os.chdir(cwd)


def test_missing_required_section_is_named(tmp_path, base):
    doc = {k: v for k, v in base.items() if k != "active_volume"}
    p = tmp_path / "input.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with pytest.raises(SeakmcError, match="active_volume"):
            Settings.from_file("input.yaml")
    finally:
        os.chdir(cwd)


def test_misspelled_key_is_rejected_with_a_suggestion(tmp_path, base):
    """The project's own template shipped `Inteval4ShowProgress` for years."""
    doc = dict(base)
    doc["system"] = {"Inteval4ShowProgress": 10}
    sett = _load(tmp_path, doc)
    with pytest.raises(SeakmcError) as e:
        sett.validate_input()
    msg = str(e.value)
    assert "Inteval4ShowProgress" in msg
    assert "Interval4ShowProgress" in msg, "should suggest the near miss"


def test_prose_in_a_numeric_slot_is_rejected(tmp_path, base):
    doc = dict(base)
    doc["active_volume"] = dict(base["active_volume"], DActive="cutdefectmax*2.7")
    sett = _load(tmp_path, doc)
    with pytest.raises(SeakmcError, match="must be a number"):
        sett.validate_input()


def test_required_user_keys_are_not_flagged(tmp_path, base):
    """data.FileName and data.atom_style have no default by design."""
    sett = _load(tmp_path, base)
    problems = check_unknown_keys(sett._raw_parameters, sett)
    assert not any("FileName" in p or "atom_style" in p for p in problems), problems


def test_unknown_section_is_reported():
    problems = check_sections({"data": {}, "potentail": {}})
    assert any("potentail" in p and "potential" in p for p in problems), problems


def test_numeric_check_accepts_numbers_and_none(tmp_path, base):
    sett = _load(tmp_path, base)
    assert check_types(sett) == []


def test_strict_false_returns_problems_instead_of_raising(tmp_path, base):
    doc = dict(base)
    doc["system"] = {"NotAThing": 1}
    sett = _load(tmp_path, doc)
    problems = sett.validate_input(strict=False)
    assert problems and any("NotAThing" in p for p in problems)
