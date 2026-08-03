import os
import shutil
import time
import copy
import numpy as np
import pandas as pd
from mpi4py import MPI

import seakmc_p.datasps.DataKMC as dataKMC
import seakmc_p.datasps.DataSPS as dataSPS
import seakmc_p.datasps.PreSPS as preSPS
import seakmc_p.datasps.ReCalibrate as myRecal
import seakmc_p.general.DataOut as dataout
import seakmc_p.process.DataDyn as mydatadyn
import seakmc_p.mpiconf.MPIconf as mympi
from seakmc_p.core.data import SeakmcData
from seakmc_p.input.Input import SP_COMPACT_HEADER4Delete, SP_DATA_HEADER
from seakmc_p.kmc.KMC import SuperBasin
from seakmc_p.restart.Restart import RESTART
from seakmc_p.spsearch.SaddlePoints import Data_SPs
from seakmc_p.mpiconf.error_exit import error_exit
from seakmc_p.process.TrialDisp2Basin import TrialDisps, TrialDisp2Basin
from seakmc_p.general.Timing import timing_print


def _reset_data_for_defect_rebuild(seakmcdata):
    seakmcdata.to_atom_style()
    seakmcdata.velocities = None
    seakmcdata.defects = None
    seakmcdata.def_atoms = []
    seakmcdata.atoms_ghost = None
    seakmcdata.natoms_ghost = 0
    return seakmcdata


def _get_dactive4_initial_relax(thissett):
    value = thissett.data.get("DActive4InitialRelax", False)
    if value is False or value is None or value == "":
        return None
    if isinstance(value, str):
        if value.strip().lower() in ("", "false", "none", "na"):
            return None
        value = value.strip()
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("data.DActive4InitialRelax must be a positive finite number or false.")
    return value


def _set_active_dactive(thissett, seakmcdata, value):
    thissett.active_volume["DActive"] = value
    if hasattr(seakmcdata, "sett") and seakmcdata.sett is not None:
        seakmcdata.sett.active_volume["DActive"] = value


