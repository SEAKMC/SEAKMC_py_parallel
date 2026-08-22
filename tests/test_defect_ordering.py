"""Defect grouping must not depend on the row order of the atom frame.

Chain building seeds greedily in row order, so the grouping of point defects
into active volumes followed whatever order the frame happened to be in. That
order is not stable -- the relaxed structure comes back with a row order that
varies with the MPI rank count -- so identical geometry produced different
active volumes at different -np, and `idav` named a different physical defect
depending on how many cores the job used.

SortD4PDR does not fix this: it sorts on distance from the defect centroid,
and for a symmetric defect every entry ties, leaving the incoming order.
"""

import numpy as np
import pandas as pd

from seakmc.core.data import SeakmcData


def _frame(tags, coords):
    return pd.DataFrame({
        "tag": tags,
        "xsn": [c[0] for c in coords],
        "ysn": [c[1] for c in coords],
        "zsn": [c[2] for c in coords],
    })


def _canonicalize(df):
    obj = SeakmcData.__new__(SeakmcData)
    obj.defects = df
    obj._canonicalize_defect_order()
    return obj.defects


def test_shuffled_rows_give_the_same_order():
    tags = [7, 2, 91, 34, 5]
    coords = [(0.1, 0.2, 0.3), (0.4, 0.5, 0.6), (0.7, 0.8, 0.9), (0.2, 0.2, 0.2), (0.9, 0.1, 0.5)]
    base = _canonicalize(_frame(tags, coords))
    rng = np.random.default_rng(0)
    for _ in range(8):
        order = rng.permutation(len(tags))
        shuffled = _frame([tags[i] for i in order], [coords[i] for i in order])
        out = _canonicalize(shuffled)
        assert list(out["tag"]) == list(base["tag"])
        np.testing.assert_allclose(out["xsn"].to_numpy(), base["xsn"].to_numpy())


def test_order_is_ascending_by_tag():
    out = _canonicalize(_frame([9, 3, 40, 1], [(0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0), (0.4, 0, 0)]))
    assert list(out["tag"]) == [1, 3, 9, 40]


def test_index_is_reset_to_positional():
    out = _canonicalize(_frame([9, 3, 40], [(0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)]))
    assert list(out.index) == [0, 1, 2]


def test_symmetric_defects_are_still_ordered_deterministically():
    """The vacancy case: eight neighbours all equidistant from the centroid,
    so a distance sort cannot separate them but the tag can."""
    tags = [999, 990, 909, 900, 99, 90, 9, 0]
    c = [(0.94, 0.94, 0.94), (0.94, 0.94, 0.96), (0.94, 0.96, 0.94), (0.94, 0.96, 0.96),
         (0.96, 0.94, 0.94), (0.96, 0.94, 0.96), (0.96, 0.96, 0.94), (0.96, 0.96, 0.96)]
    a = _canonicalize(_frame(tags, c))
    b = _canonicalize(_frame(list(reversed(tags)), list(reversed(c))))
    assert list(a["tag"]) == list(b["tag"]) == sorted(tags)


def test_missing_or_duplicate_key_leaves_the_frame_alone():
    df = pd.DataFrame({"xsn": [0.1, 0.2], "ysn": [0, 0], "zsn": [0, 0]})
    assert list(_canonicalize(df.copy())["xsn"]) == [0.1, 0.2]
    dup = _frame([5, 5], [(0.1, 0, 0), (0.2, 0, 0)])
    assert list(_canonicalize(dup)["xsn"]) == [0.1, 0.2]
