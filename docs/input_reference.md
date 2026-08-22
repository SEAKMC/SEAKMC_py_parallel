# SEAKMC input reference

Generated from the settings defaults by `seakmc schema --markdown`.
Do not edit by hand.

Required sections: `data`, `potential`, `kinetic_MC`, `active_volume`, `spsearch`, `saddle_point`

Optional sections: `system`, `force_evaluator`, `dynamic_matrix`, `defect_bank`, `visual`

## `data` (required)

| setting | notes |
|---|---|
| `BoxRelax` | default: False (unset; may also take a value) |
| `MoleDyn` | default: False (unset; may also take a value) |
| `Relaxed` | default: True |
| `RinputMD` | default: False (unset; may also take a value) |
| `RinputMD0` | default: False (unset; may also take a value) |
| `RinputOpt` | default: False (unset; may also take a value) |
| `boundary` | default: 'p p p' |
| `dimension` | default: 3 |
| `units` | default: 'metal' |
| `FileName` | supplied by the user; no default |
| `atom_style` | supplied by the user; no default |

## `potential` (required)

no defaults registry; keys are not checked

## `kinetic_MC` (required)

| setting | notes |
|---|---|
| `AccStyle` | default: 'NoAcc' |
| `DispStyle` | default: 'FI' |
| `EnCut4Transient` | default: 0.5 -- must be a number |
| `Handle_no_Backward` | default: 'Out' |
| `NMaxBasin` | default: "NA" (no limit) |
| `NSteps` | default: 1 -- must be a number |
| `Sorting` | default: False (unset; may also take a value) |
| `Temp` | default: 800.0 -- must be a number |
| `Temp4Time` | default: 800.0 |
| `Tol4Barr` | default: 0.03 -- must be a number |
| `Tol4Disp` | default: 0.1 -- must be a number |

## `active_volume` (required)

| setting | notes |
|---|---|
| `DActive` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `DBuffer` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `DCut4PDR` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `DCut4noOverlap` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `DFixed` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `DefectCenter4RT_SetMolID` | default: 'AUTO' |
| `Exclusive` | default: True |
| `FCT4RT_SetMolID` | list, default: ['INF', 'INF', 'INF', 'INF', 'INF', 'INF'] |
| `FindDefects` | mapping with 3 key(s) |
| `FindDefects.DiscardType` | list, default: [] |
| `FindDefects.Method` | default: 'BLCN' |
| `FindDefects.MolIDCap` | default: "NA" (no limit) |
| `FindDefects.atom_style4Ref` | supplied by the user; no default |
| `FindDefects.ReferenceData` | supplied by the user; no default |
| `FindDefects.Defects` | supplied by the user; no default |
| `FindDefects.DCut4Def` | supplied by the user; no default |
| `MaxBreadth4Recursive4AV` | default: not set |
| `MaxBreadth4Recursive4PDR` | default: not set |
| `NMax4AV` | default: False (unset; may also take a value) |
| `NMax4Def` | default: False (unset; may also take a value) |
| `NMax4PG` | default: 1000 |
| `NMin4AV` | default: 40 -- must be a number |
| `NMin_perproc` | default: 5 -- must be a number |
| `NPredef` | default: 0 |
| `Overlapping` | default: True |
| `PBC` | list, default: [False, False, False] |
| `PDReduction` | default: True |
| `PointGroupSymm` | default: False (unset; may also take a value) |
| `PredefOnly` | default: False (unset; may also take a value) |
| `R4RT_SetMolID` | default: 30 -- must be a number |
| `RT_SetMolID` | default: False (unset; may also take a value) |
| `RecursiveRed` | default: False (unset; may also take a value) |
| `SortD4PDR` | default: False (unset; may also take a value) |
| `Sort_by` | list, default: ['D', 'X', 'Y', 'Z'] |
| `Sorting` | default: True |
| `SortingBuffer` | default: False (unset; may also take a value) |
| `SortingFixed` | default: False (unset; may also take a value) |
| `SortingShift` | list, default: [0.0, 0.0, 0.0] |
| `SortingSpacer` | list, default: [0.3, 0.3, 0.3] |
| `Stack4noOverlap` | default: False (unset; may also take a value) |
| `Style` | default: 'defects' |
| `cutdefectmax` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `NActive` | supplied by the user; no default |
| `NBuffer` | supplied by the user; no default |
| `NFixed` | supplied by the user; no default |
| `TurnoffPBC` | supplied by the user; no default |

## `spsearch` (required)

