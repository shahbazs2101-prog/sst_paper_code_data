# SST Paper 1 — current reproducibility materials

This repository now accompanies the finalized simulation-only manuscript in [current/Manuscript](current/Manuscript). The earlier Python reconstruction and manuscript are preserved under [legacy](legacy); they are not the current paper's authoritative results.

## Current materials
- `current/Code_MATLAB/`: development stages, kept in separate folders.
- `current/Executed_Results/`: executed source snapshots, summary CSVs and execution logs.
- `current/Audit/Stage6_FullStep/`: audit script, expected summary, original mixed-file report, interpretation and 132 passing full-step records.
- `current/Python_Supplement/`: separate ideal switching, energy, balancing and irradiance sensitivity analyses.
- `current/Manuscript/`: final coauthor-review Word and PDF manuscript.

## Stage 6 findings
The 132 runs cover three implementations, 11 cases, two reference variants and two time steps.

| Implementation | Baseline trips | 20 ms ramp trips |
|---|---:|---:|
| Original SST | 7/11 | 3/11 |
| SST with min–max injection | 3/11 | 3/11 |
| Matched conventional interface | 3/11 | 3/11 |

Min–max injection removes four additional baseline SST overcurrent trips. Equal remaining trip counts do not imply equal failure mechanisms: the remaining SST trips are MV-cell undervoltage and the conventional trips LV undervoltage. These selected cases establish no inherent SST ride-through advantage.

Both time steps agree on trip outcomes and cause masks. All 132 expected full-step records pass the author's local audit; the mixed report also contains downsampled exports and a summary MAT outside the full-step schema. Read the audit interpretation before using its aggregate flag.

## Reproducing and checking
For the executed Stage 6 equations, open `current/Executed_Results/Stage6_20261002_190112/executed_source/` in MATLAB/Simulink and run `RUN_STAGE6`. The author used MATLAB R2025b. This runs simulations and creates new outputs. Do not mix stage scripts in a flat folder.

To audit existing full-step records without rerunning simulations, keep `AUDIT_STAGE6_RAW.m` and `expected_stage6_summary.csv` together, run the audit script and select only the timestamp folder containing the 132 full-step records.

For separate Python analyses, install `current/Python_Supplement/requirements.txt`, enter that directory, then run `python run_all.py`, `python verify_results.py` and `python verify_data.py`. Consult that folder's README for model boundaries.

## Data and limits
The complete approximately 1.8 GB full-step MAT archive is retained by the author and is not included here. Audit hashes identify those local records. Summary/log files are not substitutes for full waveforms. Coordinate access to full records with the corresponding author; this repository does not claim a public raw-data deposit.

The supplied irradiance archive and processing provenance support a separate energy sensitivity. Coupled sag/demand inputs are synthetic. Models are simulations; device-level ZVS, hardware validation and field outage probabilities are not established.

## Version status
Snapshot assembled from `SST_Paper1_Compiled_Master_v4.zip` on 2026-10-03 (India). Scientific coauthor assessment, journal choice, declarations and journal-specific requirements remain before submission. No acceptance or publication is claimed.

The previous repository snapshot is commit `36c31b83d7a9773e982365cbcee446e58c05689d`. Paper 2 remains in its separate repository.
