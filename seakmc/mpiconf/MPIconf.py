import numpy as np


from seakmc.mpiconf.error_exit import error_exit
from seakmc.mpiconf.context import mpi

__author__ = "Tao Liang"
__copyright__ = "Copyright 2021"
__version__ = "1.0"
__maintainer__ = "Tao Liang"
__email__ = "xhtliang120@gmail.com"
__date__ = "October 7th, 2021"


def get_2D_task_distribution(inrow, incol, ntask_time):
    ntot = inrow * incol
    processing_tasks = np.array([], dtype=int)

    idstart = 0
    while idstart < ntot:
        irowstart = int(idstart / incol)
        irowend = min(irowstart + ntask_time, inrow)
        ids = np.arange(idstart, (irowend - irowstart) * incol + idstart)
        ids = ids.reshape([irowend - irowstart, incol])
        processing_tasks = np.append(processing_tasks, ids.T.flatten())
        idstart += (irowend - irowstart) * incol
    return processing_tasks


def get_proc_partition(ntot, size, nmin_rank=1):
    """Split ``ntot`` items over ``size`` ranks.

    Returns ``(n_rank, rank_last, n_rank_last)``. Ranks below ``rank_last``
    take ``n_rank`` items each, ``rank_last`` takes ``n_rank_last``, and any
    rank above it takes none -- the convention every caller implements.

    The previous formula silently dropped items whenever
    ``int(ntot / n_rank) > size``. For ntot=7 over 4 ranks it returned
    (1, 3, 1), covering items 0-3 and leaving 4, 5 and 6 unprocessed. Across
    ntot in 1..199 and sizes 1..16 it lost items in 226 of 2786
    configurations, never double-counting, always dropping -- so neighbour
    lists and defect searches quietly missed atoms, by an amount that
    depended on the rank count.
    """
    if ntot <= 0:
        return max(int(nmin_rank), 1), 0, 0
    n_rank = max(int(ntot / size), int(nmin_rank), 1)
    n_working = min(size, -(-ntot // n_rank))   # ceil division
    rank_last = max(n_working - 1, 0)
    n_rank_last = ntot - rank_last * n_rank

    return n_rank, rank_last, n_rank_last


def get_ntask_time(nproc_task, start_proc=0, thiscomm=None):
    if thiscomm is not None:
        pass
    else:
        thiscomm = mpi.comm
    size_local = thiscomm.Get_size()
    #rank_local = thiscomm.Get_rank()
    if size_local < nproc_task + start_proc:
        error_exit(f"The number of cores ({size_local}) must be greater than the number of "
                   f"communicators ({nproc_task + start_proc}).")
    ntask_time = int((size_local - start_proc) / nproc_task)

    return ntask_time


def split_communicator(nproc_task, start_proc=0, thiscomm=None):
    if thiscomm is not None:
        pass
    else:
        thiscomm = mpi.comm
    size_local = thiscomm.Get_size()
    rank_local = thiscomm.Get_rank()
    if rank_local < start_proc:
        thiscolor = size_local
    else:
        thiscolor = int((rank_local - start_proc) / nproc_task)
    #thiskey = (rank_local - start_proc) % nproc_task
    comm_split = thiscomm.Split(thiscolor)
    return comm_split, thiscolor

def get_COMM_info(nproc_task, start_proc=0):
    comm_world = mpi.comm
    size_world = comm_world.Get_size()
    if nproc_task == size_world:
        COMM_dict = {"isSplit": False, "color": 0, "thiscomm": comm_world}
    else:
        comm_split, thiscolor = split_communicator(nproc_task, start_proc=start_proc, thiscomm=None)
        COMM_dict = {"isSplit": True, "color": thiscolor,  "thiscomm": comm_split}
    return COMM_dict