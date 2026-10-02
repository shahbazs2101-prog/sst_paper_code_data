# SST coupled pilot refinement v0.2

Extract into a NEW folder and run RUN_ME_FIRST.m in MATLAB R2025b. Return SST_Refinement_Executed_TIMESTAMP.zip. Retain raw_results locally.

Twelve simulations: all three architectures for rated interruption at 12.5 microseconds, and short interruption, coincident net-demand disturbance and partial sag at 25 microseconds. Recovery cases run for six seconds. Rated interruption retains the 1.8 second scoring horizon so unmet-energy metrics can be compared directly to the first run. No physical equations, controller gains or protection thresholds change.

Full-step results determine metrics; return waveforms are sampled every 1 ms with trip edges retained. Full-step MAT waveforms remain in raw_results. Compare the 12.5 microsecond rated-load results to the prior 25 and 50 microsecond results before asserting convergence.

Recovery_within_1pct_s is the time after grid restoration following the final violation of the 1% voltage band through the END OF THE RECORDED WINDOW. SST requires both LV and all nine MV voltages; conventional requires LV only. Zero means inside the band throughout the recorded restoration window. NaN means tripped or not recovered by the end. This finite-window metric is not an asymptotic stability proof. Coincident net-demand changes end at 0.75 s; grid recovery occurs earlier at 0.70 s, so its recovery metric includes the later demand removal. Mean MV voltages for conventional runs are frozen bookkeeping values, not real conventional links.

First-run results were inspected: all 48 runs supplied; trip outcomes agreed between steps; the largest trip-time difference was 75 microseconds. At 25 microseconds, 60 kW long interruption gives 453.30 ms SST and matched hold-up. At 150 kW, SST trips at 140.375 ms after onset versus matched 181.325 ms. The latter differs from the separate 112.3 ms analytical full-power boundary because this dynamic model permits DAB saturation and LV-capacitor depletion before protection. Do not equate onset of power saturation with protection trip.

This remains the average POWER-DOMAIN pilot described in v0.1: ideal grid angle, first-order current actuator, instantaneous SPS transfer, lossless capacitor accounting and proportional differential balancing. It is not switched CHB/PLL validation, hardware evidence or measured NREL disturbance replay. All events are synthetic controlled scenarios. No new executed results are included.
