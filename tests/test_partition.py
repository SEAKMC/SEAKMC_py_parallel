"""MPI work partitioning.

get_proc_partition silently dropped items whenever int(ntot/n_rank) > size.
For 7 items over 4 ranks it returned (1, 3, 1): ranks 0-2 took items 0, 1, 2,
rank 3 took item 3, and items 4, 5 and 6 were processed by nobody. Neighbour
lists and defect searches therefore missed atoms, by an amount that depended
on the rank count -- so results shifted with the number of cores.
"""

import pytest

from seakmc.mpiconf.MPIconf import get_proc_partition


def assigned_items(ntot, size, nmin_rank=1):
    """Replay the range convention every caller implements."""
    n_rank, rank_last, n_rank_last = get_proc_partition(ntot, size, nmin_rank=nmin_rank)
    items = []
    for r in range(size):
        if r < rank_last:
            start, end = r * n_rank, r * n_rank + n_rank
        elif r == rank_last:
            start, end = r * n_rank, r * n_rank + n_rank_last
        else:
            start = end = ntot
        items.extend(range(start, end))
    return items


@pytest.mark.parametrize("ntot", list(range(0, 60)) + [199, 449, 1999, 2000])
@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 8, 16])
@pytest.mark.parametrize("nmin", [1, 5])
def test_partition_covers_every_item_exactly_once(ntot, size, nmin):
    assert assigned_items(ntot, size, nmin) == list(range(ntot))


def test_the_regression_case():
    """7 items over 4 ranks: items 4, 5, 6 used to vanish."""
    assert assigned_items(7, 4) == [0, 1, 2, 3, 4, 5, 6]


def test_no_rank_is_assigned_a_negative_count():
    for ntot in range(0, 50):
        for size in range(1, 9):
            n_rank, rank_last, n_rank_last = get_proc_partition(ntot, size)
            assert n_rank >= 1
            assert 0 <= rank_last < max(size, 1)
            assert n_rank_last >= 0


def test_single_rank_takes_everything():
    for ntot in (0, 1, 7, 1999):
        assert assigned_items(ntot, 1) == list(range(ntot))


def test_more_ranks_than_items_is_safe():
    assert assigned_items(3, 16) == [0, 1, 2]


def test_nmin_rank_is_respected_as_a_floor():
    n_rank, _, _ = get_proc_partition(100, 50, nmin_rank=5)
    assert n_rank >= 5
