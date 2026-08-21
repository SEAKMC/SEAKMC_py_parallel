
import seakmc.mpiconf.MPIconf as mympi
from seakmc.mpiconf.context import mpi
from seakmc.mpiconf.error_exit import error_exit


def data_dynamics(purpose, force_evaluator, data, ntask_tot, nactive=None, nproc_task=1, thisExports=None, **COMM_args):
    start_proc = 0
    if COMM_args is None:
        COMM_args = mympi.get_COMM_info(nproc_task, start_proc=0)
    thiscolor = COMM_args["color"]
    ntask_time = mympi.get_ntask_time(nproc_task, start_proc=start_proc, thiscomm=None)

    if nactive is None:
        try:
            nactive = data.nactive
        except:
            nactive = data.natoms

    ntask_left = ntask_tot
    ntask_time = min(ntask_time, ntask_left)
    itask_start = 0
    while ntask_left > 0:
        if COMM_args["color"] < ntask_time:
            [Eground, relaxed_coords, isValid, errormsg] = force_evaluator.run_runner(purpose, data, thiscolor,
                                                                                      nactive=nactive,
                                                                                      thisExports=thisExports,
                                                                                      comm=COMM_args["thiscomm"])
        else:
            Eground = None
            relaxed_coords = None
            isValid = None
            errormsg = None

        mpi.comm.Barrier()

        itask_start += ntask_time
        ntask_left = ntask_left - ntask_time
        ntask_time = min(ntask_time, ntask_left)

    mpi.comm.Barrier()
    Eground = mpi.comm.bcast(Eground, root=0)
    relaxed_coords = mpi.comm.bcast(relaxed_coords, root=0)
    isValid = mpi.comm.bcast(isValid, root=0)
    errormsg = mpi.comm.bcast(errormsg, root=0)
    if not isValid:
        error_exit(errormsg)

    return [Eground, relaxed_coords, isValid, errormsg]


