# Code and Data -- Solid-State Transformer Interfaces for PV-BESS Microgrids

This repository backs two papers:

**Paper 1** -- "Switching-Verified Design and Grid-Disturbance
Ride-Through of a Three-Stage Solid-State Transformer Interface for a
PV-BESS Microgrid" -- design, switching-resolution verification,
disturbance-rejection testing, and Monte Carlo statistical analysis of a
CHB+DAB+LV-inverter SST versus a conventional LFT+VSC interface. Code
and manuscript are at the repository root (`code/`, `results/`,
`paper/Paper1_SST_Hardware.docx`).

**Paper 2** -- "Does a Smarter Grid Interface Change What a Supervisory
Reinforcement-Learning Energy Manager Must Learn? Observation Design,
Retraining, and Techno-Economics for an SST-Interfaced PV-BESS
Microgrid" -- companion paper studying what Paper 1's interface swap
means for a supervisory RL energy-management policy. Code, checkpoints,
manuscript, and its own README with per-script fidelity notes are under
`paper2/`.

## Scope note (Paper 1)

These scripts implement the full manuscript methodology, including every
reported table and figure value. Closed-form results (DAB power transfer,
the analytic ride-through Thold formula, the PI cell-balancing gains, the
open-loop drift-rate formula) reproduce the paper's own reported numbers
**essentially exactly**, since they follow directly from stated equations.
Simulation-based results are close but not bit-identical, because some
inputs aren't specified to bit-for-bit precision in the manuscript text
itself (see per-script notes below).

**Before treating any number here as authoritative, re-run the relevant
script yourself and compare against the specific figure you intend to
cite or revise.**

## Per-script fidelity notes

| Script | Match to paper | Known gap |
|---|---|---|
| `sst_dab_model.py` | Essentially exact (0.18% vs paper's 0.08% max error over a 17-point sweep across d=0.10-0.50; ZVS boundary exact) | Discretization-resolution dependent, tunable |
| `sst_chb_model.py` | Close (97.5% delivered / 0.68% TDD vs paper's 99.1% / 0.56%) | Exact filter ESR / control-angle convention not given in text |
| `sst_losses.py` | Correct qualitative trend (efficiency rises as carrier frequency drops); CHB/full-SST efficiency run ~1-3 points optimistic (99.7%/96.9% vs paper's 98.85%/94.31%) | Uses fixed representative RMS currents per device position, not full waveform integration; manufacturer Foster-network tables not reproduced in manuscript text so representative values are used instead |
| `sst_sim.py` | Trip timing and MV-link SOC essentially exact (e.g. 453.3ms vs 453.2ms, 0.833pu vs 0.833pu) | SST post-budget throttle-law gain approximated (paper states it qualitatively, not numerically) |
| `sst_montecarlo.py` | Conventional trip rate near-exact (59.6% vs 57.8%); SST direction/dominance confirmed | Depends on both the throttle-law approximation above and on `sst_real_profiles.py`'s synthetic PV-event catalog (see below) -- the trip-rate split is not currently traceable to the real NREL event population the manuscript describes |
| `sst_balancing.py` | Essentially exact on every headline number (6.412s vs 6.4s; 0.144%/0.211s vs 0.14%/0.21s; 1.053s vs 1.05s) | -- |
| `sst_thermal_transient.py` | Correct qualitative behavior (CHB cools, DAB primary heats, SiC smallest) | Magnitudes ~5-20x off; same Foster-network limitation as sst_losses.py |
| `sst_real_profiles.py` | N/A (data provenance) | Real NREL SRRL BMS data could not be fetched (robots.txt + network sandboxing); a documented synthetic stand-in with matching statistical character is used instead. Drop the real CSV in `data/` to override. |

## Files

```
code/         10 Python scripts (simulation, analysis, plotting)
data/         NREL solar data (synthetic stand-in unless you supply the real CSVs -- see sst_real_profiles.py)
results/      JSON result summaries + figs/ (regenerated plots)
```

## Dependencies

```
pip install -r requirements.txt
```

## Running

Simplest: run everything in the correct order with one command:

```bash
cd code && python3 run_all.py
```

Or run each script standalone from inside `code/` (mind the order --
`sst_plots.py` and `sst_graphical_abstract.py` read results/ files the
earlier scripts produce, and `sst_montecarlo.py` reads the event catalog
`sst_real_profiles.py` produces):

```bash
python3 sst_dab_model.py
python3 sst_chb_model.py
python3 sst_losses.py
python3 sst_sim.py
python3 sst_real_profiles.py
python3 sst_montecarlo.py
python3 sst_balancing.py
python3 sst_thermal_transient.py
python3 sst_plots.py                  # after the above have populated results/
python3 sst_graphical_abstract.py     # after sst_losses.py and sst_montecarlo.py
```

## Data provenance

`sst_real_profiles.py`'s module docstring documents exactly what could and
could not be retrieved for the NREL SRRL BMS irradiance data, and how to
supply the real file if you have it.

## Citation

See `CITATION.cff`.
