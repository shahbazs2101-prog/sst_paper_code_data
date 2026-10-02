# Coupled SST average power model pilot v0.1

This package is the first coupled validation step for the fixed manuscript Energy-Matched Ride-Through Assessment of a Three-Stage Solid-State Transformer for PV-BESS Microgrids. It contains MATLAB source and a Simulink builder. It contains no executed MATLAB results and no prebuilt SLX. MATLAB/Simulink R2025b must execute the builder on the author's computer.

## Run
1. Extract into a new folder on your Windows laptop. Keep all M files together.
2. Open RUN_ME_FIRST.m in MATLAB R2025b and click Run.
3. MATLAB first checks invariants, builds SST_Coupled_Average_Pilot_v01.slx and runs 48 simulations: three interfaces, eight scenarios, two sample times. This may take several minutes.
4. Return the generated SST_Pilot_Executed_TIMESTAMP.zip. This contains execution logs, parameters, summaries, convergence differences, plots and waveforms sampled every 1 ms with trip edges retained.
5. Keep raw_results/TIMESTAMP on your computer. It contains full-step MAT waveforms; summary metrics and invariant checks use these full waveforms. The smaller return archive contains decimated waveforms, not the full temporal record. Do not delete raw files: detailed follow-up may require selected full-resolution runs.
6. If MATLAB errors, return the exact error and execution_log.txt. A failed execution is not evidence of successful validation. Do not remove assertions to get a pass.

## Model and numerical method
The model uses 26 explicit discrete states and forward Euler integration at 50 and 25 microseconds. Nine capacitor energies and one LV capacitor energy couple through instantaneous SPS DAB transfer. Grid d/q current follows a 2 ms first-order closed-loop actuator with actual current-circle enforcement and reactive-current priority. A PI energy controller commands active current. The SST LV PI loop commands total DAB power; a box projection redistributes per-cell power by voltage error, preserves total power and respects voltage-dependent DAB bounds. The fleet differential controller is proportional in this first pilot; reserved differential integrator states are unused. This differs from the manuscript's separate PI balancing experiment and must not silently replace it.

An ideal grid-aligned frame is assumed. The current actuator represents finite closed-loop bandwidth rather than a switched CHB/filter plant. There is no implemented PLL, CHB modulation-voltage limit, phase imbalance, transformer magnetic model, reverse-power DAB operation, switching loss, dead time, device Coss, PV/BESS converter or LV AC inverter. This is an average power-domain model implemented in Simulink through a Level-2 MATLAB S-function, not a physically wired Simscape network. It can test coupling, power limits, energy depletion, protection and recovery under these assumptions; it does not close the entire switching/control validation gap.

SST: nine 2 mF links at 3300 V plus a 2 mF LV bus. LFT-ripple: 2 mF LV bus. LFT-matched: 236.0918 mF LV bus. All use the same 150 kVA current rating and actuator law. Matching is the manuscript's MV usable-energy budget against the conventional LV bank. The SST also has 230.4 J of usable LV ripple-capacitor energy, which the manuscript's ideal comparison excluded; report this extra energy explicitly when interpreting a difference. Frozen MV states in conventional runs are bookkeeping only and supply no power.

Protection latches at any SST MV link at or below 0.85 pu or the LV bus at or below 0.80 pu. Tripped delivered load is zero; unmet demand continues to be recorded. No automatic restart is assumed. Successful nontripping runs include recovery; tripped runs remain latched after grid restoration. No independent DAB-headroom trip is imposed: DAB saturation can lower LV voltage until protection acts.

Demand and grid events in this pilot are deterministic synthetic tests. The coincident 20 kW step is a net-demand disturbance, not measured PV/load data. No NREL data are consumed by these runs. The real irradiance input remains in the manuscript's separate audited sensitivity package.

## Interpretation and checks
Initial states are the nominal load equilibrium. Controller gains are starting engineering values, not experimentally identified or validated. Record gains if changed; rerun every comparator and both step sizes. The energy residual compares total capacitor-energy change with accumulated grid energy minus delivered-load energy. Internal DAB flows cancel. Current actuator energy/losses are omitted, consistently with the lossless power-domain boundary.

Convergence.csv reports differences and trip-status agreement. It does not auto-declare convergence. Review trip times, min voltage, unmet energy and waveform recovery before selecting further refinement or changing gains. Differences in outcomes are reported without any target trip rate. No claim of MATLAB execution, hardware validation or submission readiness is made in this package.

## Implementation sources
MathWorks Level-2 MATLAB S-functions documentation:
https://www.mathworks.com/help/simulink/sfg/writing-level-2-matlab-s-functions.html
https://www.mathworks.com/help/simulink/sfg/sample-times-matlab.html

Source preparation assisted by ChatGPT. Author execution and scientific review are required before using results in the manuscript.
