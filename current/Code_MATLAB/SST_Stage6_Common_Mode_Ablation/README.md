# Stage 6: common-mode ablation — executed 2026-10-02

The preparation instructions below are retained as historical context. Stage 6 has now been executed and incorporated in the manuscript. See ../../Executed_Results/Stage6_20261002_190112/summary.csv and ../../Audit/Stage6_FullStep/AUDIT_INTERPRETATION.md.


Extract this folder beside the existing stages, not into a stage folder. Open it in MATLAB and run `RUN_STAGE6`.

132 runs: 3 implementations × 2 reference variants × 11 existing cases × 2 time steps. SST is the archived Stage 5 implementation. SST_minmax applies standard min/max common-mode injection BEFORE phase voltage clamping, while keeping cell capacitances, controls, protection, events and integration unchanged. LFT_matched repeats the conventional comparator. Per-phase cell voltage limits remain actual sums, so this intervention does not make the voltage capabilities equal. It changes an averaged voltage allocation; it does not execute cell PWM.

The run repeats nominal and energy invariants, checks finite outputs and trip latches, preserves executed source, and saves full-step raw outputs separately from decimated exports. It does not automatically prove stability or causal generality. Return the Stage6 Executed ZIP and keep raw_results. Compare the SST and conventional repeats with Stage 5, then compare SST vs SST_minmax first causes, trip times, utilization and tracking before deciding how to revise the scientific claims. No Stage 6 outcomes appear in the manuscript until actual execution.