def relax_initial_active_volumes(thissett, seakmcdata, force_evaluator, LogWriter,
                                 last_de_center=None, nproc_task=1, GPU_args=None):
    """Relax only active atoms of each initial active volume.

    This is the MPI-safe counterpart of the fast-scan initial relaxation hook:
    all ranks participate in each SPSRELAX call, while only rank 0 writes logs.
    """
    comm_world = MPI.COMM_WORLD
    rank_world = comm_world.Get_rank()
    if not thissett.data.get("InitialRelaxActiveOnly", False):
        return seakmcdata, 0.0
    if thissett.saddle_point.get("CalBarrsInData", False):
        error_exit("data.InitialRelaxActiveOnly does not support saddle_point.CalBarrsInData.")
    if thissett.force_evaluator["TrialDisps2Basin"].get("TrialDisps2Basin", False):
        error_exit("data.InitialRelaxActiveOnly does not support force_evaluator.TrialDisps2Basin.")

    if GPU_args is None:
        GPU_args = {}
    t_all = time.perf_counter()
    formal_dactive = float(thissett.active_volume["DActive"])
    try:
        relax_dactive = _get_dactive4_initial_relax(thissett)
    except (TypeError, ValueError) as exc:
        error_exit(str(exc))
    use_relax_dactive = relax_dactive is not None and not np.isclose(relax_dactive, formal_dactive)
    dactive_used = relax_dactive if relax_dactive is not None else formal_dactive

    ndefects_initial = seakmcdata.ndefects
    if ndefects_initial < 1:
        error_exit("InitialRelaxActiveOnly found no active volume to relax.")

    if use_relax_dactive:
        if rank_world == 0:
            logstr = (
                f"InitialRelaxActiveOnly: using data.DActive4InitialRelax={dactive_used} A "
                f"for initial local relaxation; formal active_volume.DActive={formal_dactive} A "
                "will be restored for saddle search."
            )
            if dactive_used < formal_dactive:
                logstr += (
                    "\nInitialRelaxActiveOnly warning: data.DActive4InitialRelax is smaller than "
                    "active_volume.DActive; this is allowed but may not be intended."
                )
            LogWriter.write_data(logstr)
        _set_active_dactive(thissett, seakmcdata, dactive_used)
        seakmcdata = _reset_data_for_defect_rebuild(seakmcdata)
        seakmcdata.get_defects(LogWriter, last_de_center=last_de_center)
        if seakmcdata.ndefects != ndefects_initial:
            _set_active_dactive(thissett, seakmcdata, formal_dactive)
            error_exit(
                "InitialRelaxActiveOnly aborts because data.DActive4InitialRelax changed defect count: "
                f"formal_DActive={formal_dactive} gives ndefects={ndefects_initial}, "
                f"relax_DActive={dactive_used} gives ndefects={seakmcdata.ndefects}."
            )

    if rank_world == 0:
        LogWriter.write_data(
            f"InitialRelaxActiveOnly: locally relaxing {ndefects_initial} active volumes before writing KMC_0_Data_AVs.dat."
        )

    local_energies = []
    seen_itags = set()
    try:
        for idav in range(ndefects_initial):
            t_idav = time.perf_counter()
            seakmcdata = _reset_data_for_defect_rebuild(seakmcdata)
            seakmcdata.get_defects(LogWriter, last_de_center=last_de_center)
            if seakmcdata.ndefects != ndefects_initial:
                error_exit(
                    "InitialRelaxActiveOnly aborts because defect count changed during AV rebuild: "
                    f"initial={ndefects_initial}, current={seakmcdata.ndefects}."
                )

            thisAV = seakmcdata.get_active_volume(idav, Rebuild=True)
            active_itags = thisAV.itags[0:thisAV.nactive].astype(int).copy()
            overlap = sorted(set(active_itags.tolist()).intersection(seen_itags))
            if overlap and rank_world == 0:
                LogWriter.write_data(
                    f"InitialRelaxActiveOnly warning: AV {idav} overlaps previously relaxed AVs on "
                    f"{len(overlap)} active atoms; later AV coordinates overwrite earlier ones."
                )
            seen_itags.update(active_itags.tolist())

            original_coords = thisAV.to_coords(Buffer=False, Fixed=False)
            try:
                force_evaluator.close()
            except Exception:
                pass
            force_evaluator.init_binary(comm=comm_world,
                                        Screen=thissett.force_evaluator['Screen'],
                                        Log=thissett.force_evaluator['LogFile'],
                                        **GPU_args)
            [encalc, coords, isValid, errormsg] = force_evaluator.run_runner(
                "SPSRELAX", thisAV, 0, nactive=thisAV.nactive, comm=comm_world)
            force_evaluator.close()
            comm_world.Barrier()

            coords = np.asarray(coords, dtype=float)
            if coords.size < 3 * thisAV.nactive:
                error_exit(
                    f"InitialRelaxActiveOnly aborts because SPSRELAX returned only {coords.size} coordinate values "
                    f"for AV {idav}, but {3 * thisAV.nactive} are required."
                )
            active_coords = coords[0:3 * thisAV.nactive].reshape([thisAV.nactive, 3]).T
            disps = active_coords - original_coords
            AVitags_relax = [np.array([], dtype=int) for _ in range(seakmcdata.ndefects)]
            AVitags_relax[idav] = active_itags
            seakmcdata.update_coords_from_disps(idav, disps, AVitags_relax)
            local_energies.append(encalc)
            max_disp = float(np.max(np.linalg.norm(disps.T, axis=1))) if disps.size > 0 else 0.0
            if rank_world == 0:
                if use_relax_dactive:
                    LogWriter.write_data(
                        f"InitialRelaxActiveOnly AV {idav}: DActive_used={dactive_used}, "
                        f"nactive={thisAV.nactive}, local_energy={encalc}, "
                        f"max_active_disp_A={max_disp:.6f}."
                    )
                else:
                    LogWriter.write_data(
                        f"InitialRelaxActiveOnly AV {idav}: nactive={thisAV.nactive}, "
                        f"local_energy={encalc}, max_active_disp_A={max_disp:.6f}."
                    )
            if use_relax_dactive:
                timing_print(
                    f"initial_active_av_relax idav={idav} DActive_used={dactive_used} nactive={thisAV.nactive} "
                    f"total_s={time.perf_counter() - t_idav:.6f} max_disp_A={max_disp:.6f}",
                    rank_world,
                )
            else:
                timing_print(
                    f"initial_active_av_relax idav={idav} nactive={thisAV.nactive} "
                    f"total_s={time.perf_counter() - t_idav:.6f} max_disp_A={max_disp:.6f}",
                    rank_world,
                )
    finally:
        _set_active_dactive(thissett, seakmcdata, formal_dactive)

    seakmcdata = _reset_data_for_defect_rebuild(seakmcdata)
    seakmcdata.get_defects(LogWriter, last_de_center=last_de_center)
    if seakmcdata.ndefects != ndefects_initial:
        error_exit(
            "InitialRelaxActiveOnly aborts because local relaxation changed defect count: "
            f"before={ndefects_initial}, after={seakmcdata.ndefects}."
        )
    if use_relax_dactive and rank_world == 0:
        LogWriter.write_data(
            f"InitialRelaxActiveOnly: rebuilt formal active volumes after local relaxation "
            f"with active_volume.DActive={formal_dactive} A."
        )
    eproxy = float(np.sum(local_energies)) if len(local_energies) > 0 else 0.0
    seakmcdata = comm_world.bcast(seakmcdata if rank_world == 0 else None, root=0)
    if rank_world == 0:
        LogWriter.write_data(
            "InitialRelaxActiveOnly finished. The reported ground energy is a local AV energy proxy; "
            "CalBarrsInData must remain false in this mode."
        )
    timing_print(f"initial_active_av_relax total_s={time.perf_counter() - t_all:.6f} ndefects={ndefects_initial}",
                 rank_world)
    return seakmcdata, eproxy