| setting | notes |
|---|---|
| `ActiveOnly4SPConfig` | default: True |
| `AngCut` | default: 2.0 |
| `ApplyMass` | default: False (unset; may also take a value) |
| `CheckAng` | default: True |
| `CheckAngSteps` | default: 50 |
| `DCut4SPAtom` | default: 0.01 |
| `DRatio4Relax` | default: 2.0 |
| `DecayRate` | default: 0.71 |
| `DecaySteps` | default: 20 |
| `DecayStyle` | default: 'Fixed' |
| `DimerSep` | default: 0.005 -- must be a number |
| `DynCut4SPAtom` | default: False (unset; may also take a value) |
| `En4TransHorizon` | default: 0.1 |
| `EnConv` | default: 1e-05 -- must be a number |
| `FConv` | default: 1e-06 -- must be a number |
| `FMin4Rot` | default: 0.001 |
| `FThres4Rot` | default: 0.1 |
| `FixAxesStr` | default: 'ALL' |
| `FixTypes` | default: False (unset; may also take a value) |
| `HandleVN` | mapping with 24 key(s) |
| `HandleVN.AngTol4Init` | default: 5.0 |
| `HandleVN.CenterVN` | default: False (unset; may also take a value) |
| `HandleVN.CheckAng4Init` | default: True |
| `HandleVN.IgnoreSteps` | default: 4 |
| `HandleVN.Int4ComputeScale` | default: 1 |
| `HandleVN.MaxIter4Init` | default: 20 |
| `HandleVN.MinSpan4LOGV` | default: 4.0 |
| `HandleVN.MinSpan4RAS` | default: 40.0 |
| `HandleVN.MinValue4LOGV` | default: -20.0 |
| `HandleVN.NMaxRandVN` | default: 20 |
| `HandleVN.NSteps4CenterVN` | default: 5 |
| `HandleVN.Period4MA` | default: 1 |
| `HandleVN.PowerOnV` | default: 4 |
| `HandleVN.Ratio4Zero4LOGV` | default: 0.2 |
| `HandleVN.Ratio4Zero4RAS` | default: 0.3 |
| `HandleVN.RatioVN04Preload` | default: 0.2 |
| `HandleVN.RescaleStyle4LOGV` | default: 'SIGMOID' |
| `HandleVN.RescaleStyle4RAS` | default: 'SIGMOID' |
| `HandleVN.RescaleVN` | default: True |
| `HandleVN.RescaleValue` | default: 'LOGVN' |
| `HandleVN.ResetVN04Preload` | default: True |
| `HandleVN.TakeMin4MixedRescales` | default: True |
| `HandleVN.XRange4LOGV` | default: 20.0 |
| `HandleVN.XRange4RAS` | default: 40.0 |
| `IgnoreSteps` | default: 4 |
| `IgnoreStepsFine` | default: 2 |
| `Inteval4ShowIterationResults` | default: 1 |
| `LocalRelax` | mapping with 4 key(s) |
| `LocalRelax.InitTemp4Opt` | default: 0.0 |
| `LocalRelax.LocalRelax` | default: True |
| `LocalRelax.NVTSteps4Opt` | default: 1000 |
| `LocalRelax.TargetTemp4NVT` | default: 5.0 |
| `Master_Slave` | default: True |
| `MaxStepsize` | default: 0.05 -- must be a number |
| `MaxStepsizeFine` | default: 0.01 |
| `Method` | default: 'dimer' |
| `MinStepsize` | default: 0.003 -- must be a number |
| `NMax4Rot` | default: 3 -- must be a number |
| `NMax4Trans` | default: 1000 -- must be a number |
| `NSearch` | default: 10 -- must be a number |
| `OutFix4IterationResults` | default: False (unset; may also take a value) |
| `OutForces4IterationResults` | default: False (unset; may also take a value) |
| `Preloading` | mapping with 10 key(s) |
| `Preloading.CheckSequence` | default: False (unset; may also take a value) |
| `Preloading.FileHeader` | default: 'SPS_AV_' |
| `Preloading.FileHeader4Data` | default: 'SPS_basin_' |
| `Preloading.IgnoreType` | default: True |
| `Preloading.LoadPath` | default: False (unset; may also take a value) |
| `Preloading.Method` | default: 'Files' |
| `Preloading.Preload` | default: False (unset; may also take a value) |
| `Preloading.Ratio4DispLoad` | default: 0.8 |
| `Preloading.Scaling` | default: 1.0 |
| `Preloading.SortDisps` | default: False (unset; may also take a value) |
| `R2Dmax4SPAtom` | default: 0.04 |
| `SearchBuffer` | default: False (unset; may also take a value) |
| `ShowCoords4ShowIterationResults` | default: False (unset; may also take a value) |
| `ShowIterationResults` | default: False (unset; may also take a value) |
| `ShowVN4ShowIterationResults` | default: False (unset; may also take a value) |
| `TaskDist` | default: 'AV' |
| `Tol4Connect` | default: 0.1 |
| `TransHorizon` | default: True |
| `TrialStepsize` | default: 0.015 -- must be a number |
| `TrialStepsizeFine` | default: 0.003 |
| `force_evaluator` | inherited from the top-level force_evaluator section |
| `force_evaluator.Bin` | inherited from the top-level force_evaluator section |
| `force_evaluator.GPU` | inherited from the top-level force_evaluator section |
| `force_evaluator.ImportValue4RinputOpt` | inherited from the top-level force_evaluator section |
| `force_evaluator.Keys4ImportValue4RinputOpt` | inherited from the top-level force_evaluator section |
| `force_evaluator.LogFile` | inherited from the top-level force_evaluator section |
| `force_evaluator.Master_Slave4ReCal` | inherited from the top-level force_evaluator section |
| `force_evaluator.NSteps4Relax` | inherited from the top-level force_evaluator section |
| `force_evaluator.OutFileHeaders` | inherited from the top-level force_evaluator section |
| `force_evaluator.Path2Bin` | inherited from the top-level force_evaluator section |
| `force_evaluator.Rinput` | inherited from the top-level force_evaluator section |
| `force_evaluator.RinputDM` | inherited from the top-level force_evaluator section |
| `force_evaluator.RinputMD0` | inherited from the top-level force_evaluator section |
| `force_evaluator.RinputOpt` | inherited from the top-level force_evaluator section |
| `force_evaluator.Screen` | inherited from the top-level force_evaluator section |
| `force_evaluator.Style` | inherited from the top-level force_evaluator section |
| `force_evaluator.TrialDisps2Basin` | inherited from the top-level force_evaluator section |
| `force_evaluator.nproc` | inherited from the top-level force_evaluator section |
| `force_evaluator.nproc4ReCal` | inherited from the top-level force_evaluator section |
| `force_evaluator.partition` | inherited from the top-level force_evaluator section |
| `force_evaluator.processors` | inherited from the top-level force_evaluator section |
| `force_evaluator.timestep` | inherited from the top-level force_evaluator section |

