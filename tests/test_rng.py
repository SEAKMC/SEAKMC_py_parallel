"""Task-keyed random streams.

The properties asserted here are exactly the ones a per-process seed fails to
provide, and they are what makes a golden-file regression test possible.
"""

import numpy as np
import pytest

from seakmc.core.rng import RandomSource, NS_VN, NS_KMC_SELECT


def test_same_key_same_numbers():
    src = RandomSource(); src.seed(12345)
    a = src.stream(NS_VN, 0, 1, 2).random(5)
    b = src.stream(NS_VN, 0, 1, 2).random(5)
    np.testing.assert_array_equal(a, b)


def test_different_tasks_are_independent():
    """The failure a per-process seed produces: N searches drawing one vector."""
    src = RandomSource(); src.seed(12345)
    draws = [src.stream(NS_VN, 0, 0, i).random(3) for i in range(8)]
    for i in range(len(draws)):
        for j in range(i + 1, len(draws)):
            assert not np.allclose(draws[i], draws[j]), f"searches {i} and {j} collided"


def test_namespaces_do_not_collide():
    src = RandomSource(); src.seed(7)
    a = src.stream(NS_VN, 3, 4).random(4)
    b = src.stream(NS_KMC_SELECT, 3, 4).random(4)
    assert not np.allclose(a, b)


def test_streams_are_independent_of_rank_count():
    """A task's numbers must not depend on how the work was distributed."""
    src = RandomSource(); src.seed(999)
    tasks = [(step, av, sp) for step in range(2) for av in range(2) for sp in range(3)]
    reference = {t: src.stream(NS_VN, *t).random(4) for t in tasks}
    for order in (list(reversed(tasks)), tasks[3:] + tasks[:3]):
        for t in order:
            np.testing.assert_array_equal(src.stream(NS_VN, *t).random(4), reference[t])


def test_seeds_differ_between_unseeded_sources():
    a, b = RandomSource(), RandomSource()
    assert a.master_seed != b.master_seed


def test_seed_is_reported_so_it_can_be_recorded():
    src = RandomSource()
    used = src.seed(None)
    assert isinstance(used, int) and used >= 0
    assert src.master_seed == used
    assert src.is_seeded


def test_explicit_seed_round_trips():
    src = RandomSource()
    assert src.seed(4242) == 4242
    assert src.master_seed == 4242


def test_negative_keys_are_rejected():
    src = RandomSource(); src.seed(1)
    with pytest.raises(ValueError):
        src.stream(NS_VN, -1)


def test_no_global_numpy_state_is_used():
    """Drawing must not depend on, or disturb, np.random's global state."""
    src = RandomSource(); src.seed(5)
    np.random.seed(1); before = np.random.get_state()[1][:5].copy()
    _ = src.stream(NS_VN, 1, 1, 1).random(100)
    np.testing.assert_array_equal(np.random.get_state()[1][:5], before)