def run_seakmc(thissett, seakmcdata, object_dict, Eground, thisRestart):
    comm_world = MPI.COMM_WORLD
    rank_world = comm_world.Get_rank()
    size_world = comm_world.Get_size()

    out_paths = object_dict['out_paths']
    force_evaluator = object_dict['force_evaluator']
    LogWriter = object_dict['LogWriter']
    if thissett.data.get("InitialRelaxActiveOnly", False) and thissett.saddle_point.get("CalBarrsInData", False):
        error_exit(
            "data.InitialRelaxActiveOnly does not support saddle_point.CalBarrsInData. "
            "It skips global initial DATAOPT, so no global Eground is available."
        )
    if thissett.data.get("InitialRelaxActiveOnly", False) and thissett.force_evaluator["TrialDisps2Basin"].get("TrialDisps2Basin", False):
        error_exit("data.InitialRelaxActiveOnly does not support force_evaluator.TrialDisps2Basin.")
    thisSummary = object_dict['thisSummary']
    DFWriter = object_dict['DFWriter']
    GPU_args = thissett.force_evaluator["GPU"]
    nproc_task = thissett.force_evaluator["nproc"]

    THIS_PATH = out_paths[-1]
    thisExports = thisSummary.export_dict

    if thisRestart is None:
        simulation_time = 0.0
        thisSuperBasin = SuperBasin([], thissett.kinetic_MC["Temp"])
        thisSuperBasin.initialization()
        DefectBank_list = []
        if thissett.defect_bank["LoadDB"]:
            DefectBank_list = preSPS.load_DefectBanks(thissett.defect_bank, out_paths[2],
                                                      significant_figures=thissett.system["significant_figures"])
        istep_this = 0
    else:
        thisSuperBasin = thisRestart.thisSuperBasin
        DefectBank_list = thisRestart.DefectBank_list
        istep_this = thisRestart.istep_this
        simulation_time = thisRestart.simulation_time
        if thissett.system["Restart"]["Reset_Simulation_Time"]: simulation_time = 0.0

    if isinstance(thissett.active_volume["DefectCenter4RT_SetMolID"], list):
        last_de_center = thissett.active_volume["DefectCenter4RT_SetMolID"]
    else:
        last_de_center = None

    comm_world.Barrier()

    for istep in range(istep_this, thissett.kinetic_MC['NSteps']):
        if rank_world == 0:
            tickmc = time.time()
            DFWriter.init_deleted_SPs(istep)
            DFWriter.init_SPs(istep)

        if thisRestart is None:
            if thissett.force_evaluator["TrialDisps2Basin"]["TrialDisps2Basin"]:
                TDBsett = thissett.force_evaluator["TrialDisps2Basin"]
                thisTrialDisps = TrialDisps(TDBsett["Disps"], TDBsett["Ref_Length"], TDBsett["Target_StrainRate"],
                                            temp=thissett.kinetic_MC["Temp"], mindisp=TDBsett["MinDisp"],
                                            maxdisp=TDBsett["MaxDisp"],
                                            straintype=TDBsett["StrainRateType"], istep=istep)

                for itrial in range(TDBsett["nDisps"]):
                    displacement = thisTrialDisps.displacements[itrial]
                    thisTDB = TrialDisp2Basin(seakmcdata, displacement, itrial, Eground=Eground,
                                              **thisExports)

                    COMM_args = mympi.get_COMM_info(nproc_task, start_proc=0)
                    force_evaluator.init_binary(comm=COMM_args["thiscomm"],
                                                Screen=thissett.force_evaluator['Screen'],
                                                Log=thissett.force_evaluator['LogFile'],
                                                **GPU_args)
                    thisTDB.relax_basin(force_evaluator, LogWriter,
                                        ntask_tot=1, nproc_task=thissett.force_evaluator["nproc"],
                                        **COMM_args)
                    force_evaluator.close()
                    if COMM_args["isSplit"]:
                        COMM_args["thiscomm"].Free()
                    thisTDB.update_thisdata(thissett)

                    comm_world.Barrier()
                    thisTDB.run_seakmc(istep, thissett, object_dict)
                    if rank_world == 0:
                        thisTrialDisps.Add_one_trialdisp(thisTDB)
                    comm_world.Barrier()

                comm_world.Barrier()
                if rank_world == 0:
                    target_displacement = thisTrialDisps.apply_displacement()
                    logstr = "\n" + f"---summary of trial strains of {istep} KMC step---"
                    logstr += "\n" + f"trial displacements: {np.around(thisTrialDisps.displacements, 6)}"
                    logstr += "\n" + f"strains (displacements/Ref_Length):{np.around(thisTrialDisps.strains, 6)}"
                    logstr += "\n" + f"barriers: {np.around(thisTrialDisps.barrs, 6)} one_over_freqs:{np.around(thisTrialDisps.one_over_freqs, 6)}"
                    logstr += "\n" + f"strain rates:{np.around(thisTrialDisps.strainrates, 6)}"
                    logstr += "\n" + f"target strain:{np.around(thisTrialDisps.target_strain, 6)} target displacement:{np.around(target_displacement, 6)}"
                    logstr += "\n" + f"---End of trial strains of {istep} KMC step---"
                    logstr += "\n"
                    LogWriter.write_data(logstr)
                else:
                    target_displacement = None

                comm_world.Barrier()
                target_displacement = comm_world.bcast(target_displacement, root=0)
                thisTDB = TrialDisp2Basin(seakmcdata, target_displacement, TDBsett["nDisps"], Eground=Eground,
                                          **thisExports)

                COMM_args = mympi.get_COMM_info(nproc_task, start_proc=0)
                force_evaluator.init_binary(comm=COMM_args["thiscomm"],
                                            Screen=thissett.force_evaluator['Screen'],
                                            Log=thissett.force_evaluator['LogFile'],
                                            **GPU_args)
                thisTDB.relax_basin(force_evaluator, LogWriter, ntask_tot=1,
                                    nproc_task=thissett.force_evaluator["nproc"], **COMM_args)
                force_evaluator.close()
                if COMM_args["isSplit"]:
                    COMM_args["thiscomm"].Free()

                thisTDB.update_thisdata(thissett)
                seakmcdata = copy.deepcopy(thisTDB.thisdata)
                Eground = thisTDB.Eground
                thisTDB = None
                if rank_world == 0:
                    if thissett.visual["Write_Data_SPs"]["Write_KMC_Data"]:  seakmcdata.to_lammps_data(
                        out_paths[1] + "/" + "KMC_" + str(istep) + ".dat", to_atom_style=True)
                comm_world.Barrier()
            ### End of Trial Displacements 2 Basin ###
            if rank_world == 0:
                logstr = f"istep KMC: {istep}"
                LogWriter.write_data(logstr)

            seakmcdata.get_defects(LogWriter, last_de_center=last_de_center)
            if istep == 0 and thissett.data.get("InitialRelaxActiveOnly", False):
                seakmcdata, Eground = relax_initial_active_volumes(
                    thissett, seakmcdata, force_evaluator, LogWriter,
                    last_de_center=last_de_center, nproc_task=nproc_task, GPU_args=GPU_args)
            dataout.visualize_data_AVs(thissett.visual, seakmcdata, istep, out_paths[1])
            emptya = np.array([], dtype=int)
            AVitags = [emptya for i in range(seakmcdata.ndefects)]
            DataSPs = Data_SPs(istep, seakmcdata.ndefects)
            DataSPs.initialization()
            df_delete_SPs = pd.DataFrame(columns=SP_COMPACT_HEADER4Delete)
            undo_idavs = np.arange(seakmcdata.ndefects, dtype=int)
            finished_AVs = 0
            if rank_world == 0:
                if thissett.data.get("InitialRelaxActiveOnly", False):
                    logstr = (f"The local active-volume energy proxy is "
                              f"{round(Eground, thissett.system['float_precision'])} eV at {istep} KMC step; "
                              "no full-system global Eground was computed.")
                else:
                    logstr = (f"The ground energy is "
                              f"{round(Eground, thissett.system['float_precision'])} eV at {istep} KMC step!")
                logstr += "\n" + f"There are {seakmcdata.ndefects} defects (active volumes) in data at {istep} KMC step!"
                logstr += "\n" + (f"The fractional coords of the defect center are "
                                  f"{np.around(seakmcdata.de_center, decimals=thissett.system['float_precision'])} "
                                  f"at {istep} KMC step!")
                logstr += "\n"
                LogWriter.write_data(logstr)
        else:
            DataSPs = thisRestart.DataSPs
            AVitags = thisRestart.AVitags
            df_delete_SPs = thisRestart.df_delete_SPs
            undo_idavs = thisRestart.undo_idavs
            finished_AVs = thisRestart.finished_AVs
            thisRestart = None
            if rank_world == 0:
                thisdf = pd.DataFrame()
                for i in range(len(DataSPs.df_SPs)):
                    if len(DataSPs.df_SPs[i]) > 0:
                        thisdf = pd.concat([thisdf, DataSPs.df_SPs[i]], ignore_index=True)
                if len(thisdf) == 0:
                    thisdf = pd.DataFrame(columns=SP_DATA_HEADER)
                DFWriter.write_SPs(thisdf, idstart=0, mode="w")
                DFWriter.write_deleted_SPs(df_delete_SPs, idstart=0, mode="w")
                logstr = "There are " + str(len(undo_idavs)) + " undo defects (active volumes) in data!"
                LogWriter.write_data(logstr)

        comm_world.Barrier()

        DataSPs, AVitags, df_delete_SPs = dataSPS.data_find_saddlepoints(istep, thissett, seakmcdata, DefectBank_list,
                                                                         thisSuperBasin, Eground,
                                                                         DataSPs, AVitags, df_delete_SPs, undo_idavs,
                                                                         finished_AVs, simulation_time,
                                                                         DFWriter, object_dict)

        seakmcdata.to_atom_style()
        seakmcdata.velocities = None
        seakmcdata.defects = None
        seakmcdata.def_atoms = []
        seakmcdata.atoms_ghost = None
        seakmcdata.natoms_ghost = 0

        os.chdir(THIS_PATH)

        if thissett.saddle_point["CalBarrsInData"]:
            DataSPs, df_delete_this = myRecal.recalibrate_energy(thissett, DataSPs, seakmcdata, AVitags, Eground,
                                                                 object_dict)
            if rank_world == 0:
                df_delete_SPs = preSPS.update_df_delete_SPs(df_delete_SPs, df_delete_this, DFWriter)

        df_delete_this = None
        if DataSPs.nSP <= 0:
            errormsg = "###  No saddle point found! ###"
            error_exit(errormsg)

        if rank_world == 0:
            if (thissett.system["Restart"]["WriteRestart"] and
                    istep % thissett.system["Restart"]["KMCStep4Restart"] == 0):
                thisRestart = RESTART(istep, seakmcdata.ndefects, DefectBank_list, thisSuperBasin, seakmcdata, Eground,
                                      DataSPs, AVitags, df_delete_SPs, np.array([], dtype=int), simulation_time)
                thisRestart.to_file()
                thisRestart = None

            logstr = "\n" + "In KMC step ..."
            LogWriter.write_data(logstr)
            thisExports["ground_energy"] = Eground
            simulation_time, thiskmc, thisSuperBasin, thisExports = dataKMC.run_KMC(istep, thisSuperBasin,
                                                                                    seakmcdata, AVitags, DataSPs,
                                                                                    thissett, simulation_time,
                                                                                    thisExports, LogWriter)
            thisSummary.update_data(thisExports)
            thisSummary.write_data()

            this_simulation_time = thiskmc.timeelapse
            dataout.write_prob_to_file(thissett.visual, thiskmc, DataSPs, istep, out_paths[4],
                                       VerySmallNumber=thissett.system["VerySmallNumber"])
            sel_SPs = dataout.get_sel_SPs_for_out(thissett.visual, thiskmc, DataSPs)
        else:
            sel_SPs = None
            this_simulation_time = None
            thisExports = None

        comm_world.Barrier()
        sel_SPs = comm_world.bcast(sel_SPs, root=0)
        this_simulation_time = comm_world.bcast(this_simulation_time, root=0)
        thisExports = comm_world.bcast(thisExports, root=0)
        simulation_time = comm_world.bcast(simulation_time if rank_world == 0 else None, root=0)
        if len(sel_SPs) > 0:
            dataout.visualize_data_SPs(thissett.visual, seakmcdata, AVitags, DataSPs, sel_SPs, istep, out_paths[1])
        else:
            if rank_world == 0: dataout.visualize_data_SPs_Superbasin(thissett.visual, thiskmc, thisSuperBasin, istep,
                                                                      out_paths[1])

        comm_world.Barrier()
        if not thissett.kinetic_MC.get("RelaxAfterKMC", True):
            if rank_world == 0:
                LogWriter.write_data(
                    "kinetic_MC.RelaxAfterKMC=false: skipping final KMC coordinate update and OPT relaxation."
                )
            timing_print(f"relax_after_kmc skipped istep={istep}", rank_world)
            return simulation_time

        DataSPs = None
        sel_SPs = None

        if rank_world == 0:
            last_de_center = thiskmc.update_last_defect_center(thisSuperBasin)
            if isinstance(thissett.active_volume["DefectCenter4RT_SetMolID"], list):
                last_de_center = thissett.active_volume["DefectCenter4RT_SetMolID"]
            seakmcdata = thiskmc.update_coords4relaxation(thisSuperBasin)
            thisSuperBasin.prepare_next(thissett.kinetic_MC)
            AVitags = None
            thiskmc = None
            logstr = "Relaxing the structure ..."
            LogWriter.write_data(logstr)
        else:
            last_de_center = None
            AVitags = None
            thisSuperBasin = None
            AVitags = None
            thiskmc = None
            seakmcdata = None

        comm_world.Barrier()
        seakmcdata = comm_world.bcast(seakmcdata, root=0)
        last_de_center = comm_world.bcast(last_de_center, root=0)

        COMM_args = mympi.get_COMM_info(nproc_task, start_proc=0)
        force_evaluator.init_binary(comm=COMM_args["thiscomm"],
                                    Screen=thissett.force_evaluator['Screen'], Log=thissett.force_evaluator['LogFile'],
                                    **GPU_args)
        [Eground, relaxed_coords, isValid, errormsg] = mydatadyn.data_dynamics("OPT", force_evaluator, seakmcdata, 1,
                                                                               nactive=seakmcdata.natoms,
                                                                               nproc_task=nproc_task,
                                                                               thisExports=thisExports, **COMM_args)
        force_evaluator.close()
        if COMM_args["isSplit"]: COMM_args["thiscomm"].Free()

        if rank_world == 0:
            for f in os.listdir("Runner_0/"):
                for i in range(len(thissett.force_evaluator["OutFileHeaders"])):
                    if thissett.force_evaluator["OutFileHeaders"][i] in f:
                        shutil.copy("Runner_0/" + f, out_paths[1] + "/KMC_" + str(istep + 1) + "_" + f)

        seakmcdata = SeakmcData.from_file("Runner_0/tmp1.dat", atom_style=thissett.data['atom_style_after'])
        seakmcdata.assert_settings(thissett)
        seakmcdata.to_atom_style()
        seakmcdata.velocities = None
        if rank_world == 0:
            if thissett.visual["Write_Data_SPs"]["Write_KMC_Data"]:  seakmcdata.to_lammps_data(
                out_paths[1] + "/" + "KMC_" + str(istep + 1) + ".dat", to_atom_style=True)

            tockmc = time.time()
            logstr = "\n" + "KMC " + str(istep) + "th step is finished."
            logstr += "\n" + (f"Time step for {istep} KMC step: "
                              f"{round(this_simulation_time, thissett.system['float_precision'])} ps")
            logstr += "\n" + (f"Summed time steps after {istep} "
                              f"KMC step: {round(simulation_time, thissett.system['float_precision'])} ps")
            logstr += "\n" + (f"Real time cost for {istep} "
                              f"KMC step: {round(tockmc - tickmc, thissett.system['float_precision'])} s")
            logstr += "\n" + "==================================================================="
            LogWriter.write_data(logstr)

        comm_world.Barrier()

        '''
        MPI.Finalize()
        #MPI.Init()
        comm_world = MPI.COMM_WORLD
        rank_world = comm_world.Get_rank()
        size_world = comm_world.Get_size()
        '''

    return simulation_time
