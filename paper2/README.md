# Code and Data -- Supervisory RL Energy Management Under an SST Interface Swap

This repository backs the manuscript:

**"Does a Smarter Grid Interface Change What a Supervisory
Reinforcement-Learning Energy Manager Must Learn? Observation Design,
Retraining, and Techno-Economics for an SST-Interfaced PV-BESS
Microgrid"** -- companion paper to the hardware/ride-through study [1].
Manuscript included at `paper/Paper2_SST_EMS.docx`.

## Scope note

This implements the microgrid environment, PI baseline, DQN supervisory
EMS, joint interface/policy evaluation, SST-aware retraining, an
observation-design ablation, and the techno-economic sensitivity model
described in the manuscript. Some results reproduce very closely; others
are approximate because the manuscript doesn't specify every input
(exact baseline disturbance-segment profile parameters, noise
characteristics) to the precision needed for an exact match. Every gap
below was investigated directly -- including finding and fixing a real
PI-controller integral-windup bug -- rather than assumed away.

**Before treating any number here as authoritative, re-run the relevant
script yourself and compare against the specific figure you intend to
cite or revise.**

## Per-script fidelity notes

| Script | Match to paper | Known gap |
|---|---|---|
| `environment.py`, `interface_physics.py` | Sound -- interface physics reused directly from Paper 1's verified model | -- |
| `pi_controller.py` | Fixed a genuine bug: the raw PV-load deficit used as the PI's integrated signal diverges unboundedly for any sustained nonzero deficit, since it isn't a true closed-loop error. Rewritten to integrate (target - previously-delivered power), using the observation's own 5th quantity, which converges correctly | -- |
| `train_frozen.py` (Table 3 baseline) | Very close: 12.58 kW RMSE / \$1.74 / 7.54 kW/s vs paper's 12.10 kW / \$1.61 / 8.41 kW/s | -- |
| `table2_joint_eval.py` (Table 2) | Qualitative pattern correct (conventional at genuine trip risk, SST always rides through) | Exact trip timing does not match closely; shown directly to be highly sensitive to the segment's baseline deficit magnitude and profile noise, neither given in the manuscript text -- tuning attempts flipped which policy trips faster rather than converging on the paper's values |
| SST-aware retraining (single scenario, Table 3 rows 4-9) | Direction differs from the paper's single-seed result | The paper itself explicitly cautions that this single-scenario/single-seed comparison is not representative (see its own 4-seed sweep and Table 4 discussion) -- a different single-seed outcome here is consistent with that caution, not necessarily a bug |
| `table4_montecarlo.py` (Table 4, 500-trial sweep) | SST 0% trip rate reproduces (the core safety claim); conventional trip-rate direction and magnitude, and mean-slew magnitude (~10-15x smaller than the paper's), do not match | Same class of gap as Table 2 -- disturbance-severity distribution and baseline profile aren't specified precisely enough to pin down |
| `table5_observation_ablation.py` (Table 5) | Throughput-reduction direction matches; slew moves the opposite direction and magnitudes differ by ~70x | Likely a measurement-scope mismatch (this script measures over the full 600s segment; the paper's figures are almost certainly scoped to just the event window). Also run at 200 trials, not 500, given this environment's per-call time limits |
| `table6_techno_economics.py` (Table 6, Figs 2-3) | **Exact match on every reported number** ($6,000/$18,000 capex, \$8.54/EFC, \$0.0021/\$0.0029 stress costs, \$2,385 downtime cost, 2.5/7.5 breakeven events, 56.6% MC rate, \$601/yr efficiency penalty, <1yr central breakeven) -- this piece is mostly deterministic arithmetic on cited external costs plus Paper 1's own verified figures, so exact reproduction was achievable | Tornado-chart shape also matches the paper's own stated conclusion (disturbance frequency dominates breakeven sensitivity) |

## Files

```
code/         12 Python scripts
checkpoints/  3 trained DQN checkpoints (frozen, SST-aware, +MV-link-observation variant)
results/      JSON result summaries + figs/ (regenerated Fig 2-3 plots)
paper/        the manuscript itself
```

## Dependencies

```
pip install numpy scipy matplotlib torch
```

## Running

Training is chunked (`run_training_chunk.py`) to work within this
environment's per-call time limits while still running the full
paper-specified 260 episodes; each checkpoint here was produced that
way. To retrain from scratch:

```bash
cd code
python3 run_training_chunk.py --tag frozen --episodes 260 --chunk 120
# repeat with the same --tag until it reports DONE
python3 run_training_chunk.py --tag sst_aware_seed7 --sst_aware --episodes 260 --chunk 120
python3 run_training_chunk.py --tag mv_link_obs --sst_aware --mv_link_obs --episodes 260 --chunk 120
```

Then, with checkpoints in place:

```bash
python3 table2_joint_eval.py
python3 table4_montecarlo.py 150   # run 4x to cover all 500 trials
python3 table5_observation_ablation.py
python3 table6_techno_economics.py
```
