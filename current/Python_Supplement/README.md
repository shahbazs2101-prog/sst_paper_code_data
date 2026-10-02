# SST electrical benchmarking supplementary package

Run `python run_all.py` from this directory, then `python verify_results.py`.
Install dependencies with `python -m pip install -r requirements.txt`.
The models are ideal and separate; no coupled closed-loop SST or hardware test is claimed.

## Executed analyses
- `chb_verified.py`: event-resolved unipolar CHB switching, periodic RL current, seven-level verification, RMS harmonic normalization and sampling sensitivity.
- `sst_dab_model.py`: prescribed ideal SPS switching with half-period displacement d, so the secondary delay is d*T/2. Polarity checks are necessary conditions only, not verified device-level ZVS.
- `reproduce.py`: usable energy, deterministic sag events, seed-7 conditional randomized trials, and supplied irradiance magnitude extraction.
- `interface_sensitivity.py`: seeds 7/19/42, fixed-input energy-budget sensitivity, and constant-interruption DAB headroom boundary.
- `balancing_verified.py`: voltage-dependent asymmetric headroom, zero-sum box projection, nonlinear phase-shift inversion, exact energy-state update and mismatch/time-step sensitivity.
- `make_figures.py`: DAB waveforms and control-boundary diagrams.
- `verify_results.py`: independent checks of energy matching, voltage levels, phase inversion, box feasibility, aggregate energy and matched outcomes.

## Principal results
27.197775 kJ usable MV-link energy matches 236.092 mF on the LV bus.
Both energy-only matched interfaces provide 453.296 ms at 60 kW.
Seed 7: 405/500 conventional-ripple trips and 284/500 for each matched interface.
At 150 kW, the DAB headroom boundary gives an effective floor of 0.909975 pu and 112.349 ms hold-up; the ideal matched LV comparator gives 181.319 ms.
The primary 3% seed-19 balancing draw peaks at 0.13554% and settles in 1.011 s.
Every tested 20% draw saturates and fails to settle below 0.05% within 8 s.

## Source and interpretation
User-supplied BMS measurement archive with Year/DOY/MST and instrument headers; processed GHI exactly equals the Global CMP22 (vent/cor) channel clipped at zero. Download script targets the NREL MIDC endpoint for 2022-01-20. Independent server authentication was not possible. Raw data, download script, processing description and both checksums are included. verify_data.py checks all 1440 samples and timestamp alignment.
The PV/load coincidence assumptions are synthetic steps. Trip percentages are conditional sensitivities, not field outage probabilities. SST/matched energy-only outcomes are identical by construction; additional seeds do not provide independent evidence of topology equivalence.
The 150 kW headroom result is an analytical constant-demand boundary, not a full converter-dynamics experiment. The baseline assumes ideal LV-side full-power regulation.
