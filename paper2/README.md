# Code and Data -- Supervisory RL Energy Management Under an SST Interface Swap

This repository backs the manuscript:

**"Does a Smarter Grid Interface Change What a Supervisory Reinforcement-Learning Energy Manager Must Learn? Observation Design, Retraining, and Techno-Economics for an SST-Interfaced PV-BESS Microgrid"**

## Reproducibility status

The Paper 2 evaluation pipeline has been updated so that regenerated results, rather than legacy manuscript values, are authoritative.

Key reproducibility rules now enforced:

- `environment.py` samples PV and load once per 1 s decision interval and uses that same realization for the observation and physical transition.
- `config.py` is the single source of truth for ratings, time steps, SOC limits, event ranges, seeds, and trial counts.
- `metrics.py` defines the common event-window throughput, command-slew, and time-at-slew-limit calculations used by Tables 4 and 5.
- Tables 4 and 5 use the same deterministic 500-event draw sequence (`seed=7`) and the same per-trial environment seeds.
- The Table 5 sweep is 500 trials, not the previous 200-trial shortcut.
- Table 2 and Tables 4-5 no longer print or embed legacy manuscript numbers as comparison targets.

**Important:** the existing checkpoint files were trained with the earlier environment implementation. They must be regenerated before the new Tables 2-5 results are treated as final.

## Files

```
code/         Python implementation
checkpoints/  trained DQN checkpoints (regenerate after the environment fix)
results/      regenerated JSON result summaries
paper/        manuscript
```

## Dependencies

```bash
pip install numpy scipy matplotlib torch
```

## Correct regeneration order

From `paper2/code`:

### 1. Retrain all three DQN variants from scratch

```bash
python3 run_training_chunk.py --tag frozen --episodes 260 --chunk 120
# repeat the same command until DONE

python3 run_training_chunk.py --tag sst_aware_seed7 --sst_aware --episodes 260 --chunk 120
# repeat until DONE

python3 run_training_chunk.py --tag mv_link_obs --sst_aware --mv_link_obs --episodes 260 --chunk 120
# repeat until DONE
```

Do not reuse the old checkpoint files for the final paper numbers.

### 2. Regenerate Table 2

```bash
python3 table2_joint_eval.py
```

### 3. Regenerate Table 4

```bash
python3 table4_montecarlo.py
```

This performs the complete 500-trial sweep in one run and writes:

`../results/table4_montecarlo.json`

### 4. Regenerate Table 5

```bash
python3 table5_observation_ablation.py
```

This also performs the complete 500-trial sweep and writes:

`../results/table5_observation_ablation.json`

### 5. Update the manuscript

Only after the new JSON outputs are inspected should the manuscript Tables 2-5 and associated text be updated. The regenerated values are authoritative even if they differ from the current manuscript.

## Scientific rule

Do not tune the code to recover the old manuscript numbers. If the corrected environment or common metric definitions change a result, report the new result and update the manuscript accordingly.