## `saddle_point` (required)

| setting | notes |
|---|---|
| `BackBarrierMin` | default: 0.0 |
| `BarrierCut` | default: 10.0 -- must be a number |
| `BarrierMin` | default: 0.0 -- must be a number |
| `CalBarrsInData` | default: False (unset; may also take a value) |
| `CalEbiasInData` | default: False (unset; may also take a value) |
| `DAtomCut` | derived from the interatomic potential (a multiple of cutdefectmax); omit to accept it |
| `DmagCut` | default: "NA" (no limit) |
| `DmagCut_FI` | default: "NA" (no limit) |
| `DmagCut_FS` | default: "NA" (no limit) |
| `DmagMin` | default: 0.0 |
| `DmagMin_FI` | default: 0.0 |
| `DmagMin_FS` | default: 0.0 |
| `DmaxCut` | default: "NA" (no limit) |
| `DmaxCut_FI` | default: "NA" (no limit) |
| `DmaxCut_FS` | default: "NA" (no limit) |
| `DmaxMin` | default: 0.0 |
| `DmaxMin_FI` | default: 0.0 |
| `DmaxMin_FS` | default: 0.0 |
| `DsumCut` | default: "NA" (no limit) |
| `DsumCut_FI` | default: "NA" (no limit) |
| `DsumCut_FS` | default: "NA" (no limit) |
| `DsumMin` | default: 0.0 |
| `DsumMin_FI` | default: 0.0 |
| `DsumMin_FS` | default: 0.0 |
| `DsumrCut` | default: "NA" (no limit) |
| `DsumrCut_FI` | default: "NA" (no limit) |
| `DsumrCut_FS` | default: "NA" (no limit) |
| `DsumrMin` | default: 0.0 |
| `DsumrMin_FI` | default: 0.0 |
| `DsumrMin_FS` | default: 0.0 |
| `DtotCut` | default: "NA" (no limit) |
| `DtotCut_FI` | default: "NA" (no limit) |
| `DtotCut_FS` | default: "NA" (no limit) |
| `DtotMin` | default: 0.0 |
| `DtotMin_FI` | default: 0.0 |
| `DtotMin_FS` | default: 0.0 |
| `EbiasCut` | default: "NA" (no limit) |
| `EbiasMin` | default: "NA" (no limit) |
| `Prefactor` | default: 10.0 -- must be a number |
| `Thres4Recalib` | default: not set |
| `ValidSPs` | mapping with 27 key(s) |
| `ValidSPs.AND4ScreenDE` | default: True |
| `ValidSPs.AngCut4GSP` | default: 10.0 |
| `ValidSPs.AngCut4Type` | default: 5.0 |
| `ValidSPs.CheckConnectivity` | default: True |
| `ValidSPs.EnCut4GSP` | default: 0.1 |
| `ValidSPs.EnCut4Type` | default: 0.05 |
| `ValidSPs.EnTol4AVSP` | default: 0.1 |
| `ValidSPs.FindSPType` | default: False (unset; may also take a value) |
| `ValidSPs.GroupSP` | default: False (unset; may also take a value) |
| `ValidSPs.LenCut4Type` | default: 0.05 |
| `ValidSPs.MagCut4GSP` | default: 0.1 |
| `ValidSPs.MagCut4Type` | default: 0.05 |
| `ValidSPs.MaxRatio4Barr` | default: "NA" (no limit) |
| `ValidSPs.MaxRatio4Dmag` | default: "NA" (no limit) |
| `ValidSPs.NCommonMin` | default: 10 |
| `ValidSPs.NMax4Dup` | default: 600 |
| `ValidSPs.NScreenDisp` | default: 0 |
| `ValidSPs.NScreenEng` | default: 0 |
| `ValidSPs.R2Dmax4Tol` | default: 0.1 |
| `ValidSPs.RealtimeDelete` | default: False (unset; may also take a value) |
| `ValidSPs.RealtimeValid` | default: False (unset; may also take a value) |
| `ValidSPs.ScreenDisp` | mapping with 6 key(s) |
| `ValidSPs.ScreenEng` | mapping with 4 key(s) |
| `ValidSPs.Tol4AVSP` | default: 0.1 |
| `ValidSPs.Tol4Disp` | default: 0.1 |
| `ValidSPs.toScreenDisp` | default: 'NotConn' |
| `ValidSPs.toScreenEng` | default: 'NotConn' |

