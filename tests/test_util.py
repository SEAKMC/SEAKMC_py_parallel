"""Pure numeric helpers from seakmc.core.util.

This module imports no MPI, so these run anywhere -- they are the natural
first tests and need no MPI runtime in CI.
"""

import numpy as np
import pytest

from seakmc.core.util import (
    abs_cap, generate_rotation_matrix, mat_mag, mat_unit,
    mats_angle, sigmoid_function, to_half_matrix,
)


def test_abs_cap_clamps():
    assert abs_cap(1.5) == 1.0
    assert abs_cap(-1.5) == -1.0
    assert abs_cap(0.25) == 0.25


def test_mat_mag_matches_norm():
    x = np.array([[3.0, 0.0], [4.0, 0.0], [0.0, 0.0]])
    assert mat_mag(x) == pytest.approx(5.0)


def test_mat_unit_returns_unit_norm():
    x = np.array([[3.0], [4.0], [0.0]])
    assert mat_mag(mat_unit(x)) == pytest.approx(1.0)


@pytest.mark.parametrize("angles", [[0, 0, 0], [30, 45, 60], [90, 0, 180], [-15, 200, 5]])
def test_rotation_matrix_is_orthogonal_with_unit_determinant(angles):
    R = generate_rotation_matrix(angles, Ang_Format="Degree")
    np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert np.linalg.det(R) == pytest.approx(1.0)


def test_rotation_preserves_length():
    R = generate_rotation_matrix([12.0, 34.0, 56.0], Ang_Format="Degree")
    v = np.array([1.0, -2.0, 3.0])
    assert np.linalg.norm(R @ v) == pytest.approx(np.linalg.norm(v))


def test_mats_angle_on_vectors():
    """1-D input, the default path. Used for SaddlePoint.dvec, which is
    np.sum(disp, axis=1) and therefore shape (3,)."""
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    assert mats_angle(a, b) == pytest.approx(90.0)
    assert mats_angle(b, a) == pytest.approx(90.0)
    assert mats_angle(a, a) == pytest.approx(0.0, abs=1e-6)
    assert mats_angle(a, -a) == pytest.approx(180.0)


def test_mats_angle_on_2d_arrays_requires_flatten():
    """Contract guard.

    For a (3, N) displacement field the default Flatten=False computes
    np.sum(x @ y.T), which is not the Frobenius inner product -- it gives a
    nonzero angle between an array and itself. Every 2-D call site in the
    package passes Flatten=True; this test exists so that a future one that
    forgets fails loudly here rather than silently mis-grouping saddle points.
    """
    rng = np.random.default_rng(0)
    x = rng.normal(size=(3, 5))

    assert mats_angle(x, x, Flatten=True) == pytest.approx(0.0, abs=1e-6)
    assert mats_angle(x, x) != pytest.approx(0.0, abs=1e-3)

    y = rng.normal(size=(3, 5))
    expected = np.degrees(np.arccos(np.sum(x * y) / (mat_mag(x) * mat_mag(y))))
    assert mats_angle(x, y, Flatten=True) == pytest.approx(expected)


def test_sigmoid_is_monotonic_and_centred():
    xs = np.linspace(-6, 6, 25)
    ys = np.array([sigmoid_function(x) for x in xs])
    assert np.all(np.diff(ys) > 0)
    assert sigmoid_function(0.0) == pytest.approx(0.5)


def test_to_half_matrix_keeps_lower_triangle():
    a = np.arange(9, dtype=float).reshape(3, 3)
    h = to_half_matrix(a)
    assert np.allclose(np.triu(h, 1), 0.0)