## `system` (optional)

| setting | notes |
|---|---|
| `Interval4ShowProgress` | default: 10 -- must be a number |
| `RandomSeed` | default: not set |
| `Restart` | mapping with 6 key(s) |
| `Restart.AVStep4Restart` | default: 1000 |
| `Restart.KMCStep4Restart` | default: 1 |
| `Restart.LoadFile` | default: not set |
| `Restart.LoadRestart` | default: True |
| `Restart.Reset_Simulation_Time` | default: False (unset; may also take a value) |
| `Restart.WriteRestart` | default: True |
| `TempFiles` | list, default: ['tmp0.dat', 'tmp1.dat', 'tmp2.dat'] |
| `Tolerance` | default: 0.1 |
| `VerySmallNumber` | default: 1e-20 |
| `angle_tolerance` | default: 5.0 |
| `float_precision` | default: 3 |
| `significant_figures` | default: 6 |

## `force_evaluator` (optional)

| setting | notes |
|---|---|
| `Bin` | default: 'pylammps' |
| `GPU` | default: not set |
| `ImportValue4RinputOpt` | default: False (unset; may also take a value) |
| `Keys4ImportValue4RinputOpt` | list, default: [['Timestep', 'time_step']] |
| `LogFile` | default: False (unset; may also take a value) |
| `Master_Slave4ReCal` | default: False (unset; may also take a value) |
| `NSteps4Relax` | default: 10000 |
| `OutFileHeaders` | list, default: [] |
| `Path2Bin` | default: False (unset; may also take a value) |
| `Relaxation` | mapping with 4 key(s) |
| `Relaxation.BoxRelax` | default: False (unset; may also take a value) |
| `Relaxation.InitTemp4Opt` | default: 0.0 |
| `Relaxation.NVTSteps4Opt` | default: 10000 |
| `Relaxation.TargetTemp4NVT` | default: 5.0 |
| `RinputMD0` | default: False (unset; may also take a value) |
| `RinputOpt` | default: False (unset; may also take a value) |
| `Screen` | default: False (unset; may also take a value) |
| `Style` | default: 'pylammps' |
| `TrialDisps2Basin` | mapping with 10 key(s) |
| `TrialDisps2Basin.Disps` | list, default: [0.001, 0.002, 0.004, 0.008] |
| `TrialDisps2Basin.Keys4ImportValue4RinputTDB` | list, default: [['displacement equal', 'displacement']] |
| `TrialDisps2Basin.MaxDisp` | default: 0.01 |
| `TrialDisps2Basin.MinDisp` | default: 0.0001 |
| `TrialDisps2Basin.Ref_Length` | default: not set |
| `TrialDisps2Basin.RinputTDB` | default: not set |
| `TrialDisps2Basin.StrainRateType` | default: 1 |
| `TrialDisps2Basin.Target_StrainRate` | default: not set |
| `TrialDisps2Basin.TrialDisps2Basin` | default: False (unset; may also take a value) |
| `TrialDisps2Basin.nDisps` | default: 4 |
| `nproc` | default: 'auto' |
| `nproc4ReCal` | default: 'auto' |
| `partition` | default: False (unset; may also take a value) |
| `processors` | default: False (unset; may also take a value) |
| `timestep` | default: 0.002 |

## `dynamic_matrix` (optional)

| setting | notes |
|---|---|
| `CalPrefactor` | default: False (unset; may also take a value) |
| `LowerHalfMat` | default: False (unset; may also take a value) |
| `Method4Prefactor` | default: 'harmonic' |
| `NMax4SNC` | default: 1000 |
| `OutDynMat` | default: False (unset; may also take a value) |
| `SNC` | default: False (unset; may also take a value) |
| `VibCut` | default: 1e-08 |
| `delimiter` | default: ' ' |
| `displacement` | default: 1e-06 |

## `defect_bank` (optional)

| setting | notes |
|---|---|
| `FileHeader` | default: 'DB' |
| `IgnoreType` | default: True |
| `LoadDB` | default: False (unset; may also take a value) |
| `LoadPath` | default: 'DefectBank' |
| `NMax4DB` | default: 100 |
| `NMin4DB` | default: 8 |
| `OutIndex` | default: True |
| `Preload` | default: False (unset; may also take a value) |
| `Ratio4DispLoad` | default: 0.8 |
| `Recycle` | default: False (unset; may also take a value) |
| `SaveDB` | default: False (unset; may also take a value) |
| `SavePath` | default: 'DefectBank' |
| `Scaling` | default: 1.0 |
| `SortDisps` | default: False (unset; may also take a value) |
| `Tol4Disp` | default: 0.1 |
| `UseSymm` | default: False (unset; may also take a value) |

## `visual` (optional)

| setting | notes |
|---|---|
| `DCut4Vis` | default: 0.01 |
| `Invisible` | default: True |
| `Log` | default: True |
| `LogFile` | default: 'Seakmc.log' |
| `RCut4Vis` | default: 0.04 |
| `Reset_Index` | default: False (unset; may also take a value) |
| `Screen` | default: True |
| `ShowBuffer` | default: False (unset; may also take a value) |
| `ShowFixed` | default: False (unset; may also take a value) |
| `Write_AV_SPs` | mapping with 6 key(s) |
| `Write_AV_SPs.AVOutPath` | default: 'AVOut' |
| `Write_AV_SPs.DispStyle4AVSP` | default: 'BOTH' |
| `Write_AV_SPs.OutputStyle` | default: 'SEP' |
| `Write_AV_SPs.Write_AV_SPs` | default: False (unset; may also take a value) |
| `Write_AV_SPs.Write_Data_AV_SPs` | default: False (unset; may also take a value) |
| `Write_AV_SPs.Write_Local_AV` | default: False (unset; may also take a value) |
| `Write_Data_SPs` | mapping with 11 key(s) |
| `Write_Data_SPs.DataOutPath` | default: 'DataOut' |
| `Write_Data_SPs.DetailOut` | default: True |
| `Write_Data_SPs.DispStyle4DataSP` | default: 'Both' |
| `Write_Data_SPs.Offset` | default: 0 |
| `Write_Data_SPs.OutputStyle` | default: 'SEP' |
| `Write_Data_SPs.SPs4Detail` | default: 'AUTO' |
| `Write_Data_SPs.Sel_iSPs` | default: 'AUTO' |
| `Write_Data_SPs.Write_Data_AVs` | default: True |
| `Write_Data_SPs.Write_Data_SPs` | default: True |
| `Write_Data_SPs.Write_KMC_Data` | default: True |
| `Write_Data_SPs.Write_Prob` | default: True |
| `Write_SP_Summary` | default: True |

